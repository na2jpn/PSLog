"""Search and selected-record identity, independent of Qt."""
from dataclasses import dataclass, replace
from pathlib import Path
import re
import unicodedata
from model import validate_station
from input_normalization import jccjcg_code
from storage import ExternalChange, StorageError, operation_lock, replace_bytes
from time_range import prefix_boundary
from logbook_sources import file_identity,base_station_call,amateur_station_calls,amateur_log_files

@dataclass(frozen=True)
class Criteria:
    own: str
    portable: bool = False
    filename: str = ''
    call: str = ''
    remarks: str = ''
    his_qth: str = ''
    my_qth: str = ''
    jccjcg: str = ''
    band: str = ''
    mode: str = ''
    start: str = ''
    end: str = ''

    def validate(self):
        validate_station(self.own, '')
        try:
            start_key=prefix_boundary(self.start,False,12)
        except ValueError as e:
            raise ValueError('開始'+str(e)) from e
        try:
            end_key=prefix_boundary(self.end,True,12)
        except ValueError as e:
            raise ValueError('終了'+str(e)) from e
        if start_key and end_key and start_key>end_key:
            raise ValueError('開始日時は終了日時以前にしてください。')

def _time_prefix_bound(value, upper=False):
    """Backward-compatible wrapper for the shared partial-time parser."""
    return prefix_boundary(value,upper,12)

def normalize_time(value):
    return unicodedata.normalize('NFKC',value).strip()

def station_call_candidates(repo, preferred=''):
    """Backward-compatible public wrapper for amateur station candidates."""
    return amateur_station_calls(repo,preferred)

@dataclass(frozen=True)
class Hit:
    session: object
    snapshot: object
    line: int
    raw: str
    qso: object
    own: str

    @property
    def path(self): return self.session.path
    @property
    def editable(self): return not self.session.log.issues

    def apply(self, qso=None):
        # A new list row index is never used to resolve a previously selected QSO.
        if self.session.snapshot != self.snapshot:
            raise ExternalChange('検索後にログが更新されました。再検索して対象を選び直してください。')
        self.snapshot.check(self.path)
        if self.session.log.lines[self.line-1].raw != self.raw:
            raise ExternalChange('対象行が変わりました。再検索してください。')
        self.session.edit(self.line, qso)



def session_rows(sessions, own):
    """Build embedded-history rows from the current parsed Session objects.

    Session.append/edit reparses a log and replaces every QSO object in that
    session. Rebuild the UI references after a write so they always point at
    the current parsed log rather than stale pre-write objects.
    """
    rows=[]
    for path,session in sessions.items():
        identity=file_identity(path)
        suffix=identity[2] if identity else ''
        for _,qso in session.log.records:
            rows.append(((own,suffix),qso))
    return rows

def embedded_history_hit(sessions, owner, qso):
    """Resolve an embedded LogSearch row safely against current sessions.

    Prefer exact object identity. If a caller still holds a stale QSO after a
    reparse, allow a value-equal fallback only when it identifies exactly one
    current record in the same log-suffix group. Ambiguous duplicates are never
    guessed.
    """
    wanted_suffix=(owner[1] if owner and len(owner)>1 else '') or ''
    equal=[]
    for path,session in sessions.items():
        identity=file_identity(path)
        suffix=identity[2] if identity else ''
        if suffix!=wanted_suffix:
            continue
        for line,record in session.log.records:
            if record is qso:
                return Hit(session,session.snapshot,line,session.log.lines[line-1].raw,record,owner[0])
            if record==qso:
                equal.append((session,line,record))
    if len(equal)==1:
        session,line,record=equal[0]
        return Hit(session,session.snapshot,line,session.log.lines[line-1].raw,record,owner[0])
    return None

@dataclass
class Results:
    hits: list
    problems: list
    files: int

def hits_to_rows(hits):
    """Convert an exact search result into read-only export rows.

    The returned rows preserve the QSO snapshots selected by the search, not
    whole source files.  This lets purpose-specific exporters consume the exact
    filtered result even when the search used CALL/BAND/MODE/QTH filters that
    their standalone screens do not expose.
    """
    sessions=[];seen=set();rows=[]
    for hit in hits:
        key=str(hit.path.resolve())
        if key not in seen:
            seen.add(key);sessions.append(hit.session)
        rows.append((hit.own,replace(hit.qso),hit.path,hit.line))
    rows.sort(key=lambda r:(r[1].date,r[1].time,str(r[2]),r[3]))
    return sessions,rows


def delete_hits(repo, hits):
    """Delete an exact checked search selection as one recoverable batch.

    Every selected row is revalidated against the search snapshot before any
    original log is touched.  Files are backed up first, then a durable batch
    intent is written so an interrupted multi-file deletion can be completed
    safely on recovery.
    """
    hits=list(hits)
    if not hits:
        raise StorageError('削除する交信が選択されていません。')
    targets={}
    seen=set()
    for hit in hits:
        key=(str(hit.path.resolve()),hit.line)
        if key in seen:
            continue
        seen.add(key)
        if not hit.editable:
            raise StorageError('要確認行を含むログがあります。原本を確認・修正してから再検索してください。')
        target=targets.setdefault(hit.path,{'session':hit.session,'hits':[]})
        if target['session'] is not hit.session and target['session'].snapshot != hit.snapshot:
            raise ExternalChange('同じログの検索状態が一致しません。再検索してください。')
        target['hits'].append(hit)
    plans=[]
    for path,target in sorted(targets.items(),key=lambda x:str(x[0])):
        session=target['session']
        if session.log.issues:
            raise StorageError(path.name+' に要確認行があります。削除できません。')
        session.snapshot.check(path)
        lines=set()
        for hit in target['hits']:
            if hit.snapshot != session.snapshot:
                raise ExternalChange('検索後にログが更新されました。再検索して対象を選び直してください。')
            if not 1 <= hit.line <= len(session.log.lines) or session.log.lines[hit.line-1].raw != hit.raw:
                raise ExternalChange('対象行が変わりました。再検索してください。')
            lines.add(hit.line)
        body=''.join(row.raw for i,row in enumerate(session.log.lines,1) if i not in lines).encode('utf-8')
        data=(b'\xef\xbb\xbf' if session.log.bom else b'')+body
        plans.append((path,session,data))
    with operation_lock(repo.book):
        for path,session,_ in plans:
            session.snapshot.check(path)
        for path,session,_ in plans:
            repo.backup(path,session.snapshot.data)
        from batch_recovery import create,recover_locked
        intent=create(repo,'delete',[(path,session.snapshot,data) for path,session,data in plans],{})
        try:
            for path,session,data in plans:
                replace_bytes(path,data,session.snapshot)
                repo.started.add(path);repo.changed.add(path)
            intent.finish()
        except (StorageError,OSError):
            # The confirmed operation has a durable after-state.  Try to finish
            # it immediately; if that is impossible the pending recovery record
            # remains and the next locked log operation will refuse to guess.
            try:
                recover_locked(repo.book)
            except (StorageError,OSError) as recovery_error:
                raise StorageError('一括削除を完了できませんでした。回復記録を保全してログを再読み込みしてください。\n'+str(recovery_error)) from recovery_error
            for path,_,_ in plans:
                repo.started.add(path);repo.changed.add(path)
        for path,_,_ in plans:
            try:repo.prune(path)
            except OSError:pass
    return len(seen)

def search(repo, criteria):
    criteria.validate()
    own = validate_station(criteria.own,'')
    start_key = _time_prefix_bound(criteria.start, False)
    end_key = _time_prefix_bound(criteria.end, True)
    hits, problems, count = [], [], 0
    for path in amateur_log_files(repo):
        identity = file_identity(path)
        if not identity: continue
        actual = identity[1]
        if not (actual == own or (criteria.portable and actual.startswith(own+'/'))): continue
        if criteria.filename.casefold() not in path.name.casefold(): continue
        count += 1
        try: session = repo.open(path)
        except (StorageError,OSError) as e:
            problems.append(f'{path.name}: {e}'); continue
        problems.extend(f'{path.name}:{i.line} {i.reason}' for i in session.log.issues)
        for line,q in session.log.records:
            stamp = q.date.replace('-','') + q.time.replace(':','') + '00'
            if start_key and stamp < start_key: continue
            if end_key and stamp > end_key: continue
            if criteria.call.casefold() not in q.call.casefold(): continue
            if criteria.remarks.casefold() not in q.remarks.casefold(): continue
            if criteria.his_qth.casefold() not in q.his_qth.casefold(): continue
            if criteria.my_qth.casefold() not in q.my_qth.casefold(): continue
            if criteria.jccjcg:
                wanted=jccjcg_code(criteria.jccjcg).casefold()
                actual_code=jccjcg_code(q.code).casefold()
                if wanted not in actual_code: continue
            if criteria.band and criteria.band != q.band: continue
            if criteria.mode.casefold() not in q.mode.casefold(): continue
            hits.append(Hit(session,session.snapshot,line,session.log.lines[line-1].raw,replace(q),actual))
    # Deterministic ties: pathname and original line. No arbitrary result cap.
    hits.sort(key=lambda h:(h.qso.date,h.qso.time,h.path.name,h.line),reverse=True)
    return Results(hits,problems,count)
