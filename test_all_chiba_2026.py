from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import unittest,tempfile
from PySide6.QtWidgets import QComboBox
from test_contest_batch10 import ExportFixture,rule,context
from contest_rules import score,loads,dumps,RuleStore
from contest_export import plan
from contest_event_ui import EventDialog
from contest_submit_ui import SubmissionPane
from storage import Repository
ROOT=Path(__file__).parent
def r():return rule('all_chiba')
def row(**kw):return dict(dict(date='2026-10-18',time='12:00',band='430',mode='CW',call='JA1AAA',sent='13',exchange='120101'),**kw)
def ctx(spec,code):
 v=context(spec,code)
 if 'JUNIOR' in code:v['age']=18
 if 'CLUB' in code:v['station_type']='club'
 return v
class ChibaTests(ExportFixture):
 def fixture2(self,spec,rows,v,**kw):
  # Reuse storage fixture; the flexible club category supports either SO or MO.
  f=deepcopy(spec)
  for c in f['event']['categories']:c.setdefault('operator','SO')
  cat=next(c for c in spec['event']['categories'] if c['id']==v['category'])
  return self.fixture(f,rows,v,category=cat['submission_code'],opplace='Soka Saitama Japan',**kw)
 def test_all_42_categories_r10_and_original_unchanged(self):
  spec=r();self.assertEqual(len(spec['event']['categories']),42)
  for c in spec['event']['categories']:
   with self.subTest(c=c['id']):
    v=ctx(spec,c['id']);q=row(band=c['bands'][0],mode=c['modes'][0],sent='1202' if c['id'].startswith('C-') else '13');s=score(spec,[q],v);expected=3 if q['mode']=='CW' else 2;self.assertEqual(s.total,expected,s.problems)
    p,before,sel,draft,info=self.fixture2(spec,[q],v,multioplist='試験 太郎 / 二アマ' if 'CLUB' in c['id'] else '',comments='元の意見')
    out=plan(sel,spec,draft,'JARL R1.0',info,context=v).preview();self.assertIn('<CATEGORYCODE>'+c['submission_code']+'</CATEGORYCODE>',out);self.assertIn(f'<TOTALSCORE>{expected}</TOTALSCORE>',out)
    self.assertEqual(p.read_bytes(),before);self.assertEqual(info['comments'],'元の意見')
 def test_region_points_and_phone_common_duplicates(self):
  spec=r();qs=[row(mode=m) for m in ['CW','SSB','FM','DV','C4FM']];s=score(spec,qs,ctx(spec,'X-MIX'));self.assertEqual([x['points'] for x in s.rows],[3,2,0,0,0]);self.assertEqual((s.multi1,s.total),(1,5))
  qs=[row(sent='1202',exchange='13',mode=m) for m in ['CW','SSB']];self.assertEqual(score(spec,qs,ctx(spec,'C-MIX')).total,3)
  qs=[row(exchange='13'),row(exchange='1202',call='JA1BBB')];s=score(spec,qs,ctx(spec,'X-MIX'));self.assertEqual([x['points'] for x in s.rows],[0,3]);self.assertEqual(s.total,3)
  self.assertIsNone(score(spec,[row(mode='CW TEST')],ctx(spec,'X-CW')).total)
 def test_region_dictionary_does_not_guess_ward(self):
  spec=r();v=ctx(spec,'X-CW')
  for number in ['12','1201','129999','01']:self.assertIsNone(score(spec,[row(exchange=number)],v).total)
  self.assertEqual(score(spec,[row(sent='1202')],v).total,None)
  for number in ['101','114','48']:self.assertEqual(score(spec,[row(sent='1202',exchange=number)],ctx(spec,'C-CW')).total,2)
 def test_bands_upper_single_and_no_virtual_merge(self):
  spec=r();v=ctx(spec,'X-2400UP');self.assertEqual(score(spec,[row(band='10100')],v).total,3)
  qs=[row(band='2400'),row(band='10100'),row(band='10400')];s=score(spec,qs,v);self.assertEqual((s.points,s.multi1,s.total),(9,3,27));self.assertEqual(score(spec,qs,ctx(spec,'X-MIX')).total,3)
  self.assertEqual(score(spec,[row(band='10G',contest_band='10100')],v).total,3);self.assertIsNone(score(spec,[row(band='10G')],v).total)
  for code in ['X-QRP','X-QRP_CW']:self.assertEqual(score(spec,[row(band='1200'),row()],ctx(spec,code)).total,3)
  v=ctx(spec,'X-QRP');v['power']=5.001;self.assertIsNone(score(spec,[row()],v).total)
 def test_digital_data_excluded_voice_phone_and_boundaries(self):
  spec=r();v=ctx(spec,'X-MIX');qs=[row(mode='RTTY'),row(mode='FT8'),row(mode='DV'),row(time='11:59',call='JA1BBB'),row(time='18:00',call='JA1CCC')];s=score(spec,qs,v);self.assertEqual([x['points'] for x in s.rows],[0,0,2,0,0]);self.assertEqual(s.total,2)
  self.assertEqual(score(spec,[row(band='1.8'),row(band='1.9')],ctx(spec,'X-19')).total,3)
 def test_newcomer_age_comments_no_r21_forcing(self):
  spec=r()
  for code,field,bad in [('X-JUNIOR','age',19),('X-NEWCOMER','licensedate','2023-10-17')]:
   v=ctx(spec,code);p,b,sel,draft,info=self.fixture2(spec,[row()],v,comments='維持')
   word='運用者年齢: 18歳' if field=='age' else '初回局免許年月日: 2023-10-18'
   for _ in range(2):self.assertEqual(plan(sel,spec,draft,'JARL R1.0',info,context=v).preview().count(word),1)
   self.assertEqual(info['comments'],'維持');v[field]=bad;self.assertIsNone(score(spec,[row()],v).total)
  v=ctx(spec,'X-NEWCOMER');v['licensedate']='2026-10-19';self.assertIsNone(score(spec,[row()],v).total)
 def test_station_category_and_club_so_mo_roster(self):
  spec=r();v=ctx(spec,'X-MIX');v['station_type']='club';self.assertIsNone(score(spec,[row()],v).total)
  v=ctx(spec,'X-CLUB');v['station_type']='individual';self.assertIsNone(score(spec,[row()],v).total);v['station_type']='club'
  p,b,sel,draft,info=self.fixture2(spec,[row()],v)
  with self.assertRaisesRegex(ValueError,'姓名'):plan(sel,spec,draft,'JARL R1.0',info,context=v)
  info['multioplist']='試験 太郎 / 二アマ'
  for mo in [False,True]:
   info['multiop']=mo;out=plan(sel,spec,draft,'JARL R1.0',info,context=v).preview();self.assertIn('全運用者(姓名・無線従事者資格)',out);self.assertIn('<CATEGORYCODE>X-社団',out)
  v=ctx(spec,'X-MIX');p,b,sel,draft,info=self.fixture2(spec,[row()],v,multiop=True,multioplist='試験')
  with self.assertRaisesRegex(ValueError,'シングル'):plan(sel,spec,draft,'JARL R1.0',info,context=v)
 def test_required_place_format_and_registered_club(self):
  spec=r();v=ctx(spec,'X-MIX');p,b,sel,draft,info=self.fixture2(spec,[row()],v)
  for fmt in ['JARL R2.1','Cabrillo']:
   with self.assertRaises(ValueError):plan(sel,spec,draft,fmt,info,context=v)
  info['opplace']=''
  with self.assertRaises(ValueError):plan(sel,spec,draft,'JARL R1.0',info,context=v)
  info['opplace']='Soka';info.update(clubnumber='12-01-01',clubname='試験クラブ');self.assertIn('試験クラブ',plan(sel,spec,draft,'JARL R1.0',info,context=v).preview())
  info['clubnumber']='13-01-01';out=plan(sel,spec,draft,'JARL R1.0',info,context=v).preview();self.assertIn('<REGCLUBNUMBER>13-01-01</REGCLUBNUMBER>',out)
  info['clubnumber']='12-xx-xx'
  with self.assertRaises(ValueError):plan(sel,spec,draft,'JARL R1.0',info,context=v)
 def test_gui_official_codes_and_newcomer_comment_note(self):
  spec=r();v=ctx(spec,'X-NEWCOMER');d=EventDialog(spec['event'],v);self.assertEqual(d.category.count(),42);self.assertIn('X-ニューカマー',d.category.currentText());self.assertIn('個人局',d.summary.text());d.deleteLater()
  p,b,sel,draft,info=self.fixture2(spec,[row()],v);tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);fmt=QComboBox();fmt.addItem('JARL R1.0');w=SimpleNamespace(repo=Repository(tmp.name),format=fmt,selection=sel,draft=draft,loaded_scope=('JH1HST',),rule=spec,result=score(spec,[row()],v),event_context=lambda:v,activity_name='コンテスト');pane=SubmissionPane(w);pane.set_context();self.assertEqual(pane.fields['category'].text(),'X-ニューカマー');self.assertNotIn('R2.1を選択',pane.overview.text());self.assertIn('2023-10-18',pane.overview.text());pane.deleteLater();fmt.deleteLater()
 def test_schema_guards_and_pack_reimport(self):
  for mutate in [lambda s:s['event']['categories'][0].update(submission_code='<BAD>'),lambda s:s['event']['categories'][0].update(station_types=['special']),lambda s:s['event']['categories'][0].update(submission_code='C-電話'),lambda s:s['event']['categories'][0].update(qualification=dict(license_output='comments'))]:
   spec=r();mutate(spec)
   with self.assertRaises(ValueError):loads(dumps(spec))
  import rule_pack
  with tempfile.TemporaryDirectory() as t:
   store=RuleStore(Path(t));pack=ROOT/'distribution/rules/all_chiba_2026_r1.zip';self.assertEqual(rule_pack.install(store,rule_pack.preview(store,pack)),1);self.assertEqual(rule_pack.install(store,rule_pack.preview(store,pack)),0)
if __name__=='__main__':unittest.main()
