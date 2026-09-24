"""Safe synchronization of PSLog-managed bundled data into the portable tree.

Bundled files are application assets and must be updateable, while local edits
must survive an updater run.  A small per-folder state records hashes that
PSLog itself last installed; only those unchanged managed files are replaced.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import hashlib
import json
import sys

from storage import Snapshot,replace_bytes,operation_lock

STATE_NAME='.pslog-bundled-state.json'
SCHEMA=1


def _sha(data):return hashlib.sha256(data).hexdigest()


def source_folder(relative):
    if getattr(sys,'frozen',False):
        root=Path(getattr(sys,'_MEIPASS',Path(sys.executable).resolve().parent))
    else:
        root=Path(__file__).resolve().parent
    return root/Path(relative)


def _read_state(target):
    path=Path(target)/STATE_NAME
    try:
        data=json.loads(path.read_text(encoding='utf-8'))
        if data.get('schema')==SCHEMA and isinstance(data.get('managed'),dict):return data
    except (OSError,ValueError,TypeError,json.JSONDecodeError):pass
    return {'schema':SCHEMA,'managed':{}}


def _write_state(target,state):
    path=Path(target)/STATE_NAME
    payload=(json.dumps(state,ensure_ascii=False,indent=2,sort_keys=True)+'\n').encode('utf-8')
    replace_bytes(path,payload,Snapshot.read(path))


def _backup(target,name,data):
    stamp=datetime.now().strftime('%Y%m%d%H%M%S%f')
    path=Path(target)/'history'/'bundled'/stamp/name
    replace_bytes(path,data,Snapshot(None,None))


def sync_bundled_folder(target,relative,pattern,migrate=None):
    """Synchronize bundled app assets without overwriting local modifications.

    ``migrate`` may be ``callable(name, local_bytes, bundled_bytes)`` and return
    replacement bytes for a narrowly-defined legacy migration, or ``None`` to
    keep the local file unchanged.
    """
    if not getattr(sys,'frozen',False):return 0
    source=source_folder(relative)
    if not source.is_dir():return 0
    target=Path(target);target.mkdir(parents=True,exist_ok=True)
    changed=0
    with operation_lock(target):
        state=_read_state(target);managed=state['managed']
        for src in sorted(source.glob(pattern)):
            if not src.is_file():continue
            bundled=src.read_bytes();bundled_hash=_sha(bundled);dst=target/src.name;snap=Snapshot.read(dst)
            if snap.data is None:
                replace_bytes(dst,bundled,snap);managed[src.name]=bundled_hash;changed+=1;continue
            local=snap.data;local_hash=_sha(local)
            if local_hash==bundled_hash:
                managed[src.name]=bundled_hash;continue
            previous=managed.get(src.name)
            if previous and local_hash==previous:
                _backup(target,src.name,local);replace_bytes(dst,bundled,snap);managed[src.name]=bundled_hash;changed+=1;continue
            replacement=migrate(src.name,local,bundled) if migrate else None
            if replacement is not None and replacement!=local:
                _backup(target,src.name,local);replace_bytes(dst,replacement,snap);changed+=1
                if _sha(replacement)==bundled_hash:managed[src.name]=bundled_hash
                else:managed.pop(src.name,None)
            elif local_hash!=bundled_hash:
                # Unknown or explicitly edited local data: preserve it and do
                # not claim that PSLog owns the current bytes.
                managed.pop(src.name,None)
        _write_state(target,state)
    return changed


def bundled_status(target,relative,name):
    """Return official / user_modified / user_defined for one local asset."""
    target=Path(target);local=target/name
    if not local.is_file():return 'user_defined'
    source=source_folder(relative)/name
    if not source.is_file():return 'user_defined'
    try:
        if _sha(local.read_bytes())==_sha(source.read_bytes()):return 'official'
    except OSError:return 'user_defined'
    state=_read_state(target)
    if state['managed'].get(name):
        # The state proves that PSLog managed this file before it diverged.
        return 'user_modified'
    if getattr(sys,'frozen',False):
        # Portable/frozen builds may be upgraded from versions that predate the
        # bundled-state file.  Preserve the legacy inference there: a differing
        # same-name bundled asset is treated as a user edit of an official file.
        return 'user_modified'
    # In a source checkout an unrelated rule root can legitimately contain a
    # user-created file whose name happens to match a bundled rule.  Without
    # managed history, same-name alone is not proof that it came from PSLog.
    return 'user_defined'
