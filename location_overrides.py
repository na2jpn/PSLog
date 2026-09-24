"""User-confirmed romanizations, separate from the supplied reference master."""
from pathlib import Path
from copy import deepcopy
from datetime import datetime,timezone
import json
from storage import Snapshot,StorageError,replace_bytes,operation_lock

def identity(row):return row['kind'],row['source_code'],row['name']
def qth(value):
    value=value.strip()
    if not value or not value.isascii() or any(ord(c)<32 or ord(c)==127 or c=='|' for c in value):raise ValueError('所在地は区切り文字・制御文字を含まない半角ローマ字で入力してください。')
    return value

class Overrides:
    def __init__(self,root):
        self.path=Path(root)/'config/db/location_overrides.json';self.snapshot=Snapshot.read(self.path)
        try:
            self.values=json.loads(self.snapshot.data.decode('utf-8-sig')) if self.snapshot.data else {'schema':1,'rows':[]}
            if not isinstance(self.values,dict) or set(self.values)!= {'schema','rows'} or type(self.values['schema']) is not int or self.values['schema']!=1 or not isinstance(self.values['rows'],list):raise ValueError('保存形式が不正です。')
            seen=set()
            for row in self.values['rows']:
                if not isinstance(row,dict) or set(row)!= {'kind','source_code','name','qth','confirmed_at'} or any(not isinstance(v,str) for v in row.values()):raise ValueError('保存項目が不正です。')
                if row['kind'] not in ('JCC','JCG') or not row['source_code'] or not row['name'] or identity(row) in seen:raise ValueError('所在地が重複または不正です。')
                qth(row['qth']);seen.add(identity(row))
        except (ValueError,UnicodeError,TypeError,KeyError) as e:raise StorageError('確認済み所在地の設定を読み込めません: '+str(e)) from e
    def remember(self,row,text):
        item={'kind':row['kind'],'source_code':row['source_code'],'name':row['name'],'qth':qth(text),'confirmed_at':datetime.now(timezone.utc).isoformat()};values=deepcopy(self.values);values['rows']=[r for r in values['rows'] if identity(r)!=identity(row)]+[item];self.commit(values)
    def forget(self,row):
        values=deepcopy(self.values);values['rows']=[r for r in values['rows'] if identity(r)!=identity(row)];self.commit(values)
    def commit(self,values):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with operation_lock(self.path.parent):
            self.snapshot.check(self.path)
            if self.snapshot.data is not None:
                history=self.path.parent/'history'/('location_overrides_'+datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')+'.json');replace_bytes(history,self.snapshot.data,Snapshot(None,None))
            replace_bytes(self.path,(json.dumps(values,ensure_ascii=False,indent=2)+'\n').encode('utf-8'),self.snapshot)
        self.values=values;self.snapshot=Snapshot.read(self.path)

def merge(data,root):
    overrides=Overrides(root);known={identity(r):r for r in data['rows']};data['override_notices']=[]
    for r in overrides.values['rows']:
        row=known.get(identity(r))
        if row is None:data['override_notices'].append(r['name']+'（現在のDBに一致せず適用していません）');continue
        row['verified_qth']=r['qth'];row['qth_source']='ユーザー確認済み';row['confirmed_at']=r['confirmed_at']
    overrides.snapshot.check(overrides.path);return data
