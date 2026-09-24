"""Small shared state helpers for the external PSLog update transaction."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import ctypes
import json
import os
import shutil
import sys

LOCK_NAME = '.pslog-update-active.json'
ROLLBACK_PREFIX = '.PSLogUpdateRollback-'


def lock_path(data_root):
    return Path(data_root).resolve() / 'bak' / LOCK_NAME


def _utcnow():
    return datetime.now(timezone.utc)


def _parse_time(value):
    try:return datetime.fromisoformat(str(value))
    except (TypeError,ValueError):return None


def process_alive(pid):
    try:pid=int(pid)
    except (TypeError,ValueError):return False
    if pid<=0:return False
    if sys.platform=='win32':
        SYNCHRONIZE=0x00100000
        handle=ctypes.windll.kernel32.OpenProcess(SYNCHRONIZE,False,pid)
        if not handle:return False
        try:
            result=ctypes.windll.kernel32.WaitForSingleObject(handle,0)
            return result==0x102  # WAIT_TIMEOUT => still running
        finally:ctypes.windll.kernel32.CloseHandle(handle)
    try:os.kill(pid,0);return True
    except OSError:return False


def read_lock(data_root):
    path=lock_path(data_root)
    if not path.is_file():return None
    try:
        data=json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(data,dict) or data.get('format')!='PSLog update active':return None
        return data
    except (OSError,ValueError,UnicodeError):return None


def write_lock(data_root,token,updater_pid=0):
    path=lock_path(data_root);path.parent.mkdir(parents=True,exist_ok=True)
    data={'format':'PSLog update active','token':str(token),'updater_pid':int(updater_pid or 0),'created_utc':_utcnow().isoformat()}
    temp=path.with_name(path.name+'.tmp')
    temp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    os.replace(temp,path)
    return path


def update_lock_pid(data_root,token,updater_pid):
    data=read_lock(data_root)
    if not data or data.get('token')!=str(token):raise OSError('更新待ち情報を確認できません。')
    return write_lock(data_root,token,updater_pid)


def remove_lock(data_root,token=None):
    path=lock_path(data_root)
    if token is not None:
        data=read_lock(data_root)
        if data and data.get('token')!=str(token):return False
    try:path.unlink(missing_ok=True);return True
    except OSError:return False


def lock_status(data_root,staging_grace_seconds=120):
    """Return ('none'|'active'|'stale', data). Invalid/stale files are removed."""
    path=lock_path(data_root)
    data=read_lock(data_root)
    if data is None:
        if path.exists():
            try:path.unlink()
            except OSError:pass
        return 'none',None
    pid=data.get('updater_pid',0)
    if process_alive(pid):return 'active',data
    created=_parse_time(data.get('created_utc'))
    age=(_utcnow()-created).total_seconds() if created and created.tzinfo else staging_grace_seconds+1
    # launch_update writes the lock immediately before spawning the updater;
    # tolerate that very short pid=0 handoff window.
    if not pid and age<=staging_grace_seconds:return 'active',data
    remove_lock(data_root,data.get('token'))
    return 'stale',data


def cleanup_stale_rollbacks(data_root):
    """Remove abandoned program rollback trees only while no update is active."""
    status,_=lock_status(data_root)
    if status=='active':return []
    root=Path(data_root).resolve();removed=[]
    for path in root.parent.glob(ROLLBACK_PREFIX+'*'):
        if not path.is_dir() or path.is_symlink():continue
        # If automatic rollback itself failed, updater.py deliberately marks
        # the directory as evidence/recovery material.  Never auto-delete it.
        if (path/'.PSLOG_KEEP_ROLLBACK').exists():continue
        try:
            shutil.rmtree(path);removed.append(path)
        except OSError:pass
    return removed
