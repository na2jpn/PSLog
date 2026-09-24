from copy import deepcopy
from pathlib import Path
import tempfile,unittest
from PySide6.QtWidgets import QApplication
from contest_rules import loads,score,RuleStore
from contest_export import plan,key
from contest import select_logs
from contest_event_ui import EventDialog
from model import QSO
from storage import Repository
from test_six_meter_2026 import rule as six,context as sixctx
ROOT=Path(__file__).parent

def fd():return loads((ROOT/'config/rules/field_day_2026.txt').read_text(encoding='utf-8'))
def ctx(r,code='CA',kind='HOME',power=20):
 c=next(c for c in r['event']['categories'] if c['id']==code)
 return dict(category=code,power=power,fd_class=kind,fd_confirmed=True,flags={f:True for f in r['event']['required_flags']+c['required_flags']})
def q(**kw):return dict(dict(date='2026-08-01',time='21:00',band='7',mode='CW',call='JA1AAA',sent='13M',exchange='10L'),**kw)

class StationTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
 def setup_log(self,r,own='JH1HST',date='2026-08-01'):
  tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);repo=Repository(tmp.name);p=repo.path_for(own,'',date)
  repo.open(p).append(QSO(date,'21:00','50','CW','JA1AAA','599','599','Japan','Soka Japan','',''));sel=select_logs(repo,[p],own)
  draft={key(sel.rows[0]):dict(sent='13L',received='10L',status='確認済み')}
  info=dict(contest=r['event']['submission']['contest'],category='CA',name='試験',address='試験',power='20',date='2026-08-03',signature='試験',oath=True,email='test@example.com')
  return p,sel,draft,info
 def test_fd_factors_and_incomplete_a(self):
  r=fd()
  for kind,want in [('A',2),('B',1),('HOME',1)]:
   s=score(r,[q()],ctx(r,kind=kind));self.assertEqual(s.total,want);self.assertEqual(s.multi2,want)
  v=ctx(r,kind='A');v['fd_confirmed']=False;self.assertIsNone(score(r,[q()],v).total)
  v.pop('fd_class');self.assertIsNone(score(r,[q()],v).total)
 def test_fd_high_is_one_point_and_power_thresholds(self):
  r=fd();s=score(r,[q(),q(band='2400',sent='1319M',exchange='120101P')],ctx(r,kind='A'));self.assertEqual(s.total,8)
  self.assertEqual(score(r,[q(band='1200',sent='13M')],ctx(r,power=15)).total,1)
  self.assertIsNone(score(r,[q(band='144',sent='13M')],ctx(r,power=15)).total)
  self.assertEqual(score(r,[q(band='144',sent='13L')],ctx(r,power=15)).total,1)
  self.assertIsNone(score(r,[q()],ctx(r,power=50.001)).total)
  self.assertIsNone(score(r,[q(exchange='10H')],ctx(r)).total)
 def test_fd_no_second_factor_double_application(self):
  r=fd();r['multi2'].update(kind='fixed',value=2);self.assertIsNone(score(r,[q()],ctx(r,kind='A')).total)
 def test_conditional_fields_and_portable_suffix(self):
  r=six();p,sel,d,info=self.setup_log(r,'JH1HST/1','2026-07-04');v=sixctx()
  with self.assertRaisesRegex(ValueError,'運用地'):plan(sel,r,d,'JARL R2.1',info,context=v)
  info['opplace']='埼玉県草加市 公園';info['guest']=True
  with self.assertRaisesRegex(ValueError,'ゲスト'):plan(sel,r,d,'JARL R2.1',info,context=v)
  info['opcall']='JQ7FIU';out=plan(sel,r,d,'JARL R2.1',info,context=v).preview();self.assertIn('<OPCALLSIGN>JQ7FIU</OPCALLSIGN>',out)
 def test_fd_exports_a_b_home(self):
  r=fd()
  for kind,own in [('A','JH1HST/1'),('B','JH1HST/1'),('HOME','JH1HST')]:
   p,sel,d,info=self.setup_log(r,own);before=p.read_bytes();info.update(fd=True,opplace='埼玉県草加市 公園' if kind!='HOME' else '',powersupply='電池' if kind=='A' else '')
   for f in ('JARL R1.0','JARL R2.1'):
    out=plan(sel,r,d,f,info,context=ctx(r,kind=kind)).preview();n='2' if kind=='A' else '1';self.assertIn('<FDCOEFF>'+n+'</FDCOEFF>',out);self.assertIn('<TOTALSCORE>'+n+'</TOTALSCORE>',out)
   self.assertEqual(p.read_bytes(),before)
 def test_fd_a_requires_actual_source_and_portable(self):
  r=fd();p,sel,d,info=self.setup_log(r,'JH1HST/1');info.update(fd=True,opplace='埼玉県草加市 公園',powersupply='安定化電源')
  with self.assertRaisesRegex(ValueError,'供給源'):plan(sel,r,d,'JARL R2.1',info,context=ctx(r,kind='A'))
  p,sel,d,info=self.setup_log(r);info.update(fd=True,opplace='埼玉県草加市 公園',powersupply='電池')
  with self.assertRaisesRegex(ValueError,'移動表記'):plan(sel,r,d,'JARL R2.1',info,context=ctx(r,kind='A'))
 def test_whole_checklog_bypasses_entry_qualification_and_numbers(self):
  r=six();p,sel,d,info=self.setup_log(r,date='2026-07-04');before=p.read_bytes();v=dict(submission_mode='checklog',power=20);info['category']='CHECKLOG';d[key(sel.rows[0])]['sent']='99H'
  for f in ('JARL R1.0','JARL R2.1'):
   out=plan(sel,r,d,f,info,context=v).preview();self.assertIn('<CATEGORYCODE>CHECKLOG</CATEGORYCODE>',out);self.assertIn('<TOTALSCORE>0</TOTALSCORE>',out);self.assertIn('99H',out);self.assertNotIn('\nX ',out)
  self.assertEqual(p.read_bytes(),before)
 def test_whole_checklog_not_a_way_to_claim_entry_score(self):
  r=six();p,sel,d,info=self.setup_log(r,date='2026-07-04')
  with self.assertRaisesRegex(ValueError,'部門'):plan(sel,r,d,'JARL R2.1',info,context=dict(submission_mode='checklog',power=20))
  v=sixctx();info['category']='CHECKLOG'
  with self.assertRaisesRegex(ValueError,'部門'):plan(sel,r,d,'JARL R2.1',info,context=v)
 def test_checklog_rejects_unsupported_rule_and_fd_claim(self):
  r=six();p,sel,d,info=self.setup_log(r,date='2026-07-04');info['category']='CHECKLOG';v=dict(submission_mode='checklog',power=20)
  broken=deepcopy(r);broken.pop('event')
  with self.assertRaisesRegex(ValueError,'大会条件'):plan(sel,broken,d,'JARL R2.1',info,context=v)
  info['fd']=True
  with self.assertRaisesRegex(ValueError,'得点係数'):plan(sel,r,d,'JARL R2.1',info,context=v)
 def test_ui_can_choose_checklog_without_category_and_fd_class(self):
  d=EventDialog(six()['event'],{});d.purpose.setCurrentIndex(1);d.power.setValue(20);d.apply();self.assertEqual(d.context['submission_mode'],'checklog');d.deleteLater()
  d=EventDialog(fd()['event'],ctx(fd()));d.fd_class.setCurrentIndex(d.fd_class.findData('B'));d.apply();self.assertEqual(d.context['fd_class'],'B');d.deleteLater()
 def test_fd_pack_and_initial_scope(self):
  import rule_pack
  with tempfile.TemporaryDirectory() as tmp:
   store=RuleStore(Path(tmp));rule_pack.install(store,rule_pack.preview(store,ROOT/'distribution/rules/field_day_2026_ca_xa_r1.zip'));r=store.read(store.files()[0])[0];self.assertEqual({c['id'] for c in r['event']['categories']},{'CA','XA'})

if __name__=='__main__':unittest.main()
