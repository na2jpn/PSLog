from copy import deepcopy
from pathlib import Path
import tempfile,unittest
from PySide6.QtWidgets import QApplication
from contest_rules import score,loads,dumps,RuleStore
from contest_timing import HISTORY_FLAG
from contest_event_ui import EventDialog
from contest_export import plan,key
from contest_qualification import operator_text
from contest import select_logs
from storage import Repository
from model import QSO
from test_jarl_station_fd import fd,q,ctx
ROOT=Path(__file__).parent

def context(code='CA',power=50,kind='HOME'):
 r=fd();c=next(c for c in r['event']['categories'] if c['id']==code);v=ctx(r,code,kind,power)
 if c.get('timing'):v['flags'][HISTORY_FLAG]=True
 if c.get('power_by_band'):v['power_by_band']=deepcopy(c['power_by_band'])
 if code=='PN':v['licensedate']='2023-08-01'
 if code in ('CS','XS'):v['age']=70
 if code=='XMJ':v['operators']=[dict(name='JH1HST',age=18)]
 return v

def example(c,v):
 b=c['bands'][0];power=v.get('power_by_band',{}).get(b,v['power']);threshold=20 if b in ('50','144','430') else 10
 letter='P' if power<=5 else 'L' if power<=threshold else 'M'
 high=b in ('2400','5600','10100','10400','24000','47000','77000','135000','248000')
 return q(date='2026-08-02' if c.get('scoring_windows') else '2026-08-01',time='06:00' if c.get('scoring_windows') else '21:00',band=b,mode='SSB' if c.get('required_mode_families') else c['modes'][0],sent=('1319' if high else '13')+letter,exchange='120101P' if high else '10P',tx='1')

class FieldDayCategoryTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
 def test_exact_42_categories(self):
  expected={'PA','PN','PMA','XMJ'}
  for prefix in ('C','X'):expected.update(prefix+s for s in ['A','19','35','7','14','21','28','50','144','430','1200','2400','5600','10G','S','P','AR','MA','M2'])
  self.assertEqual({c['id'] for c in fd()['event']['categories']},expected)
 def test_every_category_scores_and_outputs_r21_and_r10_when_supported(self):
  r=fd()
  for c in r['event']['categories']:
   with self.subTest(category=c['id']),tempfile.TemporaryDirectory() as tmp:
    power=5 if c['id'] in ('CP','XP') else 20 if c['id'].startswith('P') else 50
    v=context(c['id'],power);row=example(c,v);self.assertEqual(score(r,[row],v).total,1)
    repo=Repository(tmp);p=repo.path_for('JH1HST','',row['date']);rst='599' if row['mode']=='CW' else '59'
    repo.open(p).append(QSO(row['date'],row['time'],row['band'],row['mode'],row['call'],rst,rst,'Japan','Soka Japan','',''));before=p.read_bytes();sel=select_logs(repo,[p],'JH1HST')
    draft={key(sel.rows[0]):dict(sent=row['sent'],received=row['exchange'],tx='1',status='確認済み')}
    info=dict(contest=r['event']['submission']['contest'],category=c['id'],name='試験',address='試験',power=str(power),date='2026-08-03',signature='試験',oath=True,email='test@example.com',fd=True,multiop=c['operator']=='MO',multioplist=operator_text(v['operators']) if 'operators' in v else 'JH1HST' if c['operator']=='MO' else '',age=str(v.get('age','')),licensedate=v.get('licensedate',''))
    formats=['JARL R2.1'] if c['id'] in ('PN','CS','XS') else ['JARL R1.0','JARL R2.1']
    for f in formats:
     out=plan(sel,r,draft,f,info,context=v).preview();self.assertIn('<TOTALSCORE>1</TOTALSCORE>',out);self.assertIn('<FDCOEFF>1</FDCOEFF>',out)
     line=next(line for line in out.splitlines() if line.startswith(row['date']+' '));self.assertEqual(len(line.split()),12 if c.get('timing') else 11)
    if c['id'] in ('PN','CS','XS'):
     with self.assertRaisesRegex(ValueError,'R2.1'):plan(sel,r,draft,'JARL R1.0',info,context=v)
    self.assertEqual(p.read_bytes(),before)
 def test_phone_per_band_power_and_14_exclusion(self):
  v=context('PA',20);r=fd();rows=[q(mode='SSB',sent='13L'),q(mode='SSB',band='144',call='JA1BBB',sent='13L'),q(mode='SSB',band='1200',call='JA1CCC',sent='13L'),q(mode='SSB',band='14',call='JA1DDD')]
  s=score(r,rows,v);self.assertEqual([x['points'] for x in s.rows],[1,1,1,0]);self.assertEqual(s.total,9)
  v['power_by_band']['1200']=15;self.assertIsNone(score(r,rows,v).total)
  v=context('PA',20);v.pop('power_by_band');self.assertIsNone(score(r,[q(mode='SSB',sent='13L')],v).total)
 def test_newcomer_silver_junior_qrp_boundaries(self):
  for date,ok in [('2023-07-31',False),('2023-08-01',True),('2026-08-01',True),('2026-08-02',False)]:
   v=context('PN',20);v['licensedate']=date;self.assertEqual(score(fd(),[q(mode='SSB',sent='13L')],v).total is not None,ok)
  v=context('CS');v['age']=69;self.assertIsNone(score(fd(),[q()],v).total)
  v['age']=70;self.assertEqual(score(fd(),[q()],v).total,1)
  v=context('XMJ');self.assertEqual(score(fd(),[q()],v).total,1);v['operators'][0]['age']=19;self.assertIsNone(score(fd(),[q()],v).total)
  self.assertEqual(score(fd(),[q(sent='13P')],context('CP',5)).total,1);self.assertIsNone(score(fd(),[q(sent='13P')],context('CP',5.001)).total)
 def test_morning_boundaries_and_night_does_not_occupy_duplicate(self):
  rows=[q(time='21:00'),q(date='2026-08-02',time='05:59'),q(date='2026-08-02',time='06:00'),q(date='2026-08-02',time='11:59',call='JA1BBB'),q(date='2026-08-02',time='12:00',call='JA1CCC')]
  s=score(fd(),rows,context('CAR'));self.assertEqual([x['points'] for x in s.rows],[0,0,1,1,0]);self.assertEqual(s.total,2)
  self.assertEqual(score(fd(),rows[:1],context('CA')).total,1)
 def test_morning_mixed_phone_must_be_in_scoring_window(self):
  rows=[q(mode='SSB'),q(date='2026-08-02',time='06:00')];self.assertIsNone(score(fd(),rows,context('XAR')).total)
  rows[1]['mode']='SSB';self.assertEqual(score(fd(),rows,context('XAR')).total,1)
 def test_only_two_wave_categories_have_timing(self):
  self.assertEqual({c['id'] for c in fd()['event']['categories'] if c.get('timing')},{'CM2','XM2'})
  for code in ('CA','CMA','XMJ'):
   self.assertEqual(score(fd(),[q(),q(band='14',time='21:01')],context(code)).total,4)
 def test_two_wave_independent_clocks_and_shared_duplicate(self):
  rows=[q(tx='1'),q(band='14',time='21:01',tx='2'),q(band='21',time='21:09',tx='1'),q(band='21',time='21:10',tx='1'),q(band='7',time='21:11',tx='2')]
  s=score(fd(),rows,context('CM2',kind='A'));self.assertEqual([x['points'] for x in s.rows],[1,1,0,1,0]);self.assertEqual(s.total,18)
  self.assertIsNone(score(fd(),[q()],context('CM2')).total)
 def test_violation_does_not_advance_clock_or_reserve_contact(self):
  rows=[q(tx='1'),q(band='14',time='21:09',tx='1'),q(band='7',time='21:09',call='JA1BBB',tx='2'),q(band='14',time='21:10',tx='1')]
  s=score(fd(),rows,context('CM2'));self.assertEqual([x['points'] for x in s.rows],[1,0,1,1]);self.assertEqual(s.total,6)
 def test_excluded_morning_and_two_wave_rows_remain_in_submission(self):
  r=fd()
  cases=[('CAR',[q(),q(date='2026-08-02',time='06:00'),q(date='2026-08-02',time='12:00',call='JA1BBB')],[0,1,0]),('CM2',[q(tx='1'),q(band='21',time='21:09',tx='1'),q(band='21',time='21:10',tx='1')],[1,0,1])]
  for code,rows,want in cases:
   with self.subTest(code=code),tempfile.TemporaryDirectory() as tmp:
    repo=Repository(tmp);p=repo.path_for('JH1HST','','2026-08-01')
    for row in rows:repo.open(p).append(QSO(row['date'],row['time'],row['band'],row['mode'],row['call'],'599','599','Japan','Soka Japan','',''))
    original=p.read_bytes();sel=select_logs(repo,[p],'JH1HST');draft={key(record):dict(sent=rows[i]['sent'],received=rows[i]['exchange'],tx=rows[i].get('tx','')) for i,record in enumerate(sel.rows)}
    info=dict(contest=r['event']['submission']['contest'],category=code,name='試験',address='試験',power='50',date='2026-08-03',signature='試験',oath=True,email='test@example.com',fd=True,multiop=code=='CM2',multioplist='JH1HST' if code=='CM2' else '')
    for f in ('JARL R1.0','JARL R2.1'):
     out=plan(sel,r,draft,f,info,context=context(code)).preview();lines=[line.split() for line in out.splitlines() if line.startswith('2026-08-')];self.assertEqual(len(lines),3);self.assertEqual([int(line[-2] if code=='CM2' else line[-1]) for line in lines],want);self.assertNotIn('\nX ',out)
     if code=='CM2':self.assertEqual([line[-1] for line in lines],['1','1','1'])
    if code=='CM2':
     draft[key(sel.rows[1])]['tx']=''
     with self.assertRaisesRegex(ValueError,'系列'):plan(sel,r,draft,'JARL R2.1',info,context=context(code))
    self.assertEqual(p.read_bytes(),original)
 def test_morning_schema_rejects_invalid_or_overlapping_windows(self):
  for periods in [[],[dict(start='2026-08-02 12:00',end='2026-08-02 06:00')],[dict(start='2026-07-31 06:00',end='2026-07-31 12:00')],[dict(start='2026-08-02 06:00',end='2026-08-02 10:00'),dict(start='2026-08-02 09:00',end='2026-08-02 12:00')]]:
   r=fd();next(c for c in r['event']['categories'] if c['id']=='CAR')['scoring_windows']=periods
   with self.assertRaises(ValueError):loads(dumps(r))
 def test_pack_upgrades_two_to_42_without_duplicate_file(self):
  import rule_pack
  with tempfile.TemporaryDirectory() as tmp:
   store=RuleStore(Path(tmp));base=ROOT/'distribution/rules';rule_pack.install(store,rule_pack.preview(store,base/'field_day_2026_ca_xa_r1.zip'));self.assertEqual(len(store.read(store.files()[0])[0]['event']['categories']),2)
   change=rule_pack.preview(store,base/'field_day_2026_r2.zip');self.assertEqual(change.items[0].status,'更新');self.assertEqual(rule_pack.install(store,change),1);self.assertEqual(len(store.files()),1);self.assertEqual(len(store.read(store.files()[0])[0]['event']['categories']),42)
 def test_ui_shows_morning_and_two_wave_conditions(self):
  for code,text in [('CAR','2026-08-02 06:00'),('XM2','10分')]:
   d=EventDialog(fd()['event'],context(code));self.assertEqual(d.category.count(),42);self.assertIn(text,d.time_summary.text());d.deleteLater()

if __name__=='__main__':unittest.main()
