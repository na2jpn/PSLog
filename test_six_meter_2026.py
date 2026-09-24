from pathlib import Path
from copy import deepcopy
import json,tempfile,unittest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from contest_rules import loads,score,RuleStore
from contest import select_logs
from contest_export import plan,key
from contest_submit_ui import DetailsDialog
from contest_event_ui import EventDialog
from contest_qualification import operator_text
from storage import Repository
from model import QSO
ROOT=Path(__file__).parent

def rule():return loads((ROOT/'config/rules/six_meter_and_down_2026.txt').read_text(encoding='utf-8'))
def context(code='CA',power=20):
 r=rule();c=next(c for c in r['event']['categories'] if c['id']==code)
 v=dict(category=code,power=power,flags={f:True for f in r['event']['required_flags']+c['required_flags']})
 if code=='PN':v['licensedate']='2023-07-04'
 if code in ('CS','XS'):v['age']=70
 if code=='XMJ':v['operators']=[dict(name='JH1HST',age=18)]
 return v

def qso(**kw):return dict(dict(date='2026-07-04',time='21:00',call='JA1AAA',band='50',mode='CW',sent='13L',exchange='10L'),**kw)

class SixMeterTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
 def test_official_category_set(self):
  expected={'PA','PN','PD','PMA','XMJ'}
  for p in ('C','X'):expected.update(p+s for s in ['A','50','144','430','1200','2400','5600','10G','S','P','MA'])
  self.assertEqual({c['id'] for c in rule()['event']['categories']},expected)
 def test_dictionary_counts_and_retired_codes(self):
  db=json.loads((ROOT/'config/db/contest/jarl_municipal_2026.json').read_text(encoding='utf-8'));self.assertEqual(db['counts'],dict(city=815,county=379,ward=171))
  codes=set(rule()['event']['exchange']['profiles'][1]['codes']);self.assertEqual(len(codes),1345)
  self.assertTrue({'010101','100101','120101','180207','180208','180209','2731','4037','10007'}<=codes)
  self.assertFalse({'0101','1201','180201','180205','2722','40010','999999'}&codes)
 def test_every_dictionary_code_parses_on_high_band(self):
  # Each row independently: these are alternative locations, not one operation.
  from contest_jarl import prepare_exchange
  spec=rule()['event']['exchange']
  for code in spec['profiles'][1]['codes']:
   v=qso(band='2400',sent=code+'P',exchange=code+'P');prepare_exchange(spec,v,5);self.assertEqual(v['area'],code)
 def test_low_high_points_and_region_consistency(self):
  rows=[qso(),qso(band='2400',sent='1319L',exchange='120101P')]
  s=score(rule(),rows,context());self.assertEqual(s.total,6)
  rows[1]['sent']='120101L';self.assertIsNone(score(rule(),rows,context()).total)
  rows=[qso(sent='48L'),qso(band='2400',sent='10007L',exchange='120101P')]
  self.assertEqual(score(rule(),rows,context()).total,6)
 def test_distinct_high_bands_and_alias_duplicate(self):
  rows=[qso(band=b,sent='1319L',exchange='120101P') for b in ['10.1G','10100','10.4G','24G','47G','77G','135G','248G']]
  s=score(rule(),rows,context('C10G'));self.assertEqual(s.total,98);self.assertEqual(s.multi1,7);self.assertEqual(s.rows[1]['points'],0)
 def test_phone_limits_and_dstar_only(self):
  self.assertEqual(score(rule(),[qso(mode='D-STAR')],context('PD')).total,1)
  self.assertIsNone(score(rule(),[qso(mode='SSB')],context('PD')).total)
  self.assertIsNone(score(rule(),[qso(mode='SSB',sent='13M')],context('PA',21)).total)
  self.assertEqual(score(rule(),[qso(mode='SSB',sent='13M')],context('XA',21)).total,1)
  for mode in ('FT8','RTTY','C4FM','DMR'):self.assertIsNone(score(rule(),[qso(mode=mode)],context('XA')).total)
 def test_qualification_boundaries_and_mixed_exception(self):
  for date,ok in [('2023-07-03',False),('2023-07-04',True),('2026-07-04',True),('2026-07-05',False)]:
   v=context('PN');v['licensedate']=date;self.assertEqual(score(rule(),[qso(mode='SSB')],v).total is not None,ok)
  for age,ok in [(69,False),(70,True)]:
   v=context('CS');v['age']=age;self.assertEqual(score(rule(),[qso()],v).total is not None,ok)
  self.assertIsNone(score(rule(),[qso()],context('XA')).total)
  self.assertEqual(score(rule(),[qso()],context('XMJ')).total,1)
  v=context('XMJ');v['operators'][0]['age']=19;self.assertIsNone(score(rule(),[qso()],v).total)
  for p,ok in [(5,True),(5.001,False)]:self.assertEqual(score(rule(),[qso(sent='13P')],context('CP',p)).total is not None,ok)
 def test_end_time_and_no_ten_minute_rule(self):
  rows=[qso(date='2026-07-05',time='14:59'),qso(date='2026-07-05',time='15:00',call='JA1BBB')]
  s=score(rule(),rows,context());self.assertEqual([x['points'] for x in s.rows],[1,0])
  s=score(rule(),[qso(),qso(time='21:01',band='144')],context('CMA'));self.assertEqual(s.total,4)
 def test_checklog_does_not_block_later_valid_contact(self):
  rows=[qso(sent='10L',checklog=True),qso(time='21:01')]
  s=score(rule(),rows,context());self.assertEqual([x['points'] for x in s.rows],[0,1]);self.assertEqual(s.total,1)
 def test_each_category_jarl_export_and_original_unchanged(self):
  r=rule()
  for c in r['event']['categories']:
   with self.subTest(code=c['id']),tempfile.TemporaryDirectory() as tmp:
    power=5 if c['id'] in ('CP','XP') else 20;ctx=context(c['id'],power);b=c['bands'][0];hi=b not in ('50','144','430','1200');mode='SSB' if c.get('required_mode_families') else c['modes'][0];rs='599' if mode=='CW' else '59'
    repo=Repository(tmp);p=repo.path_for('JH1HST','','2026-07-04');repo.open(p).append(QSO('2026-07-04','21:00',b,mode,'JA1AAA',rs,rs,'Japan','Soka Japan','',''));original=p.read_bytes();sel=select_logs(repo,[p],'JH1HST')
    draft={key(sel.rows[0]):dict(sent=('1319' if hi else '13')+('P' if power==5 else 'L'),received='120101P' if hi else '10L',status='確認済み')}
    info=dict(contest=r['event']['submission']['contest'],category=c['id'],name='試験',address='試験',power=str(power),date='2026-07-06',signature='試験',oath=True,email='test@example.com',multiop=c['operator']=='MO',multioplist=operator_text(ctx['operators']) if 'operators' in ctx else 'JH1HST' if c['operator']=='MO' else '',age=str(ctx.get('age','')),licensedate=ctx.get('licensedate',''))
    formats=['JARL R2.1'] if c['id'] in ('PN','CS','XS') else ['JARL R1.0','JARL R2.1']
    for f in formats:
     out=plan(sel,r,draft,f,info,context=ctx).preview();self.assertIn('<TOTALSCORE>'+('2' if hi else '1')+'</TOTALSCORE>',out)
    self.assertEqual(p.read_bytes(),original)
 def test_x_ui_export_and_normalized_non_target_row(self):
  with tempfile.TemporaryDirectory() as tmp:
   repo=Repository(tmp);p=repo.path_for('JH1HST','','2026-07-04')
   for time,band in [('21:00','50'),('21:01','50'),('21:02','1.2G')]:repo.open(p).append(QSO('2026-07-04',time,band,'CW','JA1AAA','599','599','Japan','Soka Japan','',''))
   sel=select_logs(repo,[p],'JH1HST');draft={key(row):dict(sent='13L',received='10L') for row in sel.rows};before=deepcopy(draft);d=DetailsDialog(sel,draft);d.table.item(0,8).setCheckState(Qt.Checked);self.assertTrue(d.draft[key(sel.rows[0])]['checklog']);self.assertEqual(draft,before)
   info=dict(contest=rule()['event']['submission']['contest'],category='C50',name='試験',address='試験',power='20',date='2026-07-06',signature='試験',oath=True,email='test@example.com')
   out=plan(sel,rule(),d.draft,'JARL R2.1',info,context=context('C50')).preview();self.assertIn('X 2026-07-04 21:00',out);self.assertIn('21:02 1200 CW',out);self.assertIn('<TOTALSCORE>1</TOTALSCORE>',out);d.deleteLater()
 def test_pack_installs_one_annual_rule_and_ui_categories(self):
  import rule_pack
  with tempfile.TemporaryDirectory() as tmp:
   store=RuleStore(Path(tmp));p=ROOT/'distribution/rules/six_meter_and_down_2026_r1.zip';self.assertEqual(rule_pack.install(store,rule_pack.preview(store,p)),1)
   r=store.read(store.files()[0])[0];self.assertEqual(len(r['event']['categories']),27)
   dialog=EventDialog(r['event'],context('PD'));self.assertEqual(dialog.category.count(),27);dialog.deleteLater()

if __name__=='__main__':unittest.main()
