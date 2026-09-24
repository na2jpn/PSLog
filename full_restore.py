"""Validate and restore PSLog full-backup ZIPs, including legacy manifest-less ZIPs."""
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from zipfile import ZipFile, BadZipFile
import hashlib
import json
import sys

from storage import Snapshot, StorageError, parse, replace_bytes, operation_lock
from preferences import validate as validate_preferences
from full_backup import MANIFEST, FORMAT_VERSION, create_restore_safety
from model import now_jst

MAX_FILES=20000
MAX_UNCOMPRESSED=2*1024*1024*1024  # defensive; ordinary PSLog backups are far smaller

@dataclass
class RestorePlan:
    path: Path
    source_version: str
    created_at: str
    format_version: int
    legacy: bool
    files: dict
    roles: dict
    active: list
    skipped_bundled: list
    legacy_conflicts: list
    logbook_files: list


def _bundle_root():
    return Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent)).resolve()


def _safe_name(name):
    if '\\' in name:raise StorageError('ZIP内にWindows区切り文字を使った不正なパスがあります。')
    p=PurePosixPath(name)
    if p.is_absolute() or '..' in p.parts or not p.parts:raise StorageError('ZIP内に不正なパスがあります。')
    if p.parts[0] in ('config','logbook','logbook_flr') and len(p.parts)<2:raise StorageError('ZIP内に不正なパスがあります。')
    return p


def _read_archive(path):
    path=Path(path).resolve()
    if not path.is_file():raise StorageError('全体バックアップZIPが見つかりません。')
    try:
        with ZipFile(path) as z:
            infos=z.infolist()
            if len(infos)>MAX_FILES:raise StorageError('ZIP内のファイル数が多すぎます。')
            if sum(i.file_size for i in infos)>MAX_UNCOMPRESSED:raise StorageError('ZIPの展開後サイズが大きすぎます。')
            if z.testzip() is not None:raise StorageError('ZIPの検証に失敗しました。')
            seen=set();files={}
            for info in infos:
                if info.is_dir():continue
                if info.flag_bits & 0x1:raise StorageError('暗号化ZIPには対応していません。')
                p=_safe_name(info.filename);name=p.as_posix()
                if name in seen:raise StorageError('ZIP内に同名ファイルが重複しています: '+name)
                seen.add(name)
                if name!=MANIFEST and p.parts[0] not in ('config','logbook','logbook_flr'):
                    raise StorageError('PSLog全体バックアップ以外のファイルが含まれています: '+name)
                files[name]=z.read(info)
    except (BadZipFile,OSError) as e:raise StorageError('ZIPを読み込めません: '+str(e)) from e
    return path,files


def _validate_content(name,data):
    if name.startswith(('logbook/','logbook_flr/')) and name.lower().endswith('.txt'):
        try:log=parse(data)
        except StorageError:raise
        if log.issues:raise StorageError(f'{name} に解釈できないログ行があります。全体復元を停止しました。')
    elif name=='config/conf.cfg':
        try:value=json.loads(data.decode('utf-8'))
        except (ValueError,UnicodeError) as e:raise StorageError('バックアップのconf.cfgを読み込めません。') from e
        if not isinstance(value,dict):raise StorageError('バックアップのconf.cfgが設定オブジェクトではありません。')
        try:validate_preferences(value)
        except ValueError as e:raise StorageError('バックアップの設定値が不正です: '+str(e)) from e
    elif name.startswith('config/rules/') and name.lower().endswith('.txt') and '/history/' not in name:
        try:
            from contest_rules import loads
            loads(data.decode('utf-8-sig'))
        except (ValueError,UnicodeError) as e:raise StorageError(f'{name} は現在のPSLogで読み込めないルールです: {e}') from e
    elif name.startswith('config/templates/cabrillo/') and name.lower().endswith('.txt') and '/history/' not in name:
        try:
            from cabrillo_templates import loads
            loads(data.decode('utf-8-sig'))
        except (ValueError,UnicodeError) as e:raise StorageError(f'{name} は現在のPSLogで読み込めないテンプレートです: {e}') from e


def inspect_backup(repo,path):
    path,files=_read_archive(path)
    manifest_raw=files.pop(MANIFEST,None)
    legacy=manifest_raw is None
    source_version='不明';created='不明';fmt=0;roles={}
    if manifest_raw is not None:
        try:m=json.loads(manifest_raw.decode('utf-8'))
        except (ValueError,UnicodeError) as e:raise StorageError('バックアップ情報を読み込めません。') from e
        if not isinstance(m,dict) or m.get('format')!='PSLog full backup':raise StorageError('PSLog全体バックアップ情報が不正です。')
        fmt=m.get('format_version')
        if type(fmt) is not int or fmt<1 or fmt>FORMAT_VERSION:raise StorageError(f'未対応のバックアップ形式です: {fmt}')
        source_version=str(m.get('pslog_version','不明'));created=str(m.get('created_at_jst','不明'))
        entries=m.get('entries')
        if not isinstance(entries,list):raise StorageError('バックアップのファイル一覧が不正です。')
        listed=set()
        for e in entries:
            if not isinstance(e,dict):raise StorageError('バックアップのファイル情報が不正です。')
            name=e.get('path');role=e.get('role');digest=e.get('sha256')
            if not isinstance(name,str) or role not in ('logbook','user','bundled') or not isinstance(digest,str):raise StorageError('バックアップのファイル情報が不正です。')
            _safe_name(name)
            if name in listed:raise StorageError('バックアップ情報に重複パスがあります: '+name)
            listed.add(name)
            if name not in files:raise StorageError('バックアップ情報にあるファイルがZIP内にありません: '+name)
            if hashlib.sha256(files[name]).hexdigest()!=digest:raise StorageError('バックアップ情報とファイル内容が一致しません: '+name)
            roles[name]=role
        if listed!=set(files):raise StorageError('ZIP内のファイル一覧とバックアップ情報が一致しません。')
    if not files:raise StorageError('復元できるconfig/logbook/logbook_flrファイルがありません。')
    if not any(n.startswith(('logbook/','logbook_flr/')) for n in files) and 'config/conf.cfg' not in files:
        raise StorageError('PSLog全体バックアップとして必要な内容がありません。')
    if legacy and 'config/conf.cfg' in files:
        try:
            legacy_settings=json.loads(files['config/conf.cfg'].decode('utf-8'))
            if isinstance(legacy_settings,dict) and legacy_settings.get('version'):
                source_version=str(legacy_settings['version'])
        except (ValueError,UnicodeError):
            pass

    active=[];skip=[];legacy_conflicts=[];logs=[]
    bundle=_bundle_root()
    for name,data in files.items():
        if name.startswith(('logbook/','logbook_flr/')):
            _validate_content(name,data);active.append(name);logs.append(name);continue
        if not legacy:
            if roles.get(name)=='bundled':skip.append(name)
            else:_validate_content(name,data);active.append(name)
            continue
        # Legacy 1.01 and earlier: runtime state is safe to restore.  A config
        # file that is also shipped by the current PSLog is ambiguous: it may be
        # an old default or a user's edit.  Never silently downgrade current
        # bundled data; preserve the old copy separately for manual comparison.
        if name=='config/conf.cfg' or name=='config/blacklist.txt' or name.startswith('config/db/location_overrides') or '/history/' in name:
            _validate_content(name,data);active.append(name);continue
        bundled=bundle/Path(name)
        if bundled.is_file():
            try:same=bundled.read_bytes()==data
            except OSError:same=False
            if same:skip.append(name)
            else:legacy_conflicts.append(name)
        else:
            _validate_content(name,data);active.append(name)
    return RestorePlan(path,source_version,created,fmt,legacy,files,roles,active,skip,legacy_conflicts,logs)


def _target_path(repo,name):
    p=repo.root/Path(*PurePosixPath(name).parts)
    current=repo.root
    for part in PurePosixPath(name).parts[:-1]:
        current=current/part
        if current.exists() and current.is_symlink():raise StorageError('復元先にシンボリックリンクがあります: '+str(current))
    if p.exists() and p.is_symlink():raise StorageError('復元先がシンボリックリンクです: '+str(p))
    return p


def _conflict_target(repo,stamp,name):
    rel=PurePosixPath(name)
    # Keep legacy ambiguous config under config/restored_legacy/... so nothing
    # is discarded while current-version defaults stay active.
    tail=Path(*rel.parts[1:]) if rel.parts and rel.parts[0]=='config' else Path(*rel.parts)
    return repo.root/'config'/'restored_legacy'/stamp/tail


def restore(repo,plan):
    if not isinstance(plan,RestorePlan):plan=inspect_backup(repo,plan)
    if repo.book.is_symlink() or repo.free_book.is_symlink() or (repo.root/'config').is_symlink():raise StorageError('復元先のconfig/logbook/logbook_flrにシンボリックリンクは使用できません。')
    # Reinspect immediately before changing anything to detect a replaced ZIP.
    fresh=inspect_backup(repo,plan.path)
    if fresh.files!=plan.files or fresh.roles!=plan.roles:raise StorageError('確認後にバックアップZIPが変更されました。選び直してください。')

    safety,_=create_restore_safety(repo)
    stamp=now_jst().strftime('%Y%m%d-%H%M%S')
    staged=[]
    try:
        with operation_lock(repo.book),operation_lock(repo.free_book),operation_lock(repo.root/'config'):
            # Snapshot every path we intend to touch so arbitrary external changes
            # after validation are detected before replacement/deletion.
            targets={name:_target_path(repo,name) for name in fresh.active}
            snapshots={name:Snapshot.read(p) for name,p in targets.items()}
            # Legacy ambiguous config is preserved but not activated.
            conflict_targets={name:_conflict_target(repo,stamp,name) for name in fresh.legacy_conflicts}
            for name,p in conflict_targets.items():
                expected=Snapshot.read(p)
                replace_bytes(p,fresh.files[name],expected)
                staged.append(p)
            for name in fresh.active:
                replace_bytes(targets[name],fresh.files[name],snapshots[name])

            # A full restore means the logbook returns to the backed-up set.  Delete
            # current logbook files absent from the backup only after replacements
            # succeeded; the safety ZIP contains the prior state.
            wanted={(repo.root/Path(*PurePosixPath(n).parts)).resolve() for n in fresh.logbook_files}
            for book in (repo.book,repo.free_book):
                for p in sorted(book.rglob('*'),reverse=True):
                    if p.is_file() and not p.name.startswith('.pslog-') and p.resolve() not in wanted:
                        before=Snapshot.read(p);before.check(p);p.unlink()
                for d in sorted((p for p in book.rglob('*') if p.is_dir()),reverse=True):
                    try:d.rmdir()
                    except OSError:pass
    except (StorageError,OSError) as e:
        note=str(safety) if safety else '復元前の利用者データなし'
        raise StorageError(str(e)+'\n復元直前の安全バックアップ: '+note) from e
    return {
        'safety_backup':safety,
        'restored':len(fresh.active),
        'kept_current_defaults':len(fresh.skipped_bundled),
        'legacy_conflicts':len(staged),
        'legacy_conflict_folder':(repo.root/'config'/'restored_legacy'/stamp) if staged else None,
        'source_version':fresh.source_version,
        'legacy':fresh.legacy,
    }
