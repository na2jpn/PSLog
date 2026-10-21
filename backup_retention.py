"""Bound only recognized PSLog recovery/history files; never follow links.

Call locked cleaners after a successful operation. Completed recovery records
are expendable history; pending records and failed rollbacks are not.
User-chosen full backup ZIPs and arbitrary files are outside this policy.
"""
from pathlib import Path
from collections import defaultdict
import logging
import re

LOG_BACKUP = re.compile(r'(.+\.txt)\.\d{8}-\d{6}-\d{6}-[0-9a-f]{8}\.bak')
UUID_DONE = re.compile(r'[0-9a-f]{32}\.done\.json')
SAFETY = re.compile(r'PSLog_before_(?:full_restore|update)_\d{8}-\d{6}_[0-9a-f]{8}\.zip')


def _safe(root, path):
    root, path = Path(root).absolute(), Path(path).absolute()
    if not path.is_relative_to(root):return False
    current = root
    if current.is_symlink():return False
    for part in path.relative_to(root).parts:
        current = current / part
        if current.is_symlink():return False
    return True


def configured_keep(root):
    from storage import load_settings
    keep = load_settings(root).get('backup_keep', 30)
    if type(keep) is not int or keep not in (10,30,60,100):
        raise ValueError('バックアップ保持数が不正なため整理を中止しました。')
    return keep


def _trim(root, paths, keep):
    if type(keep) is not int or keep < 1:raise ValueError('保持数は1以上です。')
    safe = [p for p in paths if _safe(root,p) and p.is_file() and not p.with_name(p.name+'.keep').exists()]
    # mtime gives legacy UUID-named journals a meaningful order; name breaks ties.
    safe.sort(key=lambda p:(p.stat().st_mtime_ns,p.name))
    for p in safe[:-keep]:
        if _safe(root,p):p.unlink()


def _files(root, folder, expression, keep, grouped=False):
    folder=Path(folder)
    if not _safe(root,folder) or not folder.is_dir():return
    groups=defaultdict(list)
    for p in folder.iterdir():
        m=expression.fullmatch(p.name)
        if m and p.is_file() and _safe(root,p):groups[m[1] if grouped else 'all'].append(p)
    for paths in groups.values():_trim(root,paths,keep)


def prune_safety(root, folder):
    _files(root,folder,SAFETY,2)


def clean_book(book, keep):
    book=Path(book);root=book.parent;bak=root/'bak'
    # A pending transaction may still need any of its older evidence.
    dirs=[bak/'batch_recovery',bak/'year_moves',bak/'year_moves_flr']
    if any(not _safe(root,p) for p in dirs):return
    if any(list(p.glob('*.pending.json')) for p in dirs):return
    _files(root,bak,LOG_BACKUP,keep,True)
    for folder in dirs:_files(root,folder,UUID_DONE,keep)
    _files(root,bak/'logbook_bak',LOG_BACKUP,keep,True)
    _files(root,bak,re.compile(r'import-\d{8}-\d{6}-[0-9a-f]{8}\.json'),keep)


def clean_history(root, folder, keep):
    folder=Path(folder)
    if not _safe(root,folder) or not folder.is_dir():return
    if any(folder.glob('*pending*')) or (folder/'.pack-pending.json').exists():return
    history=folder/'history'
    _files(root,history,re.compile(r'(.+)_\d{20}\.txt'),keep,True)
    bundled=history/'bundled'
    if _safe(root,bundled) and bundled.is_dir():
        groups=defaultdict(list);directories=[]
        for directory in bundled.iterdir():
            if not re.fullmatch(r'\d{20}',directory.name) or not _safe(root,directory) or not directory.is_dir():continue
            directories.append(directory)
            for p in directory.iterdir():
                if p.suffix in ('.txt','.json') and p.is_file() and _safe(root,p):groups[p.name].append(p)
        for paths in groups.values():_trim(root,paths,keep)
        for directory in directories:
            if not any(directory.iterdir()):directory.rmdir()
    # Rule-pack safety groups contain several originals; retain per original,
    # rather than deleting a whole group that may contain a rare edited file.
    if _safe(root,history) and history.is_dir():
        groups=defaultdict(list);directories=[]
        for directory in history.iterdir():
            if not re.fullmatch(r'pack-[0-9a-f]{32}',directory.name) or not _safe(root,directory) or not directory.is_dir():continue
            directories.append(directory)
            for p in directory.iterdir():
                if p.is_file() and p.suffix in ('.txt','.json') and _safe(root,p):groups[p.name].append(p)
        for paths in groups.values():_trim(root,paths,keep)
        for directory in directories:
            if not any(directory.iterdir()):directory.rmdir()


def clean_award(root, folder, keep):
    _files(root,folder,re.compile(r'([0-9a-f]{16})\.\d{20}\.bak'),keep,True)


def after_operation(directory):
    """Best-effort housekeeping must not turn a committed save into a failure."""
    directory=Path(directory)
    try:
        if directory.name in ('logbook','logbook_flr'):
            root=directory.parent;clean_book(directory,configured_keep(root))
        elif directory.parent.name=='config' and directory.name in ('rules','templates'):
            root=directory.parent.parent;clean_history(root,directory,configured_keep(root))
        elif directory.name=='cabrillo' and directory.parent.name=='templates' and directory.parent.parent.name=='config':
            root=directory.parent.parent.parent;clean_history(root,directory,configured_keep(root))
        elif directory.name=='db' and directory.parent.name=='config':
            root=directory.parent.parent
            _files(root,directory/'history',re.compile(r'(location_overrides)_\d{20}\.json'),configured_keep(root),True)
        elif directory.parent.name=='awards' and directory.parent.parent.name=='config':
            root=directory.parent.parent.parent;clean_award(root,directory,configured_keep(root))
    except Exception as e:
        logging.getLogger(__name__).warning('バックアップ整理を完了できません: %s',e)


def maintain(root, keep):
    """Startup/exit migration: lock each writer's scope; never alter originals."""
    from storage import operation_lock
    root=Path(root);errors=[]
    def run(folder, action):
        if not _safe(root,folder):return
        try:
            with operation_lock(folder):action()
        except Exception as e:errors.append(str(e))
    for name in ('logbook','logbook_flr'):
        run(root/name,lambda name=name:clean_book(root/name,keep))
    for name in ('rules','templates'):
        folder=root/'config'/name
        if folder.exists():run(folder,lambda folder=folder:clean_history(root,folder,keep))
    folder=root/'config/templates/cabrillo'
    if folder.exists():run(folder,lambda folder=folder:clean_history(root,folder,keep))
    folder=root/'config/db'
    if folder.exists():run(folder,lambda:_files(root,root/'config/db/history',re.compile(r'(location_overrides)_\d{20}\.json'),keep,True))
    awards=root/'config/awards'
    if _safe(root,awards) and awards.is_dir():
        for folder in awards.iterdir():
            if folder.is_dir():run(folder,lambda folder=folder:clean_award(root,folder,keep))
    # Restore uses both logbook locks, so safety pruning cannot race its writes.
    try:
        with operation_lock(root/'logbook'),operation_lock(root/'logbook_flr'):
            for name in ('full-restore-safety','update-safety'):prune_safety(root,root/'bak'/name)
    except Exception as e:errors.append(str(e))
    return errors
