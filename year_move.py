"""Recoverable cross-year edits. A pending journal is an intent, not a lock.

Called with the logbook kernel lock held. Recovery finishes the saved edit only
when both files still match a recorded before/after image.
"""
import base64,json,os,re,uuid
from pathlib import Path
from storage import Snapshot,StorageError,ExternalChange,parse,replace_bytes,operation_lock

def sync_directory(path):
    if os.name!='nt':
        fd=os.open(path,os.O_RDONLY)
        try:os.fsync(fd)
        finally:os.close(fd)

def folder(book):
    # Keep the historical amateur journal path unchanged; free-radio moves use
    # a separate journal so recovery can never replay a logbook move into
    # logbook_flr (or vice versa).
    return book.parent/'bak'/('year_moves_flr' if Path(book).name=='logbook_flr' else 'year_moves')
def encoded(data):return None if data is None else base64.b64encode(data).decode('ascii')
def decoded(value):return None if value is None else base64.b64decode(value,validate=True)

def recover_locked(book):
    directory=folder(book)
    if directory.is_symlink():raise StorageError('年変更の回復記録フォルダーがリンクです。')
    completed=[]
    for journal in sorted(directory.glob('*.pending.json')):
        try:
            if journal.is_symlink():raise ValueError('回復記録がリンクです。')
            snap=Snapshot.read(journal);data=json.loads(snap.data)
            if set(data)!= {'schema','files'} or data['schema']!=1 or len(data['files'])!=2:raise ValueError('不正な回復記録')
            plans=[];names=set()
            for item in data['files']:
                if set(item)!={'name','before','after'}:raise ValueError('不正な項目')
                name=item['name']
                if (not re.fullmatch(r'[0-9]{4}_[^/\\\x00]+\.txt',name) or name in names
                        or name in ('.','..')):raise ValueError('不正な保存先')
                names.add(name);path=book/name
                if path.is_symlink():raise ValueError('保存先がリンクです。')
                before,after=decoded(item['before']),decoded(item['after'])
                if after is None or parse(after).issues:raise ValueError('変更後ログが不正です。')
                current=Snapshot.read(path)
                if current.data not in (before,after):raise ExternalChange('年変更の途中で原本が外部変更されています。回復記録と原本を確認してください: '+str(journal))
                plans.append((path,current,after))
            # Validate both before touching either; recheck each again before replacing.
            for path,current,after in plans:
                snap.check(journal)
                if current.data!=after:replace_bytes(path,after,current)
                else:current.check(path)
            sync_directory(book)
            snap.check(journal)
            done=journal.with_name(journal.name.replace('.pending.json','.done.json'))
            if done.exists():raise StorageError('回復済み記録と名前が重複しています。')
            journal.rename(done);sync_directory(directory);completed.append(done)
        except (ValueError,TypeError,KeyError,UnicodeError) as e:
            raise StorageError('年変更の回復記録を読み込めません。原本を変更せず確認してください: '+str(journal)) from e
    return completed

def move(session,line_number,qso):
    # Validate the new QSO before creating any intent or modifying either log.
    line=qso.to_ps();repo=session.repo
    book=session.path.parent
    if book not in (repo.book,repo.free_book):raise StorageError("年変更できないログ保存先です。")
    target=book/(qso.date[:4]+session.path.name[4:])
    with operation_lock(book):
        session.snapshot.check(session.path)
        dest=repo.open(target);dest._editable()
        original=session.log.lines
        source_after=(b'\xef\xbb\xbf' if session.log.bom else b'')+''.join(x.raw for i,x in enumerate(original,1) if i!=line_number).encode('utf-8')
        before=dest.snapshot.data
        if before is None:target_after=b'\xef\xbb\xbf'+(line+'\r\n').encode('utf-8')
        else:
            sep=b'' if not before or before.endswith((b'\r',b'\n',b'\xef\xbb\xbf')) else dest.log.newline.encode()
            target_after=before+sep+(line+dest.log.newline).encode('utf-8')
        repo.backup(session.path,session.snapshot.data);repo.backup(target,before)
        session.snapshot.check(session.path);dest.snapshot.check(target)
        directory=folder(book)
        if directory.is_symlink():raise StorageError('回復記録フォルダーがリンクです。')
        directory.mkdir(parents=True,exist_ok=True)
        journal=directory/(uuid.uuid4().hex+'.pending.json')
        # Destination first: interruption never leaves the QSO absent from both files.
        data={'schema':1,'files':[
            {'name':target.name,'before':encoded(before),'after':encoded(target_after)},
            {'name':session.path.name,'before':encoded(session.snapshot.data),'after':encoded(source_after)}]}
        replace_bytes(journal,json.dumps(data,ensure_ascii=False).encode('utf-8'),Snapshot(None,None))
        sync_directory(directory)
        try:recover_locked(book)
        except (StorageError,OSError) as e:
            raise StorageError('年変更は途中状態です。再保存せず「ログを再読込」で回復してください。\n'+str(journal)+'\n'+str(e)) from e
        repo.started.update((session.path,target));repo.changed.update((session.path,target))
        session.snapshot=Snapshot.read(session.path);session.log=parse(session.snapshot.data or b'')
        return target
