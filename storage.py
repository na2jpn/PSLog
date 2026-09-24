"""PSLog 1.14 storage foundation. Standard library only.

Read legacy records without applying new-entry RST constraints. Preserve every
unmodified line, BOM and newline. Never silently repair ambiguous source data.
"""
from __future__ import annotations
from contextlib import contextmanager
from dataclasses import dataclass, fields
from datetime import datetime, timedelta
from pathlib import Path
import hashlib
import json
import os
import re
import tempfile
import unicodedata
import uuid
from model import QSO, validate_station

VERSION = '1.14'
TERMINATOR = '\\' * 2

class StorageError(Exception): pass
class ExternalChange(StorageError): pass
class InvalidLog(StorageError): pass

@dataclass(frozen=True)
class Issue:
    line: int
    reason: str
    raw: str

@dataclass
class ParsedLine:
    raw: str
    qso: QSO | None = None

@dataclass
class Log:
    lines: list[ParsedLine]
    issues: list[Issue]
    notices: list[Issue]
    bom: bool
    newline: str

    @property
    def records(self):
        return [(i + 1, line.qso) for i, line in enumerate(self.lines) if line.qso]

def parse(data: bytes) -> Log:
    bom = data.startswith(b'\xef\xbb\xbf')
    try: text = data.decode('utf-8-sig')
    except UnicodeDecodeError as e: raise InvalidLog('UTF-8として読み込めません。文字コードを確認してください。') from e
    lines, issues, notices = [], [], []
    endings = re.findall(r'\r\n|\r|\n', text)
    newline = endings[0] if endings else '\r\n'
    for number, raw in enumerate(text.splitlines(keepends=True), 1):
        entry = ParsedLine(raw); lines.append(entry)
        s = raw.rstrip('\r\n').strip()
        if not s: continue
        if s.startswith('DATE | TIME |'):
            notices.append(Issue(number, '見出し行（交信には数えません）', s)); continue
        if re.fullmatch(r'-{2,}\d{4}(?:\s+.*)?', s):
            notices.append(Issue(number, '年・運用の区切り。自局の自動振り分けは行いません。', s)); continue
        try:
            if not s.endswith(TERMINATOR): raise ValueError('行末のバックスラッシュ2文字がありません。')
            vals = [v.strip() for v in s[:-2].rstrip().split('|')]
            if len(vals) not in (10, 11): raise ValueError(f'{len(vals)}項目あります（10または11項目が必要）。')
            if len(vals) == 10: vals.append('')
            if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', vals[0]): raise ValueError('DATEはYYYY-MM-DD形式が必要です。')
            if not re.fullmatch(r'\d{2}:\d{2} JST', vals[1]): raise ValueError('TIMEはhh:mm JST形式が必要です。')
            vals[1] = vals[1][:-4]
            datetime.strptime(vals[0] + ' ' + vals[1], '%Y-%m-%d %H:%M')
            if any('\t' in v or '\x00' in v for v in vals): raise ValueError('項目内にタブまたはNULがあります。')
            if not all(vals[i] for i in (2,3,4)): raise ValueError('BAND、MODE、相手コールが空欄です。')
            entry.qso = QSO(*vals)
        except ValueError as e: issues.append(Issue(number, str(e), s))
    return Log(lines, issues, notices, bom, newline)

@dataclass(frozen=True)
class Snapshot:
    data: bytes | None
    stamp: tuple | None

    @classmethod
    def read(cls, path: Path):
        try:
            with path.open('rb') as f:
                before = os.fstat(f.fileno()); data = f.read(); after = os.fstat(f.fileno())
            stamp = lambda s: (s.st_dev, s.st_ino, s.st_mtime_ns, s.st_size)
            if stamp(before) != stamp(after): raise ExternalChange('読み込み中にログが変更されました。再度読み込んでください。')
            if stamp(path.stat()) != stamp(after): raise ExternalChange('読み込み中にログが置き換えられました。')
            return cls(data, stamp(after))
        except FileNotFoundError:
            if path.exists(): raise ExternalChange('読み込み中にログの状態が変わりました。')
            return cls(None, None)

    def check(self, path):
        current = Snapshot.read(path)
        # Metadata alone (mtime/inode bookkeeping, antivirus/indexer touches, or
        # a same-content rewrite) must not block a safe save.  We only reject
        # when the bytes actually changed since the snapshot was taken.
        if current.data != self.data:
            raise ExternalChange('ファイルの内容が変更されています。再度読み込んでください。')

@contextmanager
def operation_lock(directory: Path):
    """Kernel-owned lock; no stale lock file after a crash. Cooperating writers.

    Linux locks the data directory inode; Windows uses a named mutex. Arbitrary
    editors do not obey this lock, so recheck immediately before replacement.
    """
    directory.mkdir(parents=True, exist_ok=True)
    if os.name == 'nt':
        import ctypes
        from ctypes import wintypes
        k = ctypes.WinDLL('kernel32', use_last_error=True)
        k.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
        k.CreateMutexW.restype = wintypes.HANDLE
        k.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        k.WaitForSingleObject.restype = wintypes.DWORD
        k.ReleaseMutex.argtypes = [wintypes.HANDLE]; k.CloseHandle.argtypes = [wintypes.HANDLE]
        name = hashlib.sha256(str(directory.resolve()).casefold().encode()).hexdigest()
        handle = k.CreateMutexW(None, False, 'Local\\PSLog_' + name)
        if not handle: raise StorageError('保存用ミューテックスを作成できません。')
        acquired = False
        try:
            result = k.WaitForSingleObject(handle, 0)
            if result not in (0, 0x80): raise StorageError('別のPSLogが保存中です。再度操作してください。')
            acquired = True
            if directory.name in ('logbook','logbook_flr'):
                from year_move import recover_locked
                recover_locked(directory)
                if directory.name == 'logbook':
                    from batch_recovery import recover_locked as recover_batch
                    recover_batch(directory)
            yield
        finally:
            if acquired: k.ReleaseMutex(handle)
            k.CloseHandle(handle)
    else:
        import fcntl
        fd = os.open(directory, os.O_RDONLY)
        try:
            try: fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as e: raise StorageError('別のPSLogが保存中です。') from e
            if directory.name in ('logbook','logbook_flr'):
                from year_move import recover_locked
                recover_locked(directory)
                if directory.name == 'logbook':
                    from batch_recovery import recover_locked as recover_batch
                    recover_batch(directory)
            yield
        finally: os.close(fd)

def replace_bytes(path: Path, data: bytes, expected: Snapshot):
    """Temp + fsync + atomic replace. New files use exclusive hard-link creation."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix='.pslog-', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(data); f.flush(); os.fsync(f.fileno())
        if Path(temp).read_bytes() != data: raise StorageError('一時ファイルの照合に失敗しました。')
        expected.check(path)
        if expected.data is None:
            try: os.link(temp, path)  # Fails rather than overwriting a new competing file.
            except FileExistsError as e: raise ExternalChange('保存先が新たに作成されました。再読込してください。') from e
        else: os.replace(temp, path)
    finally:
        Path(temp).unlink(missing_ok=True)

class Repository:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.book = self.root / 'logbook'; self.free_book = self.root / 'logbook_flr'; self.bak = self.root / 'bak'
        self.output = self.root / 'output'; self.contest_output = self.output / 'contest'
        self.export_output = self.output / 'export'; self.pota_output = self.output / 'pota'; self.sota_output = self.output / 'sota'
        self.started = set(); self.changed = set()
        self.backup_keep = 30

    def path_for(self, call, suffix, date):
        call = validate_station(call, suffix)
        year = datetime.strptime(date, '%Y-%m-%d').year
        return self.book / f'{year:04d}_{call.replace("/", "-")}_{suffix}.txt'

    def recover(self):
        # Taking each kernel lock completes any previously persisted year-change intent.
        with operation_lock(self.book):pass
        with operation_lock(self.free_book):pass

    def files(self, call):
        call = validate_station(call, '')
        prefix = re.compile(r'^\d{4}_' + re.escape(call.replace('/', '-')) + r'_.*\.txt$')
        return sorted(p for p in self.book.glob('*.txt') if prefix.fullmatch(p.name))

    def open(self, path, for_restore=False):
        path = Path(path).resolve()
        if path.parent not in (self.book,self.free_book): raise StorageError('logbook または logbook_flr 直下のファイルを指定してください。')
        snap = Snapshot.read(path)
        try: log = parse(snap.data or b'')
        except InvalidLog as e:
            if not for_restore: raise
            log = Log([], [Issue(0, str(e), '')], [], False, '\r\n')
        return Session(self, path, snap, log)

    def backup(self, path, data):
        if data is None: return None
        self.bak.mkdir(parents=True, exist_ok=True)
        old = self.backups(path)
        if old and old[-1].read_bytes() == data: return old[-1]
        # datetime.now() can return the same microsecond repeatedly on Windows.
        # Backup ordering is filename-based, so force the timestamp component to
        # advance beyond every existing backup for this log before adding UUID.
        now = datetime.now()
        prefix = path.name + '.'
        latest = None
        for item in old:
            stamp_text = item.name[len(prefix):len(prefix) + 22]
            try: stamp_value = datetime.strptime(stamp_text, '%Y%m%d-%H%M%S-%f')
            except ValueError: continue
            if latest is None or stamp_value > latest: latest = stamp_value
        if latest is not None and now <= latest: now = latest + timedelta(microseconds=1)
        name = path.name + '.' + now.strftime('%Y%m%d-%H%M%S-%f') + '-' + uuid.uuid4().hex[:8] + '.bak'
        dest = self.bak / name
        with dest.open('xb') as f:
            f.write(data); f.flush(); os.fsync(f.fileno())
        if dest.read_bytes() != data: raise StorageError('バックアップ照合に失敗しました。原本は変更しません。')
        return dest

    def backups(self, path):
        return sorted(p for p in self.bak.glob('*.bak') if p.name.startswith(path.name + '.'))

    def prune(self, path):
        # Only prune after a successful save, never before current-state protection.
        for old in self.backups(path)[:-self.backup_keep]: old.unlink()

    def close(self):
        errors = []
        for directory in (self.book,self.free_book):
            paths=[p for p in self.changed if p.parent==directory]
            if not paths:continue
            with operation_lock(directory):
                for p in paths:
                    try: self.backup(p, Snapshot.read(p).data); self.prune(p)
                    except OSError as e: errors.append(f'{p.name}: {e}')
        return errors

class Session:
    def __init__(self, repo, path, snapshot, log):
        self.repo, self.path, self.snapshot, self.log = repo, path, snapshot, log

    def _commit(self, data, destructive=False):
        with operation_lock(self.path.parent):
            self.snapshot.check(self.path)
            if destructive or self.path not in self.repo.started:
                self.repo.backup(self.path, self.snapshot.data)
            replace_bytes(self.path, data, self.snapshot)
            self.repo.started.add(self.path); self.repo.changed.add(self.path)
            self.snapshot = Snapshot.read(self.path); self.log = parse(self.snapshot.data or b'')
            # Retention cleanup is secondary: a failure must not report the QSO as unsaved.
            try: self.repo.prune(self.path)
            except OSError: pass

    def _editable(self):
        if self.log.issues: raise InvalidLog('解釈できない行があります。確認・修正してから再度読み込んでください。')

    def append(self, qso):
        self._editable(); line = qso.to_ps()
        if self.path.name[:4] != qso.date[:4]: raise StorageError('QSOの年と保存先の年が一致しません。')
        existing = self.snapshot.data
        if existing is None:
            data = b'\xef\xbb\xbf' + (line + '\r\n').encode('utf-8')
        else:
            sep = b'' if not existing or existing.endswith((b'\r',b'\n',b'\xef\xbb\xbf')) else self.log.newline.encode()
            data = existing + sep + (line + self.log.newline).encode('utf-8')
        self._commit(data)

    def edit(self, line_number, qso=None):
        self._editable()
        if not 1 <= line_number <= len(self.log.lines) or not self.log.lines[line_number-1].qso:
            raise StorageError('交信行を選択してください。')
        if qso and qso.date[:4] != self.path.name[:4]:
            from year_move import move
            return move(self,line_number,qso)
        new = list(self.log.lines)
        old = new[line_number-1].raw
        ending = '\r\n' if old.endswith('\r\n') else '\n' if old.endswith('\n') else '\r' if old.endswith('\r') else ''
        new[line_number-1] = ParsedLine(qso.to_ps() + ending if qso else '')
        body = ''.join(l.raw for l in new).encode('utf-8')
        self._commit((b'\xef\xbb\xbf' if self.log.bom else b'') + body, destructive=True)

    def restore(self, backup_path, expected_backup=None):
        backup_path = Path(backup_path).resolve()
        if backup_path.parent != self.repo.bak or not backup_path.name.startswith(self.path.name + '.'):
            raise StorageError('このログのバックアップを選択してください。')
        source = Snapshot.read(backup_path)
        if expected_backup is not None and source != expected_backup:
            raise ExternalChange('確認後にバックアップが変更されました。一覧を再読み込みしてください。')
        if source.data is None: raise StorageError('バックアップが見つかりません。')
        data = source.data
        if parse(data).issues: raise InvalidLog('復元するバックアップに解釈できない行があります。')
        self._commit(data, destructive=True)

def duplicate_key(q):
    return q.date, q.time, q.call.upper(), q.band, q.mode.upper()

def import_plan(repo, source, call, suffix='', all_add=False):
    """Read-only annual plan. Source sections require human self-call review."""
    log = parse(Path(source).read_bytes())
    plans = {}
    for _, q in log.records:
        path = repo.path_for(call, suffix, q.date)
        if path not in plans:
            session = repo.open(path)
            plans[path] = {'session':session, 'records':[], 'skipped':0,
                           'keys':{duplicate_key(r) for _,r in session.log.records}}
        plan = plans[path]; key = duplicate_key(q)
        if key in plan['keys'] and not all_add: plan['skipped'] += 1
        else: plan['records'].append(q); plan['keys'].add(key)
    return log, plans

def save_settings(root, values, expected=None):
    path = Path(root) / 'config' / 'conf.cfg'
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with operation_lock(path.parent):
            replace_bytes(path, json.dumps(values, ensure_ascii=False, indent=2).encode(), Snapshot.read(path) if expected is None else expected)
    except ExternalChange as e:
        raise ExternalChange('設定ファイルの内容が変更されています。設定画面を開き直して再度保存してください。') from e

def load_settings(root):
    path = Path(root) / 'config' / 'conf.cfg'
    if not path.exists(): return {}
    try:
        value = json.loads(path.read_text('utf-8'))
        if not isinstance(value, dict): raise ValueError('設定がオブジェクトではありません。')
        return value
    except (ValueError, UnicodeError) as e: raise StorageError('設定ファイルを読み込めません。元ファイルを確認してください。') from e
