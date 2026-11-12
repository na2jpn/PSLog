"""Unreceived QSL rows and snapshot-checked BURO edits in amateur logs."""
from dataclasses import dataclass,replace
from pathlib import Path
import re
from input_normalization import callsign
from logbook_sources import file_identity
from qsl_marks import tokens,TOKEN
from remarks_sections import primary,replace_primary
from storage import StorageError

RECEIPT=re.compile(r'(?<![\w./-])[A-Za-z0-9][A-Za-z0-9_-]*\.R(?![\w./-])',re.I)

def received(remarks):
    return bool(RECEIPT.search(primary(remarks)))

def has_buro(remarks):
    return 'buro' in tokens(remarks)

def set_buro(remarks,on):
    first=primary(remarks)
    if on:
        if has_buro(remarks):return remarks
        first+=(' ' if first and not first[-1].isspace() else '')+'BURO'
    else:
        first=TOKEN.sub(lambda m:'' if m.group().casefold()=='buro' else m.group(),first).rstrip()
    return replace_primary(remarks,first)

@dataclass
class Row:
    path:Path
    snapshot:object
    line:int
    raw:str
    qso:object

def collect(repo,paths,month=0,call='',exclude_buro=False):
    if type(month) is not int or not 0<=month<=12:raise StorageError('月はすべて又は1～12を指定してください。')
    paths=list(paths)
    if any(Path(p).is_symlink() for p in paths):raise StorageError('リンクではなく元ログを選択してください。')
    paths=list(dict.fromkeys(Path(p).resolve() for p in paths))
    if not paths:raise StorageError('対象ログファイルを選択してください。')
    pattern=callsign(call);rows=[]
    for path in paths:
        if path.parent!=repo.book or path.is_symlink() or not file_identity(path) or not path.is_file():raise StorageError('logbook内の既存アマチュアログを選択してください。')
        session=repo.open(path)
        if session.log.issues:raise StorageError(path.name+' に読めない行があります。ログを確認してください。')
        for n,line in enumerate(session.log.lines,1):
            q=line.qso
            if q is None or received(q.remarks):continue
            if month and q.date[5:7]!=f'{month:02d}':continue
            if pattern and pattern not in q.call.upper():continue
            if exclude_buro and has_buro(q.remarks):continue
            rows.append(Row(path,session.snapshot,n,line.raw,q))
    rows.sort(key=lambda x:(x.qso.date,x.qso.time,x.path.name,x.line))
    return rows

def toggle(repo,row):
    """A displayed snapshot must still match; never adopt external edits."""
    row.snapshot.check(row.path)
    session=repo.open(row.path)
    if session.snapshot!=row.snapshot:raise StorageError('表示後にログが変更されました。再表示してください。')
    if not 1<=row.line<=len(session.log.lines):raise StorageError('対象行がありません。再表示してください。')
    current=session.log.lines[row.line-1]
    if current.raw!=row.raw or current.qso is None or received(current.qso.remarks):raise StorageError('対象行が変わりました。再表示してください。')
    if current.qso.date[:4]!=row.path.name[:4]:raise StorageError('ログファイルの年と交信年が一致しません。検索画面で確認してください。')
    on=not has_buro(current.qso.remarks)
    session.edit(row.line,replace(current.qso,remarks=set_buro(current.qso.remarks,on)),allow_nonstandard_rst=True)
    return on
