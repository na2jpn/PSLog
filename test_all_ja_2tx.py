from pathlib import Path
from copy import deepcopy
import tempfile,unittest
from PySide6.QtWidgets import QApplication
from contest_rules import loads,score,RuleStore,dumps
from contest_export import plan,key
from contest_timing import HISTORY_FLAG
from storage import Repository
from model import QSO
from contest import select_logs
from contest_ui import ContestDialog

ROOT=Path(__file__).parent

def rule():return loads((ROOT/'config/rules/all_ja_2026.txt').read_text(encoding='utf-8'))
def ctx(cat='CM2M',power=100):
 r=rule();c=next(c for c in r['event']['categories'] if c['id']==cat)
 return dict(category=cat,power=power,flags={s:True for s in r['event']['required_flags']+c['required_flags']+[HISTORY_FLAG]})
def entry(**kw):return dict(dict(date='2026-04-25',time='21:00',call='JA1AAA',band='7',mode='CW',sent='13M',exchange='106M',tx='1'),**kw)

class AllJaTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
 def test_four_categories_and_power_boundaries(self):
  r=rule();self.assertTrue({'CM2H','CM2M','XM2H','XM2M'} <= {c['id'] for c in r['event']['categories']})
  for cat,power,mode in [('CM2M',100,'CW'),('CM2H',101,'CW'),('XM2M',100,'SSB'),('XM2H',101,'SSB')]:
   self.assertEqual(score(r,[entry(mode=mode)],ctx(cat,power)).total,1)
  for cat,power in [('CM2M',5),('CM2M',100.001),('CM2H',100)]:self.assertIsNone(score(r,[entry(sent='13P')],ctx(cat,power)).total)
  self.assertEqual(score(r,[entry(sent='13L')],ctx(power=5.001)).total,1)
 def test_two_series_independent_ten_minutes_and_cross_series_dupe(self):
  rows=[entry(),entry(time='21:01',band='14',tx='2'),entry(time='21:09',band='21'),entry(time='21:10',band='21'),entry(time='21:11',band='7',tx='2')]
  s=score(rule(),rows,ctx());self.assertEqual([r['points'] for r in s.rows],[1,1,0,1,0]);self.assertEqual(s.total,9)
 def test_official_excluded_change_does_not_advance_clock(self):
  rows=[entry(time='21:10'),entry(time='21:20',band='14'),entry(time='21:21',band='14',call='JA2BBB'),entry(time='21:22',band='21',call='JA3CCC'),entry(time='21:29',band='14',call='JA4DDD'),entry(time='21:33',band='21',call='JA5EEE')]
  s=score(rule(),rows,ctx());self.assertEqual([r['points'] for r in s.rows],[1,1,1,0,1,1]);self.assertEqual(s.total,15)
 def test_mixed_requires_phone_but_phone_only_and_duplicate_phone_are_allowed(self):
  r=rule();self.assertIsNone(score(r,[entry()],ctx('XM2M')).total)
  self.assertEqual(score(r,[entry(mode='SSB')],ctx('XM2M')).total,1)
  self.assertEqual(score(r,[entry(),entry(mode='SSB',time='21:01')],ctx('XM2M')).total,1)
  self.assertIsNone(score(r,[entry(mode='RTTY')],ctx('XM2M')).total)
 def test_regions_and_power_letters_do_not_split_multipliers(self):
  r=rule();rows=[entry(),entry(call='JA1BBB',exchange='106P'),entry(call='JA1CCC',exchange='48H')]
  s=score(r,rows,ctx());self.assertEqual(s.multi1,2);self.assertEqual(s.total,6)
  for number in ['01M','49P','115H','106','106MM','106 M','41003B']:
   self.assertIsNone(score(r,[entry(exchange=number)],ctx()).total)
  for v in [entry(sent='13H'),entry(area='10'),entry(sent='13')]:self.assertIsNone(score(r,[v],ctx()).total)
  self.assertIsNone(score(r,[entry(),entry(time='21:01',sent='10M')],ctx()).total)
 def test_power_letter_thresholds_depend_on_band(self):
  self.assertEqual(score(rule(),[entry(sent='13L')],ctx(power=10)).total,1)
  self.assertIsNone(score(rule(),[entry(sent='13M')],ctx(power=10)).total)
  self.assertEqual(score(rule(),[entry(band='50',sent='13L')],ctx(power=20)).total,1)
  self.assertIsNone(score(rule(),[entry(band='50',sent='13M')],ctx(power=20)).total)
 def test_missing_tx_and_event_boundaries(self):
  r=rule();self.assertIsNone(score(r,[entry(tx='')],ctx()).total)
  self.assertIsNone(score(r,[entry(tx='0')],ctx()).total)
  s=score(r,[entry(time='20:59'),entry(),entry(date='2026-04-26',time='21:00'),entry(band='144',time='21:02')],ctx());self.assertEqual([v['points'] for v in s.rows],[0,1,0,0])
 def make_submission(self,root,cat='CM2M'):
  r=rule();repo=Repository(root);p=repo.path_for('JH1HST','','2026-04-25')
  data=[('21:00','7','JA1AAA','106M','1'),('21:01','14','JA2BBB','48P','2'),('21:09','21','JA3CCC','10M','1'),('21:10','21','JA3CCC','10M','1')]
  for t,b,call,n,tx in data:repo.open(p).append(QSO('2026-04-25',t,b,'CW',call,'599','599','Japan','Soka Japan',n,''))
  sel=select_logs(repo,[p],'JH1HST');draft={key(row):dict(sent='13M',received=row[1].remarks,status='確認済み',tx=data[i][-1]) for i,row in enumerate(sel.rows)}
  info=dict(contest=r['event']['submission']['contest'],category=cat,power='100',name='試験',address='試験住所',date='2026-04-27',signature='試験',oath=True,zone='JST',multiop=True,multioplist='JH1HST JQ7FIU',email='test@example.com')
  return repo,p,sel,draft,info
 def test_both_jarl_versions_end_in_series_and_keep_zero_rows(self):
  with tempfile.TemporaryDirectory() as root:
   repo,p,sel,draft,info=self.make_submission(root);raw=p.read_bytes()
   for fmt in ['JARL R1.0','JARL R2.1']:
    out=plan(sel,rule(),draft,fmt,info,context=ctx()).preview();rows=[s.split() for s in out.splitlines() if s.startswith('2026-04-25 ')]
    self.assertEqual([x[-1] for x in rows],['1','2','1','1']);self.assertEqual([x[-2] for x in rows],['1','1','0','1']);self.assertIn('<TOTALSCORE>9</TOTALSCORE>',out)
    self.assertTrue(all(len(x)==12 for x in rows));self.assertIn('Mlt Pts TX',out)
    if fmt.endswith('R1.0'):self.assertIn('<SCORE BAND=TOTAL>4,3,3</SCORE>',out)
   self.assertEqual(raw,p.read_bytes())
 def test_export_requires_contact_info_and_will_not_drop_tx(self):
  with tempfile.TemporaryDirectory() as root:
   _,p,sel,draft,info=self.make_submission(root)
   for field in ['email','multioplist']:
    bad=deepcopy(info);bad[field]=''
    with self.assertRaises(ValueError):plan(sel,rule(),draft,'JARL R2.1',bad,context=ctx())
   draft[key(sel.rows[-1])]['tx']='3'
   with self.assertRaises(ValueError):plan(sel,rule(),draft,'JARL R2.1',info,context=ctx())
 def test_wizard_connects_category_to_jarl_summary(self):
  with tempfile.TemporaryDirectory() as root:
   repo,p,sel,draft,info=self.make_submission(root);path,_=RuleStore(root).save(rule());w=ContestDialog(repo,'JH1HST')
   w.advance();w.check_all(True);w.advance();w.draft=draft;w.rules.setCurrentIndex(w.rules.findData(str(path)));w.event_contexts[str(path)]=ctx();w.calculate();self.assertEqual(w.result.total,9)
   w.stack.setCurrentIndex(3);w.advance();self.assertEqual(w.stack.currentIndex(),4);self.assertEqual(w.submission.fields['category'].text(),'CM2M');self.assertTrue(w.submission.fields['multiop'].isChecked());self.assertIn('メールアドレス',w.submission.overview.text());w.timer.stop();w.deleteLater()
 def test_schema_roundtrip_and_bad_lower_limit(self):
  r=rule();self.assertEqual(loads(dumps(r)),r);next(c for c in r['event']['categories'] if c['id']=='CM2M')['min_power_exclusive']=100
  with self.assertRaises(ValueError):loads(dumps(r))

if __name__=='__main__':unittest.main()
