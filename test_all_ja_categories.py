from copy import deepcopy
from pathlib import Path
import tempfile,unittest
from PySide6.QtWidgets import QApplication
from contest_rules import score,loads,dumps,RuleStore
from contest_export import plan,key
from contest_event_ui import EventDialog
from contest_qualification import operator_text
from contest_ui import ContestDialog
from storage import Repository
from model import QSO
from contest import select_logs
from test_all_ja_2tx import rule,entry,ctx


def context(cat,power=None):
 r=rule();c=next(c for c in r['event']['categories'] if c['id']==cat)
 p=power if power is not None else 101 if c.get('min_power_exclusive')==100 else min(c.get('max_power') or 100,100)
 v=ctx(cat,p)
 if 'power_by_band' in c:v['power_by_band']=deepcopy(c['power_by_band'])
 q=c.get('qualification',{})
 if 'min_age' in q:v['age']=70
 if 'license_since' in q:v['licensedate']='2023-04-25'
 if 'operators_max_age' in q:v['operators']=[dict(name='JA1AAA',age=18),dict(name='試験 太郎',age=17)]
 return v

def qso_for(c,context):
 mode='SSB' if 'phone' in c.get('required_mode_families',[]) else c['modes'][0]
 band=c['bands'][0];p=context.get('power_by_band',{}).get(band,context['power'])
 letter='H' if p>100 else 'P' if p<=5 else 'L' if p<=(20 if band=='50' else 10) else 'M'
 return entry(band=band,mode=mode,sent='13'+letter)

class AllJaCategoryTests(unittest.TestCase):
 def test_upgrade_four_categories_to_68(self):
  import rule_pack
  with tempfile.TemporaryDirectory() as tmp:
   store=RuleStore(Path(tmp));base=Path(__file__).parent/'distribution/rules'
   rule_pack.install(store,rule_pack.preview(store,base/'all_ja_2026_2tx_r1.zip'))
   self.assertEqual(len(store.read(store.files()[0])[0]['event']['categories']),4)
   update=rule_pack.preview(store,base/'all_ja_2026_r2.zip')
   self.assertEqual(update.items[0].status,'更新')
   self.assertEqual(rule_pack.install(store,update),1)
   self.assertEqual(len(store.files()),1)
   self.assertEqual(len(store.read(store.files()[0])[0]['event']['categories']),68)

 @classmethod
 def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
 def test_exact_68_codes_against_regulation_table(self):
  expected={'PA','P19','P35','P7','P21','P28','P50','PN','PMA','CS','XS','XMJ'}
  for mode in ('C','X'):
   expected|={mode+b+p for b in ('A','19','35','7','14','21','28','50') for p in ('H','M','P')}
   expected|={mode+m+p for m in ('MA','M2') for p in ('H','M')}
  self.assertEqual(len(expected),68);self.assertEqual({c['id'] for c in rule()['event']['categories']},expected)
 def test_every_category_can_score_valid_contact(self):
  r=rule()
  for c in r['event']['categories']:
   with self.subTest(category=c['id']):
    v=context(c['id']);s=score(r,[qso_for(c,v)],v);self.assertEqual(s.total,1,s.problems)
 def test_ordinary_so_mo_do_not_inherit_two_wave_rule(self):
  for cat in ('CAM','CMAM','XAM','XMAM'):
   v=context(cat);rows=[entry(),entry(time='21:01',band='14',mode='SSB' if cat.startswith('X') else 'CW')]
   self.assertEqual(score(rule(),rows,v).total,4)
 def test_single_band_preserves_other_band_without_scoring(self):
  rows=[entry(),entry(time='21:01',band='50',call='JA2BBB')];s=score(rule(),rows,context('C7M'))
  self.assertEqual([r['points'] for r in s.rows],[1,0]);self.assertEqual(s.total,1)
 def test_phone_power_10_20_and_number_letters(self):
  v=context('PA');v['power']=20;v['power_by_band']={'7':10,'50':20}
  rows=[entry(mode='SSB',sent='13L'),entry(mode='FM',band='50',sent='13L',call='JA2BBB')]
  self.assertEqual(score(rule(),rows,v).total,4)
  bad=deepcopy(v);bad['power_by_band']['7']=10.001;self.assertIsNone(score(rule(),rows,bad).total)
  bad=deepcopy(v);bad['power_by_band']={};self.assertIsNone(score(rule(),rows,bad).total)
  self.assertEqual(score(rule(),[rows[0]],context('P7',10)).total,1)
  low=context('PA',10);low.pop('power_by_band');self.assertEqual(score(rule(),rows,low).total,4)
  invalid=deepcopy(rows);invalid[0]['sent']='13M';self.assertIsNone(score(rule(),invalid,v).total)
 def test_band_mode_and_phone_14_exclusions(self):
  r=rule();s=score(r,[entry(mode='SSB',sent='13L'),entry(mode='SSB',band='14',sent='13L')],context('PA'))
  self.assertEqual([x['points'] for x in s.rows],[1,0])
  self.assertIsNone(score(r,[entry(mode='FM')],context('X7M')).total)
  self.assertEqual(score(r,[entry(mode='FM',band='28')],context('X28M')).total,1)
 def test_newcomer_date_boundaries(self):
  c=next(c for c in rule()['event']['categories'] if c['id']=='PN');v=context('PN');q=qso_for(c,v)
  for date,ok in [('2023-04-24',False),('2023-04-25',True),('2026-04-25',True),('2026-04-26',False),('2023-02-29',False),('',False)]:
   v['licensedate']=date;self.assertEqual(score(rule(),[q],v).total is not None,ok)
 def test_silver_is_operator_age_and_has_no_100w_minimum(self):
  for cat,mode in [('CS','CW'),('XS','SSB')]:
   v=context(cat,5);v['age']=69;self.assertIsNone(score(rule(),[entry(mode=mode,sent='13P')],v).total)
   v['age']=70;self.assertEqual(score(rule(),[entry(mode=mode,sent='13P')],v).total,1)
 def test_junior_cw_only_and_all_operator_ages(self):
  v=context('XMJ');self.assertEqual(score(rule(),[entry()],v).total,1)
  v['operators'][1]['age']=19;self.assertIsNone(score(rule(),[entry()],v).total)
  v['operators']=[];self.assertIsNone(score(rule(),[entry()],v).total)
 def test_category_and_qualification_ui_roundtrip(self):
  v=context('PN');d=EventDialog(rule()['event'],v);d.qualification.license.setText('２０２３-０４-２５');d.apply();self.assertEqual(d.context['licensedate'],'2023-04-25');d.deleteLater()
  v=context('XMJ');d=EventDialog(rule()['event'],v);d.qualification.ops.setPlainText('JA1AAA / 18\n試験 太郎 / 17');d.apply();self.assertEqual(d.context['operators'],v['operators']);d.deleteLater()
  d=EventDialog(rule()['event'],context('PA'));self.assertEqual(d.qualification.widgets['7'].value(),10);self.assertEqual(d.qualification.widgets['50'].value(),20);d.deleteLater()
 def test_every_category_exports_r21_and_expected_optional_fields(self):
  r=rule()
  for c in r['event']['categories']:
   with self.subTest(category=c['id']),tempfile.TemporaryDirectory() as root:
    v=context(c['id']);q=qso_for(c,v);repo=Repository(root);p=repo.path_for('JH1HST','',q['date']);rs='599' if q['mode']=='CW' else '59'
    repo.open(p).append(QSO(q['date'],q['time'],q['band'],q['mode'],q['call'],rs,rs,'Japan','Soka Japan',q['exchange'],''));original=p.read_bytes();sel=select_logs(repo,[p],'JH1HST')
    draft={key(sel.rows[0]):dict(sent=q['sent'],received=q['exchange'],tx='1',status='確認済み')}
    info=dict(contest=r['event']['submission']['contest'],category=c['id'],name='試験',address='試験',power=str(v['power']),date='2026-04-27',signature='試験',oath=True,email='test@example.com',multiop=c['operator']=='MO',multioplist=operator_text(v['operators']) if 'operators' in v else 'JH1HST JQ7FIU' if c['operator']=='MO' else '',age=str(v.get('age','')),licensedate=v.get('licensedate',''))
    out=plan(sel,r,draft,'JARL R2.1',info,context=v).preview();self.assertIn('<TOTALSCORE>1</TOTALSCORE>',out)
    row=next(s for s in out.splitlines() if s.startswith('2026-04-25 '));self.assertEqual(len(row.split()),12 if 'timing' in c else 11)
    if c['id']=='PN':self.assertIn('<LICENSEDATE>2023-04-25</LICENSEDATE>',out)
    if c['id'] in ('CS','XS'):self.assertIn('<AGE>70</AGE>',out)
    if c['id']=='XMJ':self.assertIn('JA1AAA (18歳)',out)
    if c['id'] not in ('PN','CS','XS'):self.assertIn('<SUMMARYSHEET VERSION=R1.0>',plan(sel,r,draft,'JARL R1.0',info,context=v).preview())
    else:
     with self.assertRaisesRegex(ValueError,'R2.1'):plan(sel,r,draft,'JARL R1.0',info,context=v)
     info['age']='69';info['licensedate']='2023-04-26'
     with self.assertRaises(ValueError):plan(sel,r,draft,'JARL R2.1',info,context=v)
    self.assertEqual(p.read_bytes(),original)
 def test_strict_new_schema_values(self):
  r=rule();self.assertEqual(loads(dumps(r)),r)
  for q in ({'min_age':True},{'license_since':'2023-01-01'},{'operators_max_age':-1}):
   bad=deepcopy(r);bad['event']['categories'][0]['qualification']=q
   with self.assertRaises(ValueError):loads(dumps(bad))

if __name__=='__main__':unittest.main()
