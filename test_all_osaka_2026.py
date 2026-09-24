from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import unittest,tempfile
from PySide6.QtWidgets import QComboBox
from PySide6.QtCore import Qt
from test_contest_batch10 import ExportFixture,rule,context
from contest_rules import score,loads,dumps,RuleStore
from contest_export import plan,key
from contest import entries
from contest_submit_ui import DetailsDialog,SubmissionPane
from contest_event_ui import EventDialog
from storage import Repository
ROOT=Path(__file__).parent
def r():return rule('all_osaka')
def row(**kw):return dict(dict(date='2026-11-01',time='06:00',band='7',mode='CW',call='JA3AAA',own='JH1HST',sent='13',exchange='2506'),**kw)
def ctx(spec,code):
 v=context(spec,code);v['operating_locations']=dict(cw='Osaka site',phone='Soka site',digital='Osaka site')
 if 'YLM' in code:v.update(qualification_basis='young',birthdate='2006-11-02')
 return v
class OsakaTests(ExportFixture):
 def fixture2(self,spec,qs,v,**kw):
  f=deepcopy(spec)
  for c in f['event']['categories']:c.setdefault('operator','SO')
  cat=next(c for c in spec['event']['categories'] if c['id']==v['category'])
  p,b,sel,draft,info=self.fixture(f,qs,v,category=cat.get('submission_code',cat['id']),opplace=v['operating_locations'][cat['location_group']],**kw)
  for rec,q in zip(sel.rows,qs):
   for k in ['operator_name','operator_birthdate','operator_yl']:
    if k in q:draft[key(rec)][k]=q[k]
  return p,b,sel,draft,info
 def test_all_58_categories_score_output_and_source_unchanged(self):
  spec=r();self.assertEqual(len(spec['event']['categories']),58)
  for c in spec['event']['categories']:
   with self.subTest(c=c['id']):
    v=ctx(spec,c['id']);q=row(band=c['bands'][0],mode=c['modes'][0],time='12:30' if c['location_group']=='phone' else '06:00',sent='2503' if c['id'].endswith('-O') else '13')
    if 'YLM' in c['id']:q.update(sent='2503Y',operator_name='試験 太郎',operator_birthdate=v['birthdate'])
    s=score(spec,[q],v);self.assertEqual(s.total,1,s.problems)
    p,b,sel,draft,info=self.fixture2(spec,[q],v,comments='保持',multioplist='JH1HST / 試験 太郎 / 二アマ' if c.get('operator')=='MO' else '')
    out=plan(sel,spec,draft,'JARL R1.0',info,context=v).preview();self.assertIn('<CATEGORYCODE>'+c.get('submission_code',c['id'])+'</CATEGORYCODE>',out);self.assertIn('<TOTALSCORE>1</TOTALSCORE>',out);self.assertEqual(info['comments'],'保持');self.assertEqual(p.read_bytes(),b)
 def test_mode_times_independent_four_submissions(self):
  spec=r();qs=[row(time='11:29'),row(time='11:30',call='JA3BBB'),row(mode='SSB',time='12:29',call='JA3CCC'),row(mode='SSB',time='12:30'),row(mode='FM',time='12:31'),row(mode='RTTY',time='12:00'),row(mode='SSTV',time='12:00'),row(mode='RTTY',time='18:00',call='JA3DDD')]
  for code in ['CM','FM','RTTY','SSTV']:
   s=score(spec,qs,ctx(spec,code));self.assertEqual(s.total,1,(code,s.problems))
  self.assertEqual(score(spec,[row(mode='SSB',time='12:30',band='1.8')],ctx(spec,'F19')).total,1)
 def test_received_suffix_points_and_common_region(self):
  spec=r();qs=[row(),row(call='JA3BBB',exchange='2506Y'),row(call='JK3ZKX',exchange='2506X'),row(call='JA3YRL/3',exchange='2506X')];s=score(spec,qs,ctx(spec,'CM'));self.assertEqual([x['points'] for x in s.rows],[1,2,4,4]);self.assertEqual((s.multi1,s.total),(1,11))
  self.assertEqual(score(spec,[row(exchange='2506Y'),row(exchange='2506')],ctx(spec,'CM')).total,2)
  self.assertEqual(score(spec,[row(exchange='2506'),row(exchange='2506Y')],ctx(spec,'CM')).total,1)
 def test_special_calls_and_regions_never_substring_guessed(self):
  spec=r();v=ctx(spec,'CM')
  for call,ex in [('JA3AAA','2506X'),('JA3RL','2506X'),('JK3ZKX','2503X'),('JK3ZKX','2506'),('JA3YRL/3/P','2506X'),('JA3YRL','2506Y')]:self.assertIsNone(score(spec,[row(call=call,exchange=ex)],v).total)
  for ex in ['13X','13Y','13']:
   s=score(spec,[row(exchange=ex),row(call='JA3BBB')],v);self.assertEqual([x['points'] for x in s.rows],[0,1]);self.assertEqual(s.total,1)
  self.assertIsNone(score(spec,[row(exchange='2506XY')],v).total)
 def test_sent_y_per_qso_operator_and_twentieth_birthday(self):
  spec=r();v=ctx(spec,'CA-O');qs=[row(sent='2503Y',operator_name='JA3AAA / 若年',operator_birthdate='2006-11-02'),row(sent='2503',call='JA3BBB')];s=score(spec,qs,v);self.assertEqual(s.total,2,s.problems)
  qs[0]['operator_birthdate']='2006-11-01';self.assertIsNone(score(spec,qs,v).total);qs[0]['operator_yl']=True;self.assertEqual(score(spec,qs,v).total,2)
  qs[0]['operator_name']='';self.assertIsNone(score(spec,qs,v).total)
  self.assertIsNone(score(spec,[row(sent='13Y',operator_name='試験',operator_yl=True)],ctx(spec,'CM')).total)
  qs=[row(sent='2503Y',operator_name='A',operator_yl=True),row(sent='2503Y',operator_name='B',operator_yl=True,call='JA3BBB')];self.assertIsNone(score(spec,qs,ctx(spec,'CM-O')).total);self.assertEqual(score(spec,qs,ctx(spec,'CA-O')).total,2)
 def test_yl_young_category_and_comments(self):
  spec=r();v=ctx(spec,'CYLM-O');q=row(sent='2503Y',operator_name='試験 太郎',operator_birthdate=v['birthdate']);p,b,sel,draft,info=self.fixture2(spec,[q],v,comments='保持')
  for _ in range(2):
   out=plan(sel,spec,draft,'JARL R1.0',info,context=v).preview();self.assertEqual(out.count('Y送信の実運用者:'),1);self.assertIn('生年月日: 2006-11-02',out)
  self.assertEqual(info['comments'],'保持');v['birthdate']='2006-11-01';self.assertIsNone(score(spec,[q],v).total)
  v['qualification_basis']='yl';q['operator_yl']=True;self.assertEqual(score(spec,[q],v).total,1);q['sent']='2503';self.assertIsNone(score(spec,[q],v).total)
 def test_locations_separate_phone_and_digital_match(self):
  spec=r();v=ctx(spec,'RTTY');q=row(mode='RTTY',time='12:00');self.assertEqual(score(spec,[q],v).total,1)
  v['operating_locations']['digital']='third site';self.assertIsNone(score(spec,[q],v).total);v['operating_locations']['digital']='Soka site';self.assertEqual(score(spec,[q],v).total,1)
  p,b,sel,draft,info=self.fixture2(spec,[q],v);info['opplace']='Other'
  with self.assertRaisesRegex(ValueError,'運用地'):plan(sel,spec,draft,'JARL R1.0',info,context=v)
  v=ctx(spec,'CM');v['operating_locations']['digital']='';self.assertEqual(score(spec,[row()],v).total,1)
 def test_sent_x_uses_actual_selected_own_and_digital_mo_roster(self):
  spec=r();v=ctx(spec,'CM-O');q=row(sent='2506X',own='JK3ZKX');self.assertEqual(score(spec,[q],v).total,1)
  p,b,sel,draft,info=self.fixture2(spec,[q],v,own='JH1HST')
  with self.assertRaisesRegex(ValueError,'指定局'):plan(sel,spec,draft,'JARL R1.0',info,context=v)
  p,b,sel,draft,info=self.fixture2(spec,[q],v,own='JK3ZKX');self.assertIn('2506X',plan(sel,spec,draft,'JARL R1.0',info,context=v).preview())
  v=ctx(spec,'RTTY');p,b,sel,draft,info=self.fixture2(spec,[row(mode='RTTY')],v,multiop=True,multioplist='JA3AAA / 試験 太郎 / 二アマ');self.assertIn('全運用者',plan(sel,spec,draft,'JARL R1.0',info,context=v).preview());info['multioplist']=''
  with self.assertRaises(ValueError):plan(sel,spec,draft,'JARL R1.0',info,context=v)
 def test_ui_operator_columns_paging_location_and_summary(self):
  spec=r();v=ctx(spec,'CYLM-O');qs=[row(sent='2503Y',operator_name='試験 太郎',operator_birthdate=v['birthdate'],time=f'{6+i//60:02}:{i%60:02}') for i in range(101)];p,b,sel,draft,info=self.fixture2(spec,qs,v);d=DetailsDialog(sel,draft,event=spec['event']);self.assertEqual(d.table.columnCount(),12);self.assertEqual(d.table.rowCount(),100);d.table.item(0,11).setCheckState(Qt.Checked);self.assertTrue(d.draft[key(sel.rows[0])]['operator_yl']);d.move(1);self.assertEqual(d.table.rowCount(),1);self.assertEqual(d.table.item(0,9).text(),'試験 太郎');d.deleteLater();self.assertEqual(p.read_bytes(),b)
  e=EventDialog(spec['event'],v);self.assertIn('CY/LM-O',e.category.currentText());self.assertEqual(e.qualification.birth.text(),v['birthdate']);e.locations['phone'].setText('New site');e.apply();self.assertEqual(e.context['operating_locations']['phone'],'New site');e.deleteLater()
  tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);fmt=QComboBox();fmt.addItem('JARL R1.0');w=SimpleNamespace(repo=Repository(tmp.name),format=fmt,selection=sel,draft=draft,loaded_scope=('JH1HST',),rule=spec,result=score(spec,qs,v),event_context=lambda:v,activity_name='コンテスト');pane=SubmissionPane(w);pane.set_context();self.assertEqual(pane.fields['opplace'].text(),'Osaka site');self.assertEqual(pane.fields['category'].text(),'CY/LM-O');pane.deleteLater();fmt.deleteLater()
 def test_schema_pack_reimport_and_other_contest_suffix_rejection(self):
  for change in [lambda s:s['event']['exchange']['special_calls'].update(JK3ZKX=['13']),lambda s:s['event']['operating_locations']['matches'].update(digital=['digital']),lambda s:s['event']['categories'][0].update(location_group='unknown'),lambda s:s['event']['categories'][0].update(qualification=dict(yl_or_younger_than=20))]:
   spec=r();change(spec)
   with self.assertRaises(ValueError):loads(dumps(spec))
  import rule_pack
  with tempfile.TemporaryDirectory() as t:
   store=RuleStore(Path(t));pack=ROOT/'distribution/rules/all_osaka_2026_r1.zip';self.assertEqual(rule_pack.install(store,rule_pack.preview(store,pack)),1);self.assertEqual(rule_pack.install(store,rule_pack.preview(store,pack)),0)
  ch=rule('all_chiba');v=context(ch,'X-CW');self.assertIsNone(score(ch,[row(date='2026-10-18',time='12:00',exchange='1202Y')],v).total)
if __name__=='__main__':unittest.main()
