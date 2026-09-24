"""Launch the external PSLogUpdater from a running frozen PSLog."""
from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import json
import os
import shutil
import subprocess
import tempfile
import uuid

from storage import StorageError
from update_state import write_lock, update_lock_pid, remove_lock

RETIRED_ROOT_DOCS=('USER_GUIDE.txt','SAVE_LOCATION.md','WINDOWS_CHECKLIST.txt')
METADATA_FILES=('BUILD_INFO.json','PSLOG_UPDATE_INFO.json')


def ensure_updater_layout(data_root):
    """Keep helper executables under exec/ while accepting legacy root layout."""
    root=Path(data_root).resolve()
    legacy=root/'PSLogUpdater.exe'
    folder=root/'exec';target=folder/'PSLogUpdater.exe'
    if legacy.is_file():
        try:
            folder.mkdir(parents=True,exist_ok=True)
            os.replace(legacy,target)
        except OSError as e:
            raise StorageError('PSLogUpdater.exe を exec フォルダーへ整理できません。\n'+str(e)) from e
    return target


def ensure_distribution_layout(data_root):
    """Migrate pre-1.043 Windows root files into the clean distribution layout.

    Bridge packages for 1.041/1.042 must use the exact layout understood by
    those already-installed updaters.  On the first Ver1.043 start, move their
    generated metadata below meta/, remove retired duplicated text documents,
    create the reserved docs/ directory, and retain helper executables in exec/.
    """
    root=Path(data_root).resolve()
    updater=ensure_updater_layout(root)
    try:
        meta=root/'meta';meta.mkdir(parents=True,exist_ok=True)
        docs=root/'docs';docs.mkdir(parents=True,exist_ok=True)
        legacy_metadata=any((root/name).is_file() for name in METADATA_FILES)
        for name in METADATA_FILES:
            legacy=root/name
            target=meta/name
            if legacy.is_file():
                os.replace(legacy,target)
        # Retire the three old distribution documents only while migrating an
        # actual pre-1.043 package.  Do not delete an unrelated file a user may
        # later create at the root with one of these names.
        if legacy_metadata:
            for name in RETIRED_ROOT_DOCS:
                legacy=root/name
                if legacy.is_file():legacy.unlink()
    except OSError as e:
        raise StorageError('PSLogの配布フォルダーをVer1.043形式へ整理できません。\n'+str(e)) from e
    return updater


def launch_update(data_root, package, current_version, mode='upgrade'):
    if mode not in ('upgrade','reinstall'):
        raise StorageError('更新モードが不正です。')
    data_root = Path(data_root).resolve()
    package = Path(package).resolve()
    updater = ensure_distribution_layout(data_root)
    if not updater.is_file():
        raise StorageError('exec\\PSLogUpdater.exe が見つかりません。Windows版PSLog一式を確認してください。')
    folder = Path(tempfile.mkdtemp(prefix='PSLogUpdateLaunch-'))
    copied = folder / 'PSLogUpdater.exe'
    session = folder / 'session.json'
    token = uuid.uuid4().hex
    try:
        shutil.copy2(updater, copied)
        payload = {
            'format': 'PSLog update session',
            'format_version': 1,
            'token': token,
            'created_utc': datetime.now(timezone.utc).isoformat(),
            'package': str(package),
            'target': str(data_root),
            'current_version': str(current_version),
            'mode': str(mode),
            'pid': os.getpid(),
        }
        session.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        # The lock lives in bak/ (a preserved runtime area), so it survives the
        # program-directory swap without adding clutter to the PSLog root.
        write_lock(data_root,token,0)
        process=subprocess.Popen([str(copied), '--session', str(session), '--token', token], cwd=str(folder), close_fds=True)
        update_lock_pid(data_root,token,process.pid)
    except BaseException:
        remove_lock(data_root,token)
        shutil.rmtree(folder, ignore_errors=True)
        raise
    return session
