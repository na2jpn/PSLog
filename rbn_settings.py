"""Shared five-slot RBN configuration; no network access while loading."""
import copy,json,re
from pathlib import Path
from PySide6.QtCore import QObject,Signal
from PySide6.QtWidgets import QApplication
from storage import Snapshot,replace_bytes,operation_lock
from cluster_monitor import valid_token
from logbook_sources import amateur_station_calls
PROFILES={
 'AR-Cluster':['set dx filt'],
 'CC Cluster':['set/skimmer','set/cw','set/rtty','set/ft4','set/ft8'],
 'DXSpider':['set/skimmer'],
 '設定なし':[],
}
DEFAULT_NODES=[
 dict(slot='A',name='日本① JG1VGX-8',host='arc.jg1vgx.net',port=7000,profile='AR-Cluster',enabled=True),
 dict(slot='B',name='日本② JG1VGX-7',host='ccc.jg1vgx.net',port=7373,profile='CC Cluster',enabled=True),
 dict(slot='C',name='中国（上海） BH4HKZ',host='spots.bh4hkz.com',port=7373,profile='AR-Cluster',enabled=True),
 dict(slot='D',name='ロシア UA0APV-1',host='ua0apv.i234.me',port=7300,profile='DXSpider',enabled=True),
 dict(slot='E',name='米国 W3LPL-1',host='dxc.w3lpl.net',port=7373,profile='AR-Cluster',enabled=True),
]
def validate(data):
 if not isinstance(data,dict) or not isinstance(data.get('nodes'),list) or len(data['nodes'])!=5:raise ValueError('RBN設定にはA〜Eの5枠が必要です。')
 result={'schema':1,'own':str(data.get('own','')).strip().upper(),'nodes':[]}
 seen=set()
 for slot,node in zip('ABCDE',data['nodes']):
  if not isinstance(node,dict):raise ValueError(f'{slot}の設定形式が不正です。')
  host=str(node.get('host','')).strip().lower();enabled=bool(node.get('enabled',False));profile=node.get('profile','設定なし')
  try:port=int(node.get('port',0))
  except (ValueError,TypeError):raise ValueError(f'{slot}のポート番号が不正です。')
  if profile not in PROFILES:raise ValueError(f'{slot}のソフト種別が不正です。')
  if not 1<=port<=65535:raise ValueError(f'{slot}のポートは1〜65535です。')
  if host and not re.fullmatch(r'[a-z0-9][a-z0-9.-]{0,252}',host):raise ValueError(f'{slot}の接続先が不正です。')
  if enabled:
   if not host:raise ValueError(f'{slot}の接続先を入力してください。')
   if (host,port) in seen:raise ValueError('有効な接続先のホスト・ポートが重複しています。')
   seen.add((host,port))
  result['nodes'].append(dict(slot=slot,name=str(node.get('name',slot))[:100],host=host,port=port,profile=profile,enabled=enabled))
 if result['own'] and not valid_token(result['own'],'call'):raise ValueError('ログインコールの形式を確認してください。例：JX1XXX')
 return result

class RbnSettings(QObject):
 changed=Signal()
 def __init__(self,repo,parent=None):
  super().__init__(parent);self.path=Path(repo.root)/'config/rbn.json';self.snapshot=Snapshot.read(self.path);self.error=''
  calls=amateur_station_calls(repo);self.data={'schema':1,'own':calls[0] if calls else '','nodes':copy.deepcopy(DEFAULT_NODES)}
  try:
   if self.snapshot.data:
    self.data=validate(json.loads(self.snapshot.data.decode('utf-8')))
    node=self.data['nodes'][2]
    # Replace only the untouched FIX1 Korean preset; keep custom endpoints.
    if node['host']=='dxc.dx.or.kr' and node['port']==23 and node['profile']=='設定なし':self.data['nodes'][2]=copy.deepcopy(DEFAULT_NODES[2])
   else:
    own_migrated=False
    for name in ('cluster_monitor.json','band_site.json'):
     legacy=self.path.parent/name
     if not legacy.exists():continue
     old=json.loads(legacy.read_text(encoding='utf-8'))
     if not own_migrated and old.get('own'):self.data['own']=old['own'];own_migrated=True
     if old.get('host') and old['host']!='arc.jg1vgx.net':
      self.data['nodes'][0].update(host=old['host'],port=old.get('port',7000),name='日本①（従来の接続先）');break
    self.data=validate(self.data)
  except Exception as e:self.error='RBN設定を読めません。元ファイルを保持します：'+str(e)
 def save(self,data):
  if self.error:raise ValueError(self.error)
  data=validate(data);self.path.parent.mkdir(parents=True,exist_ok=True)
  with operation_lock(self.path.parent):replace_bytes(self.path,(json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode('utf-8'),self.snapshot)
  self.snapshot=Snapshot.read(self.path);self.data=data;self.changed.emit()
 def validate_start(self):
  if self.error:raise ValueError(self.error)
  if not self.data['own']:raise ValueError('RBN設定でログインコールを保存してください。')
  if not any(n['enabled'] for n in self.data['nodes']):raise ValueError('RBN設定で接続先を1つ以上有効にしてください。')

def get_settings(repo):
 app=QApplication.instance()
 if not hasattr(app,'_pslog_rbn_settings'):app._pslog_rbn_settings={}
 key=str(Path(repo.root).resolve())
 if key not in app._pslog_rbn_settings:app._pslog_rbn_settings[key]=RbnSettings(repo,app)
 return app._pslog_rbn_settings[key]
