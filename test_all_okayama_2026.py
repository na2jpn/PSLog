from pathlib import Path
from types import SimpleNamespace
import unittest,tempfile
from PySide6.QtWidgets import QComboBox
from test_contest_batch10 import ExportFixture,rule,context
from contest_rules import score,loads,dumps,RuleStore
from contest_export import plan,key
from contest_event_ui import EventDialog
from contest_submit_ui import SubmissionPane
from storage import Repository
ROOT=Path(__file__).parent
def r():return rule('all_okayama')
def row(**kw):return dict(dict(date='2026-09-20',time='09:00',band='7',mode='CW',call='JA4AAA',sent='13',exchange='310101'),**kw)
def ctx(spec,code):return context(spec,code)
class OkayamaTests(ExportFixture):
 def fixture2(self,spec,qs,v,**kw):return self.fixture(spec,qs,v,opplace='Soka Saitama Japan',**kw)
 def test_all_72_categories_r10_jst_utc_and_original_unchanged(self):
  spec=r();expected={g+a+'-'+o+m+p for g in 'LHV' for a in 'OX' for o in 'SM' for m in 'CPD' for p in ['', 'P']};self.assertEqual({c['id'] for c in spec['event']['categories']},expected)
  for c in spec['event']['categories']:
   with self.subTest(c=c['id']):
    v=ctx(spec,c['id']);q=row(band=c['bands'][0],mode=c['modes'][0],sent=c['sent_codes'][0]);self.assertEqual(score(spec,[q],v).total,1)
    p,b,sel,draft,info=self.fixture2(spec,[q],v)
    for zone,time in [('JST','09:00'),('UTC','00:00')]:
     info['zone']=zone;out=plan(sel,spec,draft,'JARL R1.0',info,context=v).preview();self.assertIn('<TOTALSCORE>1</TOTALSCORE>',out);self.assertIn('2026-09-20 '+time,out);self.assertIn('DATE ('+zone+')',out)
    self.assertEqual(p.read_bytes(),b)
 def test_three_modes_and_three_groups_export_independently(self):
  spec=r();qs=[row(band=b,mode=m) for b in ['7','14','430'] for m in ['CW','SSB','RTTY']]
  for g,band in [('L','7'),('H','14'),('V','430')]:
   for suffix,mode in [('C','CW'),('P','SSB'),('D','RTTY')]:
    v=ctx(spec,g+'X-S'+suffix);p,b,sel,draft,info=self.fixture2(spec,qs,v);prepared=plan(sel,spec,draft,'JARL R1.0',info,context=v);out=prepared.preview();lines=[x for x in out.splitlines() if x.startswith('2026-09-20 ')]
    self.assertEqual(len(lines),1);self.assertIn(' '+band+' '+mode+' ',lines[0]);self.assertEqual(prepared.qsos,1);self.assertEqual(len(sel.rows),9);self.assertEqual(len(prepared.sessions),len(sel.sessions));self.assertEqual(p.read_bytes(),b)
 def test_scope_keeps_zero_duplicates_and_x_only_in_correct_category(self):
  spec=r();v=ctx(spec,'LX-SP');qs=[row(mode='SSB'),row(mode='AM'),row(mode='SSB',call='JA1BBB',exchange='10'),row(mode='CW',checklog=True),row(mode='RTTY')];p,b,sel,draft,info=self.fixture2(spec,qs,v);out=plan(sel,spec,draft,'JARL R1.0',info,context=v).preview();self.assertEqual(len([x for x in out.splitlines() if x.startswith('2026-09-20 ')]),3);self.assertIn('<SCORE BAND=TOTAL>3,1,1</SCORE>',out);self.assertNotIn(' RTTY ',out);self.assertNotIn(' CW ',out)
 def test_local_only_and_region_no_grid_guess(self):
  spec=r();v=ctx(spec,'LX-SC');s=score(spec,[row(exchange='10'),row(call='JA4BBB')],v);self.assertEqual([x['points'] for x in s.rows],[0,1]);self.assertEqual(s.total,1)
  for number in ['PM95','31','3101','319999']:self.assertIsNone(score(spec,[row(exchange=number)],v).total)
  for number in ['101','114','48']:self.assertEqual(score(spec,[row(sent='310101',exchange=number)],ctx(spec,'LO-SC')).total,1)
  self.assertIsNone(score(spec,[row(sent='310101'),row(sent='310102')],ctx(spec,'LO-SC')).total)
 def test_qrp_boundaries_and_time_modes(self):
  spec=r();v=ctx(spec,'LX-SDP');self.assertEqual(v['power'],5);self.assertEqual(score(spec,[row(mode='RTTY')],v).total,1);v['power']=5.001;self.assertIsNone(score(spec,[row(mode='RTTY')],v).total)
  qs=[row(mode='RTTY'),row(mode='FT8'),row(mode='FT4'),row(time='08:59',mode='RTTY'),row(time='21:00',mode='RTTY')];s=score(spec,qs,ctx(spec,'LX-SD'));self.assertEqual([x['points'] for x in s.rows],[1,0,0,0,0])
 def test_special_station_explicit_checklog_only(self):
  spec=r();v=ctx(spec,'LX-SC');v['station_type']='special';s=score(spec,[row()],v);self.assertIsNone(s.total);self.assertNotEqual(v.get('submission_mode'),'checklog')
  v['submission_mode']='checklog';self.assertEqual(score(spec,[row()],v).total,0);p,b,sel,draft,info=self.fixture2(spec,[row()],v,own='8J1TEST');info['category']='CHECKLOG';out=plan(sel,spec,draft,'JARL R1.0',info,context=v).preview();self.assertIn('<CATEGORYCODE>CHECKLOG</CATEGORYCODE>',out);self.assertIn('<TOTALSCORE>0</TOTALSCORE>',out)
 def test_newcomer_optional_does_not_change_score_and_comment_not_cumulative(self):
  spec=r();v=ctx(spec,'LX-SC');v.update(newcomer_requested=True,newcomer_first_license=True,newcomer_licensedate='2023-09-20');s=score(spec,[row()],v);self.assertEqual(s.total,1)
  for station,own in [('individual','JH1HST'),('club','JS1YJY')]:
   v['station_type']=station;p,b,sel,draft,info=self.fixture2(spec,[row()],v,own=own,comments='保持')
   for _ in range(2):self.assertEqual(plan(sel,spec,draft,'JARL R1.0',info,context=v).preview().count('ニューカマー記念品を申告'),1)
   self.assertEqual(info['comments'],'保持');self.assertEqual(p.read_bytes(),b)
  v['newcomer_requested']=False;p,b,sel,draft,info=self.fixture2(spec,[row()],v);self.assertNotIn('ニューカマー記念品を申告',plan(sel,spec,draft,'JARL R1.0',info,context=v).preview())
 def test_newcomer_mo_reopening_date_and_checklog_rejected_only_at_submission(self):
  spec=r()
  for code,date,first,whole in [('LX-MC','2023-09-20',True,False),('LX-SC','2023-09-19',True,False),('LX-SC','2026-09-21',True,False),('LX-SC','2023-09-20',False,False),('LX-SC','2023-09-20',True,True)]:
   v=ctx(spec,code);v.update(newcomer_requested=True,newcomer_licensedate=date,newcomer_first_license=first)
   if whole:v['submission_mode']='checklog'
   self.assertIsNotNone(score(spec,[row()],v).total);p,b,sel,draft,info=self.fixture2(spec,[row()],v)
   if whole:info['category']='CHECKLOG'
   with self.assertRaises(ValueError):plan(sel,spec,draft,'JARL R1.0',info,context=v)
 def test_gui_claim_and_station_declared_no_autoswitch(self):
  spec=r();v=ctx(spec,'LX-SC');e=EventDialog(spec['event'],v);self.assertEqual(e.category.count(),72);self.assertFalse(e.newcomer_requested.isChecked());e.station_type.setCurrentIndex(e.station_type.findData('special'));self.assertEqual(e.purpose.currentData(),'entry');e.station_type.setCurrentIndex(e.station_type.findData('individual'));e.newcomer_requested.setChecked(True);e.newcomer_first.setChecked(True);e.newcomer_date.setText('2023-09-20');e.apply();v=e.context;self.assertTrue(v['newcomer_requested']);e.deleteLater()
  p,b,sel,draft,info=self.fixture2(spec,[row()],v);tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);fmt=QComboBox();fmt.addItem('JARL R1.0');w=SimpleNamespace(repo=Repository(tmp.name),format=fmt,selection=sel,draft=draft,loaded_scope=('JH1HST',),rule=spec,result=score(spec,[row()],v),event_context=lambda:v,activity_name='コンテスト');pane=SubmissionPane(w);pane.set_context();self.assertIn('ニューカマー申告',pane.overview.text());self.assertIn('JST/UTC',pane.overview.text());pane.deleteLater();fmt.deleteLater()
 def test_schema_pack_and_existing_scope_is_unchanged(self):
  for change in [lambda s:s['event']['entrant'].update(checklog_only_types=['unknown']),lambda s:s['event']['submission'].update(allowed_zones=['UTC']),lambda s:s['event']['submission'].update(row_scope='points_only'),lambda s:s['event']['newcomer_claim'].update(operators=['SWL'])]:
   spec=r();change(spec)
   with self.assertRaises(ValueError):loads(dumps(spec))
  import rule_pack
  with tempfile.TemporaryDirectory() as t:
   store=RuleStore(Path(t));pack=ROOT/'distribution/rules/all_okayama_2026_r1.zip';self.assertEqual(rule_pack.install(store,rule_pack.preview(store,pack)),1);self.assertEqual(rule_pack.install(store,rule_pack.preview(store,pack)),0)
  self.assertNotIn('row_scope',rule('all_osaka')['event']['submission'])
if __name__=='__main__':unittest.main()
