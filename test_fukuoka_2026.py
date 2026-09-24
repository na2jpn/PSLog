from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import unittest,tempfile,json
from PySide6.QtWidgets import QComboBox
from test_contest_batch10 import ExportFixture,rule,context
from contest_rules import score,loads,dumps,RuleStore
from contest_export import plan
from contest_event_ui import EventDialog
from contest_submit_ui import SubmissionPane
from storage import Repository
ROOT=Path(__file__).parent
def r():return rule('fukuoka')
def row(**kw):return dict(dict(date='2026-09-12',time='21:00',band='430',mode='CW',call='JA6AAA',sent='13',exchange='400101'),**kw)
def ctx(spec,code,kind='stationary',power=None):
 v=context(spec,code,power);v['operation_kind']=kind;return v
class FukuokaTests(ExportFixture):
 def test_all_32_categories_r10_output_and_original_unchanged(self):
  spec=r();self.assertEqual({c['id'] for c in spec['event']['categories']},{g+p+m for g in ['L','H','A','VU','AB'] for p in ['F','X'] for m in ['C','P','CP']}|{'MOCP','MXCP'})
  for c in spec['event']['categories']:
   with self.subTest(c=c['id']):
    v=ctx(spec,c['id']);q=row(band=c['bands'][0],mode=c['modes'][0],sent=c['sent_codes'][0]);s=score(spec,[q],v);self.assertEqual(s.total,3,s.problems)
    p,b,sel,draft,info=self.fixture(spec,[q],v,comments='元の意見',multioplist='JH1HST, JA6AAA' if c['operator']=='MO' else '')
    out=plan(sel,spec,draft,'JARL R1.0',info,context=v).preview();self.assertIn('<CATEGORYCODE>'+c['id']+'</CATEGORYCODE>',out);self.assertIn('<TOTALSCORE>3</TOTALSCORE>',out);self.assertEqual(p.read_bytes(),b);self.assertEqual(info['comments'],'元の意見')
 def test_outside_only_allowed_no_fukuoka_minimum(self):
  spec=r();v=ctx(spec,'VUXCP');qs=[row(exchange='10'),row(exchange='13',call='JA1BBB')];s=score(spec,qs,v);self.assertEqual((s.points,s.multi1,s.total),(2,2,4))
  self.assertEqual(score(spec,[row(exchange='10',mode='SSB')],v).total,1)
 def test_three_vs_one_mode_duplicate_and_multis(self):
  spec=r();qs=[row(mode=m) for m in ['CW','SSB','FM']]+[row(exchange='10',call='JA1BBB')];s=score(spec,qs,ctx(spec,'ABXCP'));self.assertEqual([x['points'] for x in s.rows],[3,3,0,1]);self.assertEqual((s.multi1,s.total),(2,14))
  qs=[row(),row(date='2026-09-13',time='06:00')];self.assertEqual(score(spec,qs,ctx(spec,'ABXC')).total,3)
 def test_region_dictionary_and_aliases(self):
  spec=r();db=json.loads((ROOT/'config/db/contest/fukuoka_2026.json').read_text(encoding='utf-8'));self.assertEqual([len(x) for x in db['groups'].values()],[27,11,14])
  for x in ['40','4001','4021','40001A','409999']:
   self.assertIsNone(score(spec,[row(exchange=x)],ctx(spec,'ABXC')).total)
  self.assertEqual(score(spec,[row(exchange='400101'),row(exchange='400102',call='JA6BBB')],ctx(spec,'ABXC')).total,12)
  self.assertEqual(score(spec,[row(band='1.8'),row(band='1.9')],ctx(spec,'LXC')).total,3)
  self.assertIsNone(score(spec,[row(sent='4007')],ctx(spec,'LXC')).total)
 def test_time_windows_and_band_boundaries(self):
  spec=r();qs=[row(time='20:59'),row(),row(date='2026-09-13',time='00:00'),row(date='2026-09-13',time='05:59'),row(date='2026-09-13',time='06:00',call='JA6BBB'),row(date='2026-09-13',time='15:00'),row(band='1200'),row(band='10')];s=score(spec,qs,ctx(spec,'ABXC'));self.assertEqual([x['points'] for x in s.rows],[0,3,0,0,3,0,0,0]);self.assertEqual(s.total,6)
  self.assertEqual(score(spec,[row(band='7'),row(band='14')],ctx(spec,'LXC')).total,3)
  self.assertEqual(score(spec,[row(band='7'),row(band='14')],ctx(spec,'HXC')).total,3)
 def test_operation_power_boundaries_so_and_mo(self):
  spec=r()
  for code in ['ABXC','MXCP']:
   for kind,allowed,over in [('stationary',100,100.001),('portable',50,50.001)]:
    v=ctx(spec,code,kind,allowed);self.assertEqual(score(spec,[row()],v).total,3);v['power']=over;self.assertIsNone(score(spec,[row()],v).total);self.assertEqual(v['power'],over);self.assertNotEqual(v.get('submission_mode'),'checklog')
    v['submission_mode']='checklog';self.assertIsNone(score(spec,[row()],v).total)
  for kind in ['',None,'unknown']:
   self.assertIsNone(score(spec,[row()],ctx(spec,'ABXC',kind,50)).total)
 def test_submission_power_declaration_and_portable_call(self):
  spec=r();v=ctx(spec,'ABXC','portable',50);p,b,sel,draft,info=self.fixture(spec,[row()],v,opplace='Soka site',portable=True);self.assertIn('Soka site',plan(sel,spec,draft,'JARL R1.0',info,context=v).preview())
  info['portable']=False
  with self.assertRaisesRegex(ValueError,'運用形態'):plan(sel,spec,draft,'JARL R1.0',info,context=v)
  info['portable']=True;info['opplace']=''
  with self.assertRaisesRegex(ValueError,'運用地'):plan(sel,spec,draft,'JARL R1.0',info,context=v)
  v=ctx(spec,'ABXC','stationary',100);p,b,sel,draft,info=self.fixture(spec,[row()],v,own='JH1HST/1',opplace='site')
  with self.assertRaisesRegex(ValueError,'移動表記'):plan(sel,spec,draft,'JARL R1.0',info,context=v)
 def test_mo_calls_comments_and_club_so(self):
  spec=r();v=ctx(spec,'MXCP');p,b,sel,draft,info=self.fixture(spec,[row()],v,multioplist='JH1HST JA6AAA',comments='保持')
  for _ in range(2):self.assertEqual(plan(sel,spec,draft,'JARL R1.0',info,context=v).preview().count('全運用者コール: JH1HST, JA6AAA'),1)
  self.assertEqual(info['comments'],'保持')
  for text in ['', 'JH1HST JH1HST', '試験 太郎']:
   info['multioplist']=text
   with self.assertRaises(ValueError):plan(sel,spec,draft,'JARL R1.0',info,context=v)
  v=ctx(spec,'ABXC');p,b,sel,draft,info=self.fixture(spec,[row()],v,own='JS1YJY');self.assertIn('JS1YJY',plan(sel,spec,draft,'JARL R1.0',info,context=v).preview())
 def test_gui_operation_keeps_power_and_transfers_declaration(self):
  spec=r();v=ctx(spec,'ABXC','stationary',100);e=EventDialog(spec['event'],v);self.assertEqual(e.category.count(),32);e.operation_kind.setCurrentIndex(e.operation_kind.findData('portable'));self.assertEqual(e.power.value(),100);self.assertIn('50',e.summary.text());e.power.setValue(50);e.apply();self.assertEqual(e.context['operation_kind'],'portable');v=e.context;e.deleteLater()
  p,b,sel,draft,info=self.fixture(spec,[row()],v);tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);fmt=QComboBox();fmt.addItem('JARL R1.0');w=SimpleNamespace(repo=Repository(tmp.name),format=fmt,selection=sel,draft=draft,loaded_scope=('JH1HST',),rule=spec,result=score(spec,[row()],v),event_context=lambda:v,activity_name='コンテスト');pane=SubmissionPane(w);pane.set_context();self.assertTrue(pane.fields['portable'].isChecked());pane.deleteLater();fmt.deleteLater()
 def test_schema_pack_format_and_other_contests_unchanged(self):
  for change in [lambda s:s['event'].update(power_by_operation=dict(stationary=100)),lambda s:s['event'].update(power_by_operation=dict(stationary=100,portable=0)),lambda s:s['event']['categories'][0].update(operator_list_format='calls')]:
   spec=r();change(spec)
   with self.assertRaises(ValueError):loads(dumps(spec))
  import rule_pack
  with tempfile.TemporaryDirectory() as t:
   store=RuleStore(Path(t));pack=ROOT/'distribution/rules/fukuoka_2026_r1.zip';self.assertEqual(rule_pack.install(store,rule_pack.preview(store,pack)),1);self.assertEqual(rule_pack.install(store,rule_pack.preview(store,pack)),0)
  spec=r();v=ctx(spec,'ABXC');p,b,sel,draft,info=self.fixture(spec,[row()],v)
  with self.assertRaises(ValueError):plan(sel,spec,draft,'JARL R2.1',info,context=v)
  self.assertNotIn('power_by_operation',rule('all_chiba')['event'])
if __name__=='__main__':unittest.main()
