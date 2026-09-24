"""Durable batch intent, including original QSL result flags and final reports.

The caller holds logbook's kernel lock. No source import is replayed on recovery.
"""
import base64,hashlib,json,uuid
from pathlib import Path
from storage import Snapshot,StorageError,ExternalChange,replace_bytes,parse
from year_move import sync_directory

def digest(data):return None if data is None else hashlib.sha256(data).hexdigest()
def encode(data):return base64.b64encode(data).decode('ascii')

class Intent:
    def __init__(self,path,data,snapshot):self.path=path;self.data=data;self.snapshot=snapshot
    def save(self):
        replace_bytes(self.path,json.dumps(self.data,ensure_ascii=False).encode(),self.snapshot)
        self.snapshot=Snapshot.read(self.path);sync_directory(self.path.parent)
    def allow(self,outputs):
        # Record the next report version before it can be written.
        for path,payload in outputs.items():
            row=next(x for x in self.data['outputs'] if x['path']==str(path))
            value=digest(payload)
            if value not in row['allowed']:row['allowed'].append(value)
        self.save()
    def finish(self):
        for parent in {Path(row['path']).parent for category in ('logs','outputs') for row in self.data[category]}:sync_directory(parent)
        self.snapshot.check(self.path)
        dest=self.path.with_name(self.path.name.replace('.pending.json','.done.json'))
        if dest.exists():raise StorageError('回復記録の完了先が既にあります。')
        self.path.rename(dest);sync_directory(dest.parent)

def create(repo,kind,targets,outputs):
    directory=repo.bak/'batch_recovery'
    if directory.is_symlink():raise StorageError('回復記録フォルダーがリンクです。')
    directory.mkdir(parents=True,exist_ok=True)
    data={'schema':1,'kind':kind,'logs':[],'outputs':[]}
    for path,before,after in targets:
        before.check(path)
        data['logs'].append({'path':str(path),'before':digest(before.data),'after':encode(after)})
    for path,after in outputs.items():
        snap=Snapshot.read(path)
        data['outputs'].append({'path':str(path),'allowed':[digest(snap.data),digest(after)],'after':encode(after)})
    intent=Intent(directory/(uuid.uuid4().hex+'.pending.json'),data,Snapshot(None,None));intent.save();return intent

def recover_locked(book):
    directory=book.parent/'bak'/'batch_recovery'
    if directory.is_symlink():raise StorageError('回復記録フォルダーがリンクです。')
    for path in sorted(directory.glob('*.pending.json')):
        snap=Snapshot.read(path)
        try:
            data=json.loads(snap.data)
            if set(data)!= {'schema','kind','logs','outputs'} or data['schema']!=1 or data['kind'] not in ('import','qsl','delete','jccjcg'):raise ValueError('形式')
            plans=[];seen=set()
            for category in ('logs','outputs'):
                for row in data[category]:
                    target=Path(row['path'])
                    if not target.is_absolute() or target.is_symlink() or target.resolve()!=target or target in seen:raise ValueError('保存先')
                    seen.add(target)
                    if category=='logs':
                        if target.parent!=book or target.suffix!='.txt':raise ValueError('原本の保存先')
                    elif target.is_relative_to(book) or target.is_relative_to(book.parent/'config') or target.suffix not in ('.json','.csv'):
                        raise ValueError('結果の保存先')
                    after=base64.b64decode(row['after'],validate=True)
                    if category=='logs' and parse(after).issues:raise ValueError('原本データ')
                    allowed=[row['before'],digest(after)] if category=='logs' else row['allowed']
                    current=Snapshot.read(target)
                    if digest(current.data) not in allowed:
                        raise ExternalChange('一括処理後に原本または結果ファイルが外部変更されています。上書きせず停止しました。\n'+str(target)+'\n回復記録: '+str(path))
                    plans.append((target,current,after))
            # Preflight all logs AND reports before any recovery mutation.
            for target,current,after in plans:
                snap.check(path)
                if current.data!=after:replace_bytes(target,after,current)
                else:current.check(target)
                sync_directory(target.parent)
            Intent(path,data,snap).finish()
        except (ValueError,KeyError,TypeError,UnicodeError) as e:
            raise StorageError('一括処理の回復記録が不正です。保全して確認してください: '+str(path)) from e
