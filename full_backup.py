"""Portable full backup of PSLog user data.

Format 1 adds a manifest so newer PSLog releases can distinguish bundled defaults
from files the user actually changed.  The ZIP stays a normal, directly readable
archive: config/ and logbook/ are stored with their relative paths.
"""
from pathlib import Path
from datetime import datetime
from zipfile import ZipFile, ZIP_DEFLATED
import hashlib
import io
import json
import sys
import uuid

from storage import Snapshot, StorageError, VERSION, operation_lock, replace_bytes
from model import now_jst

MANIFEST = 'PSLOG_BACKUP_INFO.json'
FORMAT_VERSION = 1


def files(root):
    result=[]
    for name in ('config','logbook','logbook_flr'):
        directory=root/name
        if directory.is_symlink():raise StorageError('バックアップ対象フォルダーがシンボリックリンクです。')
        if not directory.exists():continue
        for p in directory.rglob('*'):
            if p.is_symlink():raise StorageError('バックアップ対象にシンボリックリンクがあります。')
            if p.is_file() and not p.name.startswith('.pslog-'):result.append(p)
    return sorted(result)


def _bundle_root():
    return Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent)).resolve()


def _role(root, path, data):
    rel=path.relative_to(root).as_posix()
    if rel.startswith(('logbook/','logbook_flr/')):
        return 'logbook'
    # conf.cfg and files absent from the shipped bundle are user state.
    bundled=_bundle_root()/Path(rel)
    try:
        if bundled.is_file() and bundled.resolve()!=path.resolve() and bundled.read_bytes()==data:
            return 'bundled'
    except OSError:
        pass
    # In source/development mode root can be the source tree itself.  Known
    # shipped config files are still defaults; explicit runtime state is not.
    if root.resolve()==_bundle_root() and rel!='config/conf.cfg':
        if rel.startswith(('config/rules/','config/db/','config/templates/')):
            return 'bundled'
    return 'user'


def _manifest(root, snapshots):
    entries=[]
    for p,snap in snapshots.items():
        data=snap.data
        if data is None:continue
        entries.append({
            'path':p.relative_to(root).as_posix(),
            'sha256':hashlib.sha256(data).hexdigest(),
            'role':_role(root,p,data),
            'size':len(data),
        })
    return {
        'format':'PSLog full backup',
        'format_version':FORMAT_VERSION,
        'pslog_version':VERSION,
        'created_at_jst':now_jst().strftime('%Y-%m-%d %H:%M:%S JST'),
        'entries':entries,
        'compatibility':{
            'newer_pslog_should_restore_older_backup':True,
            'older_pslog_may_not_restore_newer_backup':True,
        },
    }


def _payload(repo):
    paths=files(repo.root);snapshots={p:Snapshot.read(p) for p in paths}
    if not paths:raise StorageError('バックアップするファイルがありません。')
    manifest=_manifest(repo.root,snapshots)
    buffer=io.BytesIO()
    with ZipFile(buffer,'w',ZIP_DEFLATED) as archive:
        archive.writestr(MANIFEST,json.dumps(manifest,ensure_ascii=False,indent=2).encode('utf-8'))
        for p,snap in snapshots.items():
            if snap.data is None:raise StorageError('バックアップ中にファイルが削除されました。')
            archive.writestr(p.relative_to(repo.root).as_posix(),snap.data)
    payload=buffer.getvalue()
    with ZipFile(io.BytesIO(payload)) as archive:
        if archive.testzip() is not None:raise StorageError('バックアップZIPの検証に失敗しました。')
        if MANIFEST not in archive.namelist():raise StorageError('バックアップ情報の作成に失敗しました。')
    if paths!=files(repo.root):raise StorageError('バックアップ中にファイル構成が変わりました。再実行してください。')
    for p,snap in snapshots.items():snap.check(p)
    return payload,len(paths)


def create(repo,destination):
    destination=Path(destination).resolve()
    # Backward compatible: callers may pass a folder (old UI/tests) or the
    # exact ZIP path (new Save File dialog).
    if destination.suffix.lower()=='.zip':
        target=destination;parent=target.parent
        if not parent.is_dir():raise ValueError('存在する保存先フォルダーを選択してください。')
    else:
        if not destination.is_dir():raise ValueError('存在する保存先フォルダーを選択してください。')
        parent=destination;target=None
    if any(parent.is_relative_to(repo.root/n) for n in ('config','logbook','logbook_flr','bak')):
        raise ValueError('config・logbook・logbook_flr・bakの外にある保存先を選んでください。')
    with operation_lock(repo.book),operation_lock(repo.free_book),operation_lock(repo.root/'config'):
        payload,count=_payload(repo)
        if target is None:
            target=parent/('PSLog_backup_'+datetime.now().strftime('%Y%m%d-%H%M%S')+'_'+uuid.uuid4().hex[:8]+'.zip')
        expected=Snapshot.read(target) if target.exists() else Snapshot(None,None)
        replace_bytes(target,payload,expected)
    return target,count


def create_restore_safety(repo):
    """Create a durable pre-restore snapshot under bak/ (not nested in full backups)."""
    folder=repo.bak/'full-restore-safety';folder.mkdir(parents=True,exist_ok=True)
    target=folder/('PSLog_before_full_restore_'+now_jst().strftime('%Y%m%d-%H%M%S')+'_'+uuid.uuid4().hex[:8]+'.zip')
    with operation_lock(repo.book),operation_lock(repo.free_book),operation_lock(repo.root/'config'):
        # A fresh installation can legitimately have nothing to protect yet.
        if not files(repo.root):return None,0
        payload,count=_payload(repo)
        replace_bytes(target,payload,Snapshot(None,None))
    return target,count


def create_update_safety(repo):
    """Create a pre-version-update snapshot under bak/update-safety."""
    folder=repo.bak/'update-safety';folder.mkdir(parents=True,exist_ok=True)
    target=folder/('PSLog_before_update_'+now_jst().strftime('%Y%m%d-%H%M%S')+'_'+uuid.uuid4().hex[:8]+'.zip')
    with operation_lock(repo.book),operation_lock(repo.free_book),operation_lock(repo.root/'config'):
        if not files(repo.root):return None,0
        payload,count=_payload(repo)
        replace_bytes(target,payload,Snapshot(None,None))
    return target,count
