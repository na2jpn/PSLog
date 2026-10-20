"""Persistent award applications, independent of QSL receipt and log files."""
import json
from pathlib import Path
from storage import Snapshot,replace_bytes,operation_lock,StorageError
from logbook_sources import base_station_call

class Applications:
    def __init__(self,root):self.path=Path(root)/'config'/'award_applications.json'
    def _read(self):
        snap=Snapshot.read(self.path)
        if snap.data is None:return snap,{}
        try:
            data=json.loads(snap.data.decode('utf-8'))
            if data.get('schema')!=1 or not isinstance(data.get('entries'),dict):raise ValueError('unknown format')
            return snap,data['entries']
        except (ValueError,TypeError,AttributeError) as e:raise StorageError('アワード申請済データを読めません: '+str(e)) from e
    @staticmethod
    def key(own,award,unit,band='*'):
        return json.dumps([base_station_call(own),str(award),str(unit),str(band)],ensure_ascii=False)
    def entries(self):return self._read()[1]
    def checked(self,own,award,unit,band='*',entries=None):
        return bool((self.entries() if entries is None else entries).get(self.key(own,award,unit,band),False))
    def set(self,own,award,unit,band,checked):
        if not base_station_call(own):raise ValueError('自局コールを選択してください')
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with operation_lock(self.path.parent):
            snap,entries=self._read();key=self.key(own,award,unit,band)
            if checked:entries[key]=True
            else:entries.pop(key,None)
            replace_bytes(self.path,(json.dumps({'schema':1,'entries':entries},ensure_ascii=False,indent=2)+'\n').encode('utf-8'),snap)
