import json,tempfile,unittest
from pathlib import Path
from dataclasses import replace
from urllib.error import HTTPError
from model import QSO
from storage import Repository,ExternalChange,StorageError,parse
import his_qth_batch as b
from dxcc_check import aggregate,resolve
from countries import load
from country_history import load_history

def response(call,address='東京都足立区'):
 return {'musenInformation':{'totalCount':'1'},'musen':[{'detailInfo':{'identificationSignals':call,'radioEuipmentLocation':address}}]}
class V118Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.repo=Repository(self.root);self.q=QSO('2026-10-17','10:00','7','RTTY','JJ1JPE','599','599','Japan','Soka Saitama Japan','64','');self.locations=b.load_locations(self.root)
 def add(self,q=None,own='JH1HST'):
  q=q or self.q;p=self.repo.path_for(own,'',q.date);self.repo.open(p).append(q);return p
 def lookup(self,paths,**kw):return b.lookup_batch(self.repo,paths,'JH1HST',interval=0,**kw)
 def test_mic_exact_equipment_field_multiple_and_truncated(self):
  data=response('JJ1JPE');self.assertEqual(b.location_from_response(data,'JJ1JPE',self.locations)['source_code'],'100121')
  data['musen'].append(response('JJ1JPE','埼玉県草加市')['musen'][0]);data['musenInformation']['totalCount']='2'
  with self.assertRaises(StorageError):b.location_from_response(data,'JJ1JPE',self.locations)
  with self.assertRaises(StorageError):b.location_from_response(response('JJ1JPEX'),'JJ1JPE',self.locations)
  data['musenInformation']['totalCount']='1000'
  with self.assertRaises(StorageError):b.location_from_response(data,'JJ1JPE',self.locations)
 def test_request_chrome_timeout_and_throttle(self):
  class Answer:
   def __enter__(self):return self
   def __exit__(self,*args):pass
   def read(self,n):return json.dumps(response('JJ1JPE')).encode()
  def opener(req,timeout):
   self.assertIn('Chrome/',req.get_header('User-agent'));self.assertEqual(timeout,15);self.assertIn('MA=JJ1JPE',req.full_url);return Answer()
  self.assertIn('musen',b.request_location('JJ1JPE',opener))
  def blocked(*a,**k):raise HTTPError('',429,'limited',None,None)
  with self.assertRaises(b.StopLookup):b.request_location('JJ1JPE',blocked)
  for call in ['JJ1JPE/1','JJ1JPE/P','W1AW']:
   with self.assertRaises(ValueError):b.request_location(call,opener)
 def test_limit_and_filters(self):
  for n in range(25):p=self.add(replace(self.q,time=f'10:{n:02}',call='JA1'+chr(65+n)+'AA'))
  self.add(replace(self.q,call='JJ1JPE/1'));self.add(replace(self.q,call='W1AW'));self.add(replace(self.q,his_qth='Adachi Tokyo Japan'))
  other=self.add(own='JQ7FIU');calls=[]
  def lookup(call):calls.append(call);return response(call)
  rows,status=self.lookup([p],lookup=lookup);self.assertEqual(len(rows),20);self.assertEqual(len(calls),20);self.assertTrue(all(c.after for c in rows));self.assertFalse(status)
  with self.assertRaises(StorageError):self.lookup([other],lookup=lookup)
  with self.assertRaises(StorageError):self.lookup([self.root/'logbook_flr/2026_JH1HST_.txt'],lookup=lookup)
 def test_repeat_fill_backup_and_other_fields(self):
  p=self.add();self.add(replace(self.q,time='10:01',call='JH1FNU'));before=p.read_bytes()
  rows,_=self.lookup([p],limit=1,lookup=lambda c:response(c));self.assertEqual(rows[0].after.code,'100121');b.commit(self.repo,rows)
  self.assertTrue(any(f.read_bytes()==before for f in self.repo.bak.glob(p.name+'.*') if f.is_file()))
  rows,_=self.lookup([p],limit=1,lookup=lambda c:response(c));self.assertEqual(rows[0].qso.call,'JH1FNU');b.commit(self.repo,rows)
  self.assertFalse(self.lookup([p],lookup=lambda c:self.fail('already filled'))[0])
  for _,q in parse(p.read_bytes()).records:self.assertEqual(q.remarks,'64');self.assertEqual(q.mode,'RTTY')
 def test_checkbox_and_existing_code(self):
  p=self.add();rows,_=self.lookup([p],include_code=False,lookup=lambda c:response(c));self.assertEqual(rows[0].after.code,'')
  self.repo.open(p).edit(1,replace(self.q,code='1321'));rows,_=self.lookup([p],lookup=lambda c:response(c));self.assertIsNone(rows[0].after);self.assertIn('不一致',rows[0].note)
 def test_blank_start_retries_from_head_and_rate_limit_stops(self):
  p=self.add();self.add(replace(self.q,call='JH1FNU',time='10:01'));rows,_=self.lookup([p],limit=1,lookup=lambda c:response('WRONG'));self.assertIsNone(rows[0].after)
  rows,_=self.lookup([p],limit=1,lookup=lambda c:response(c));self.assertEqual(rows[0].qso.call,'JJ1JPE')
  calls=[]
  def blocked(c):calls.append(c);raise b.StopLookup('HTTP 403')
  rows,status=self.lookup([p],lookup=blocked);self.assertEqual(len(calls),1);self.assertEqual(status,'HTTP 403')
 def test_cancel_and_external_save_guard(self):
  p=self.add();self.assertFalse(self.lookup([p],cancelled=lambda:True,lookup=lambda c:self.fail('cancelled'))[0]);rows,_=self.lookup([p],lookup=lambda c:response(c));p.write_bytes(p.read_bytes()+b'\r\n');external=p.read_bytes()
  with self.assertRaises(ExternalChange):b.commit(self.repo,rows)
  self.assertEqual(p.read_bytes(),external)
 def test_prefecture_guard_and_age_exchange(self):
  p=self.add(replace(self.q,mode='FM',sent='59',received='59',remarks='13 hQSL.R'));self.assertIsNone(self.lookup([p],lookup=lambda c:response(c))[0][0].after)
  self.repo.open(p).edit(1,self.q);self.assertIsNotNone(self.lookup([p],lookup=lambda c:response(c))[0][0].after)
 def test_card_portable_and_existing_detail(self):
  q=replace(self.q,call='JJ1JPE/1',mode='FM',remarks='10 hQSL.R');new,note=b.supplied_location(self.root,q,'100121');self.assertEqual(new.his_qth,'Adachi Tokyo Japan');self.assertEqual(new.code,'100121')
  new,note=b.supplied_location(self.root,replace(q,his_qth='Actual location Japan'),'100121');self.assertEqual(new.his_qth,'Actual location Japan')
  self.assertIsNone(b.supplied_location(self.root,replace(q,remarks='13'),'100121')[0])
 def test_qsl_already_received_location_saved(self):
  import qsl_batch as batch
  p=self.add(replace(self.q,remarks='eQSL.R'));source=self.root/'receipt.txt';source.write_text('2026-10-17 10:00 JJ1JPE 100121');plan=batch.prepare(self.repo,source,'JH1HST','JST','eQSL.R');self.assertEqual(batch.decisions(plan)[0]['state'],'更新予定')
  csv,_,saved=batch.commit(self.repo,plan,self.root/'results');q=parse(p.read_bytes()).records[0][1];self.assertEqual(q.remarks,'eQSL.R');self.assertEqual(q.code,'100121');self.assertEqual(q.his_qth,'Adachi Tokyo Japan');self.assertEqual(saved,[p]);self.assertIn('HIS_QTH更新予定',csv.read_text(encoding='utf-8-sig'))
 def test_lossless_legacy_nonstandard_rst(self):
  from log_fields import patched_bytes
  p=self.add();raw=p.read_bytes().replace(b'599',b'00').replace(b' |  \\\\',b' \\\\').replace(b'\r\n',b'\n').removeprefix(b'\xef\xbb\xbf');p.write_bytes(raw);s=self.repo.open(p);new=patched_bytes(s,{1:{'his_qth':'Adachi Tokyo Japan','code':'100121'}});q=parse(new).records[0][1];self.assertEqual(q.sent,'00');self.assertEqual(q.code,'100121');self.assertFalse(new.startswith(b'\xef\xbb\xbf'));self.assertNotIn(b'\r\n',new)
 def test_dxcc_counts_portable_and_confirmed(self):
  self.add(replace(self.q,call='C21TS',his_qth='Nauru',date='2025-03-04',remarks='LoTW.R'));self.add(replace(self.q,call='C21TS',his_qth='Naoero',remarks=''),own='JH1HST/1');self.add(replace(self.q,call='N7AT',his_qth='AZ United States',remarks='eQSL.R'));self.add(replace(self.q,call='N7AT',his_qth='United States',remarks='eQSL'));self.add(replace(self.q,call='C21TS',his_qth='Nauru'),own='JQ7FIU');r=aggregate(self.repo,'JH1HST/1');self.assertEqual((r.worked,r.confirmed,r.qsos),(2,2,4));self.assertEqual(sum(e.unconfirmed for e in r.entities),2)
 def test_qth_authority_and_unknown_or_maritime(self):
  db=load(self.root);h=load_history(self.root)
  for call,qth,name in [('KH6JRB','CA United States','United States'),('DB4WC','China','China')]:self.assertEqual(resolve(db,h,replace(self.q,call=call,his_qth=qth))[0]['name'],name)
  for call,qth in [('D1DX','Donetsk'),('K1ABC/MM','United States'),('DB4WC','Unconfirmed place')]:self.assertIsNone(resolve(db,h,replace(self.q,call=call,his_qth=qth))[0])
 def test_names_and_utc_entity_boundaries(self):
  db=load(self.root);h=load_history(self.root);self.assertEqual(db.lookup('C21TS','2025-03-04')['country'],'Nauru');self.assertEqual(db.lookup('C21TS','2026-06-26')['country'],'Naoero')
  for time,valid in [('12:59',False),('13:00',True)]:self.assertEqual(resolve(db,h,replace(self.q,call='PJ2AA',date='2010-10-10',time=time,his_qth='Curacao'))[0] is not None,valid)
  self.assertIsNotNone(resolve(db,h,replace(self.q,date='2010-01-01',his_qth='Kingman Reef'))[0]);self.assertIsNone(resolve(db,h,replace(self.q,his_qth='Kingman Reef'))[0])
 def test_read_only_before_save(self):
  p=self.add();raw=p.read_bytes();aggregate(self.repo,'JH1HST');self.lookup([p],lookup=lambda c:response(c));self.assertEqual(p.read_bytes(),raw)
 def test_exact_search_handoff_excludes_similar_call_and_filename(self):
  from search import search,Criteria
  p=self.add();self.add(replace(self.q,call='JJ1JPEX'))
  similar=self.repo.book/'2026_JH1HST_2026_JH1HST_.txt';similar.write_bytes(p.read_bytes())
  r=search(self.repo,Criteria('JH1HST',portable=True,filename=p.name,call='JJ1JPE',exact_filename=True,exact_call=True));self.assertEqual(len(r.hits),1);self.assertEqual(r.hits[0].path,p)
 def test_conflicting_card_codes_do_not_write(self):
  import qsl_batch as batch
  p=self.add();raw=p.read_bytes();source=self.root/'receipt.txt';source.write_text('2026-10-17 10:00 JJ1JPE 100121\n2026-10-17 10:00 JJ1JPE 1321')
  plan=batch.prepare(self.repo,source,'JH1HST','JST','eQSL.R')
  with self.assertRaises(StorageError):batch.commit(self.repo,plan,self.root/'results')
  self.assertEqual(p.read_bytes(),raw)
 def test_import_date_selects_historical_name(self):
  from adif_import import convert
  data=b'<CALL:5>C21TS<QSO_DATE:8>20250304<TIME_ON:4>1200<BAND:3>20m<MODE:3>FT8<RST_SENT:3>-01<RST_RCVD:3>-01<EOR>'
  log,_=convert(data,'adi','JH1HST',country_data=load(self.root));self.assertFalse(log.issues);self.assertEqual(log.records[0][1].his_qth,'Nauru')
  log,_=convert(data.replace(b'20250304',b'20261017'),'adi','JH1HST',country_data=load(self.root));self.assertFalse(log.issues);self.assertEqual(log.records[0][1].his_qth,'Naoero')
if __name__=='__main__':unittest.main()
