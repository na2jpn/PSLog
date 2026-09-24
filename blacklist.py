"""Advisory-only callsign list, separate from canonical QSO logs."""
import json,unicodedata
from dataclasses import dataclass,asdict
from pathlib import Path
from storage import Snapshot,StorageError,operation_lock,replace_bytes
from model import validate_station

@dataclass(frozen=True)
class Entry:
    call: str
    memo: str = ''
    portable: bool = False
    def normalized(self):
        call=validate_station(unicodedata.normalize('NFKC',self.call).strip(),'')
        if not isinstance(self.memo,str) or '\x00' in self.memo:raise ValueError('メモの形式が不正です。')
        if type(self.portable) is not bool:raise ValueError('移動運用の指定が不正です。')
        return Entry(call,self.memo,self.portable)
    def matches(self,call):
        call=unicodedata.normalize('NFKC',call).strip().upper()
        return call==self.call or (self.portable and call.startswith(self.call+'/'))

class Blacklist:
    def __init__(self,root):
        self.path=Path(root).resolve()/'config'/'blacklist.json'
        self.reload()
    def reload(self):
        snap=Snapshot.read(self.path);entries=[]
        if snap.data is not None:
            try:
                data=json.loads(snap.data.decode('utf-8-sig'))
                if not isinstance(data,dict) or data.get('version')!=1 or not isinstance(data.get('entries'),list):raise ValueError('未対応の形式です。')
                for item in data['entries']:
                    if not isinstance(item,dict) or set(item)-{'call','memo','portable'}:raise ValueError('登録項目が不正です。')
                    entries.append(Entry(**item).normalized())
                if len({e.call for e in entries})!=len(entries):raise ValueError('コールサインが重複しています。')
            except (ValueError,TypeError,UnicodeError,AttributeError) as e:raise StorageError('ブラックリストを読めません。元ファイルは変更しません。 '+str(e)) from e
        self.snapshot=snap;self.entries=entries
    def matching(self,call):return [e for e in self.entries if e.matches(call)]
    def update(self,entry=None,original=None):
        entries=list(self.entries)
        if original is not None:
            found=[i for i,e in enumerate(entries) if e.call==original]
            if not found:raise StorageError('登録が見つかりません。一覧を再読み込みしてください。')
            entries.pop(found[0])
        if entry is not None:
            entry=entry.normalized()
            if any(e.call==entry.call for e in entries):raise ValueError('同じコールサインは登録済みです。')
            entries.append(entry)
        elif original is None:raise ValueError('登録を選択してください。')
        entries.sort(key=lambda e:e.call)
        data=json.dumps({'version':1,'entries':[asdict(e) for e in entries]},ensure_ascii=False,indent=2).encode()
        with operation_lock(self.path.parent):replace_bytes(self.path,data,self.snapshot)
        self.snapshot=Snapshot.read(self.path);self.entries=entries
