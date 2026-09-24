"""Independent award ledgers, editable claims, and six-column QSL lists."""
import csv,io,json,re,hashlib
from pathlib import Path
from datetime import datetime
from storage import Snapshot,replace_bytes,StorageError
from activity_values import band_value,norm
from contest_regional import base_call
from input_normalization import jccjcg_parts
from remarks_sections import primary
AWARDS={k:(k,t) for k,t in [('AJD','area'),('WAJA','pref'),('JCC','city'),('JCG','gun'),('WACA','city'),('WAGA','gun'),('WAKU','ward'),('AJA','aja'),('ADXA','asia'),('ADXA-HALF','asia'),('WASA-HF','grid_hf'),('WASA-V・U・SHF','grid_vu'),('WARC-1000','warc'),('V・U-1000','vu'),('ふじ','fuji'),('JARL Stations J','station'),('JARL Stations A','station'),('JARL Stations R','station'),('JARL Stations L','station')]}
for b in ('0.135','0.475','10','18','24','50','144','430','1200','2400','5600','10000','24000','47000','77000'):AWARDS[b+'MHz賞']=(b+'MHz賞','band:'+b)
from special_awards import SPECIAL_AWARDS
for name in SPECIAL_AWARDS:AWARDS[name]=(name,'special')
AREA={'01':'8','02':'7','03':'7','04':'7','05':'7','06':'7','07':'7','08':'0','09':'0','10':'1','11':'1','12':'1','13':'1','14':'1','15':'1','16':'1','17':'1','18':'2','19':'2','20':'2','21':'2','22':'3','23':'3','24':'3','25':'3','26':'3','27':'3','28':'9','29':'9','30':'9','31':'4','32':'4','33':'4','34':'4','35':'4','36':'5','37':'5','38':'5','39':'5','40':'6','41':'6','42':'6','43':'6','44':'6','45':'6','46':'6','47':'6'}
def region(code,kind):
 typ,num=jccjcg_parts(code)
 digits=re.match(r'^(\d{4,6})',num or '')
 if not typ or not digits:return ''
 num=digits.group(1)
 if kind=='pref':return num[:2]
 if kind=='area':return AREA.get(num[:2],'')
 if kind=='gun':return num[:5] if typ=='JCG' else ''
 if kind=='city':return (num if num.startswith('1001') and len(num)==6 else num[:4]) if typ=='JCC' else ''
 if kind=='ward':return num if typ=='JCC' and len(num)==6 and not num.startswith('1001') else ''
 return ''
def candidate(award,row,countries=None):
 own,q,path,line=row;t=AWARDS[award][1];b=band_value(q.band);unit='';notes=[]
 result={}
 if t=='special':
  from special_awards import special_candidate
  result=special_candidate(award,q,countries);unit=result.pop('unit');notes.append(result.pop('notes')) if result.get('notes') else None
 elif t in ('area','pref','city','gun','ward'):
  unit=region(q.code,t)
  if t=='area' and not unit:
   m=re.search(r'/([0-9])$',q.call) or re.search(r'^[A-Z]+([0-9])',q.call)
   if m:unit=m[1];notes.append('運用エリアをQSLで確認')
  if t=='ward' and q.date<'2010-04-01':notes.append('WAKU有効開始日前')
  if t=='city' and jccjcg_parts(q.code)[0]=='JCC' and jccjcg_parts(q.code)[1].startswith('1001') and q.date<'2010-04-01':notes.append('東京23区の過去計数を確認')
 elif t.startswith('grid'):
  m=re.search(r'(?<![A-Z0-9])([A-R]{2}\d{2})(?:[A-X]{2})?(?![A-Z0-9])',norm(primary(q.remarks)+' '+q.his_qth))
  if m and b is not None and ((t=='grid_hf' and b<=28) or (t=='grid_vu' and b>=50)):unit=m[1]+'@'+q.band
 elif t=='asia':
  c=countries.lookup(q.call) if countries else None
  if c and c['continent']=='AS':unit=c['entity_prefix'];notes.append('現行プリフィックス候補：QSLのエンティティを確認')
 elif t=='station':
  if re.match(r'^(?:8[JN]|JA[0-9](?:RL|YRL|YAA)(?:/|$))',q.call):unit=base_call(q.call)+'@'+q.band+'@'+q.date[:4]+'@'+q.his_qth;notes.append('対象局種・運用場所を確認')
 elif t=='fuji':
  m=re.search(r'FO[- ]?(12|20|29)|JAS[- ]?[12]',norm(primary(q.remarks)))
  if m and norm(q.mode) in ('CW','SSB'):unit=base_call(q.call);notes.append('衛星名・アップリンク/ダウンリンクを確認')
 elif t=='aja':
  from aja import candidate as aja_candidate
  result=aja_candidate(q);unit=result.pop('unit');notes.append(result.pop('notes')) if result.get('notes') else None
 elif t.startswith('band:'):
  target=float(t.split(':')[1])
  if b==target or target==10000 and b in (10100,10400):unit=base_call(q.call)
 elif t=='warc' and b in (10,18,24) or t=='vu' and b in (50,144,430,1200,2400):unit=base_call(q.call)+'@'+q.band
 answer={'unit':unit,'own':own,'call':q.call,'date':q.date,'time':q.time,'band':q.band,'mode':q.mode,'remarks':q.remarks,'qth':q.his_qth,'code':q.code,'confirmed':q.confirmed,'notes':' / '.join(n for n in notes if n),'path':str(path),'line':line}
 if t in ('aja','special'):answer.update(result)
 return answer
def universe(root,award):
 t=AWARDS[award][1]
 if t=='area':return set('0123456789')
 if t=='pref':return {str(i).zfill(2) for i in range(1,48)}
 if t in ('city','gun','ward'):
  from locations import load
  return {u for r in load(root)['rows'] if (u:=region(r['kind']+' '+r['code'],t))}
 return set()
def list_tsv(records):
 out=io.StringIO();w=csv.writer(out,delimiter='\t',lineterminator='\r\n')
 for r in records:w.writerow([r['unit'].split('@')[0],r.get('call',''),r.get('date',''),r.get('band',''),r.get('mode',''),r.get('output_notes','')])
 return out.getvalue()
class Ledger:
 def __init__(self,root,award,profile='特記なし',owners=''):
  if award not in AWARDS:raise ValueError('未対応のアワード')
  self.root=Path(root);ident=hashlib.sha256((profile+'\0'+owners).encode()).hexdigest()[:16]
  safe=re.sub(r'[^A-Za-z0-9_-]','_',award)+'_'+hashlib.sha256(award.encode()).hexdigest()[:8];self.path=self.root/'config/awards'/safe/(ident+'.json');self.snap=Snapshot.read(self.path)
  self.data=json.loads(self.snap.data.decode('utf-8')) if self.snap.data else {'schema':1,'award':award,'profile':profile,'owners':owners,'claims':[],'applications':[]}
  self.validate(self.data)
  if self.data.get('award')!=award:raise ValueError('アワード実績DBの形式が違います。')
 def validate(self,data):
  if data.get('schema')!=1 or not isinstance(data.get('claims'),list) or not isinstance(data.get('applications'),list):raise ValueError('実績DBの形式が不正です。')
  for c in data['claims']:
   if not isinstance(c,dict) or not isinstance(c.get('unit'),str) or not c['unit'] or c.get('status') not in ('候補','提出済み','認定済み','未交信','未申請','QSL未受領','交信済み','QSL受領済み'):raise ValueError('過去実績の単位・状態を確認してください。')
  for a in data['applications']:
   if not isinstance(a,dict) or a.get('status') not in ('候補','提出済み','認定済み') or not isinstance(a.get('records'),list):raise ValueError('申請履歴の形式が不正です。')
   if any(not isinstance(r,dict) or not isinstance(r.get('unit'),str) or not r['unit'] for r in a['records']):raise ValueError('申請履歴の単位を確認してください。')
 def save(self):
  self.validate(self.data)
  if self.snap.data:
   backup=self.path.parent/(self.path.stem+'.'+datetime.now().strftime('%Y%m%d%H%M%S%f')+'.bak')
   replace_bytes(backup,self.snap.data,Snapshot.read(backup))
  replace_bytes(self.path,(json.dumps(self.data,ensure_ascii=False,indent=2)+'\n').encode(),self.snap);self.snap=Snapshot.read(self.path)
 def used(self):
  return {c['unit'] for c in self.data['claims'] if c.get('status') in ('提出済み','認定済み')}|{r['unit'] for a in self.data['applications'] if a['status'] in ('提出済み','認定済み') for r in a['records']}
 def used_records(self):
  return [dict(c) for c in self.data['claims'] if c.get('status') in ('提出済み','認定済み') and c.get('call')]+[dict(r) for a in self.data['applications'] if a['status'] in ('提出済み','認定済み') for r in a['records'] if r.get('call')]
 def used_station_keys(self):
  from contest_regional import base_call
  return {r.get('station_key') or base_call(r.get('call',''))+'@'+(r.get('aja_band') or r.get('band','')) for r in self.used_records()}
 def preview_units(self,text,remaining=False,status='認定済み'):
  units={v.strip().upper() for v in re.split(r'[,\s;]+',text) if v.strip()}
  known=universe(self.root,self.data['award'])
  if remaining:
   status={'未交信':'交信済み','QSL未受領':'QSL受領済み','未申請':'提出済み'}.get(status,status)
   if not known:raise ValueError('残り方式は地域一覧を持つアワードで使えます。')
   if units-known:raise ValueError('一覧にない番号：'+', '.join(sorted(units-known)))
   units=known-units
  return units,status
 def import_units(self,text,remaining=False,status='認定済み'):
  units,status=self.preview_units(text,remaining,status)
  # Retain historical/retired codes; no invented QSO/card evidence.
  self.data['claims'] += [{'unit':u,'status':status,'basis':'残り一覧の補集合（本人申告）' if remaining else '番号取込（本人申告）'} for u in sorted(units) if not any(c['unit']==u and c['status']==status for c in self.data['claims'])]
  self.save();return len(units)
 def import_records(self,records,status='提出済み',basis='AJA表取込'):
  if status not in ('候補','提出済み','認定済み'):raise ValueError('取込状態を選択してください。')
  existing={(c.get('unit'),c.get('call'),c.get('date')) for c in self.data['claims']}
  added=0
  for record in records:
   item=dict(record);item.update(status=status,basis=basis)
   key=(item.get('unit'),item.get('call'),item.get('date'))
   if not item.get('unit') or key in existing:continue
   self.data['claims'].append(item);existing.add(key);added+=1
  self.save();return added
 def application(self,records,status,number='',level=''):
  if status not in ('候補','提出済み','認定済み'):raise ValueError('申請状態を選択してください。')
  self.data['applications'].append({'date':datetime.now().isoformat(),'status':status,'number':number,'level':level,'records':records});self.save()


def target_count(root,award):
 from special_awards import SPECIAL_AWARDS,target
 if award in SPECIAL_AWARDS:return target(award)
 if award=='AJA':return 1000
 if award in ('AJD',):return 10
 if award=='WAJA':return 47
 if award in ('WACA','WAGA','WAKU'):return len(universe(root,award))
 if award=='ADXA':return 30
 if award=='ADXA-HALF':return 15
 if award in ('WARC-1000','V・U-1000'):return 1000
 if award.startswith('JARL Stations'):return {'J':5,'A':20,'R':50,'L':100}[award[-1]]
 if award=='ふじ':return 10
 if AWARDS[award][1].startswith('band:'):
  b=float(AWARDS[award][1].split(':')[1]);return 10 if b<1 or b>=1200 else 100
 return 100
