from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import unittest,tempfile,json
from PySide6.QtWidgets import QComboBox
from test_contest_batch10 import ExportFixture,rule,context
from contest_rules import score,loads,dumps,RuleStore
from contest_export import plan,key
from contest_submit_ui import DetailsDialog,SubmissionPane
from contest_event_ui import EventDialog
from contest import entries
from contest_awards import candidates
from storage import Repository
ROOT=Path(__file__).parent
def urule():return rule('tokyo_uhf')
def srule():return rule('tokyo')
def row(**kw):return dict(dict(date='2026-11-23',time='09:00',band='430',mode='CW',call='JA1AAA',sent='13',exchange='101'),**kw)
def srow(**kw):return row(**dict(dict(date='2026-05-03',band='21'),**kw))
def ctx(r,code):
 c=context(r,code);q=next(x for x in r['event']['categories'] if x['id']==code).get('qualification',{})
 if 'max_age' in q:c['age']=q['max_age']
 return c

class TokyoNewTests(ExportFixture):
 def test_all_18_uhf_categories_and_all_30_spring_outputs(self):
  self.assertEqual({c['id'] for c in urule()['event']['categories']},{p+'X'+s for p in '12' for s in ['A','430','1200','2400','5600','10G']}|{p+'Y'+s for p in '12' for s in ['A','430','1200']})
  self.assertEqual({c['id'] for c in srule()['event']['categories']},{p+m+s for p in '12' for m in 'CXY' for s in ['A','21','28','50','144']})
  for r,make in [(urule(),row),(srule(),srow)]:
   for c in r['event']['categories']:
    with self.subTest(rule=r['id'],category=c['id']):
     v=ctx(r,c['id']);mode='SSB' if c.get('required_mode_families') else 'CW';q=make(band=c['bands'][0],mode=mode,sent='002' if c['id'].startswith('1') else '13');s=score(r,[q],v);self.assertEqual(s.total,2,s.problems)
     p,before,sel,draft,info=self.fixture(r,[q],v,comments='元の意見');out=plan(sel,r,draft,'JARL R1.0',info,context=v).preview();self.assertIn('<TOTALSCORE>2</TOTALSCORE>',out)
     if 'Y' in c['id']:self.assertIn('元の意見 運用者年齢: 18歳',out)
     else:self.assertNotIn('運用者年齢:',out)
     self.assertEqual(info['comments'],'元の意見');self.assertEqual(p.read_bytes(),before)
 def test_separate_10ghz_points_multis_and_raw_choice(self):
  r=urule();v=ctx(r,'2X10G');rows=[row(band='10.1G'),row(band='10.4G'),row(band='10100',mode='FM')];s=score(r,rows,v);self.assertEqual([x['points'] for x in s.rows],[2,2,0]);self.assertEqual((s.multi1,s.total),(2,8))
  self.assertIsNone(score(r,[row(band='10G')],v).total)
  rows=[row(band='10G',contest_band='10100'),row(band='10GHz',contest_band='10400')];self.assertEqual(score(r,rows,v).total,8)
  p,before,sel,draft,info=self.fixture(r,rows,v)
  for rec,source in zip(sel.rows,rows):draft[key(rec)]['contest_band']=source['contest_band']
  self.assertEqual(entries(sel,draft)[0]['contest_band'],'10100');out=plan(sel,r,draft,'JARL R1.0',info,context=v).preview();self.assertIn(' 10100 CW ',out);self.assertIn(' 10400 CW ',out);self.assertIn('<TOTALSCORE>8</TOTALSCORE>',out);self.assertEqual(p.read_bytes(),before)
  draft[key(sel.rows[0])]['contest_band']=''
  with self.assertRaisesRegex(ValueError,'実バンド'):plan(sel,r,draft,'JARL R1.0',info,context=v)
 def test_ambiguous_choice_invalid_or_not_applicable(self):
  r=urule();v=ctx(r,'2XA')
  for b,choice in [('10G','430'),('430','10100'),('10G',None),('10G','10.1G')]:
   self.assertIsNone(score(r,[row(band=b,contest_band=choice)],v).total)
  # Reusing the same draft in XPO must still use XPO's combined band.
  x=rule('xpo');q=row(date='2026-09-21',band='10G',contest_band='10100',exchange='10');self.assertEqual(score(x,[q],context(x,'C2400')).total,1)
  v['submission_mode']='checklog';self.assertIsNone(score(r,[row(band='10G')],v).total);self.assertEqual(score(r,[row(band='10G',contest_band='10400')],v).total,0)
 def test_details_ui_pagination_choices_no_original_change(self):
  r=urule();v=ctx(r,'2X10G');rows=[row(band='10G',time=f'{9+i//60:02}:{i%60:02}') for i in range(101)];p,before,sel,draft,info=self.fixture(r,rows,v);d=DetailsDialog(sel,draft,event=r['event']);self.assertEqual(d.table.columnCount(),10);self.assertEqual(d.table.rowCount(),100)
  combo=d.table.cellWidget(0,9);self.assertEqual(combo.currentData(),'');combo.setCurrentIndex(1);self.assertEqual(d.draft[key(sel.rows[0])]['contest_band'],'10100');d.move(1);self.assertEqual(d.table.rowCount(),1);d.table.cellWidget(0,9).setCurrentIndex(2);d.move(-1);self.assertEqual(d.table.cellWidget(0,9).currentData(),'10100');self.assertEqual(d.draft[key(sel.rows[100])]['contest_band'],'10400');self.assertNotIn('contest_band',draft[key(sel.rows[0])]);self.assertEqual(p.read_bytes(),before);d.deleteLater()
 def test_young_operation_band_is_not_just_score_filter(self):
  r=urule();v=ctx(r,'2YA')
  self.assertEqual(score(r,[row(),row(band='1200')],v).total,8)
  for explicit in (False,True):self.assertIsNone(score(r,[row(),row(band='2400',checklog=explicit)],v).total)
  self.assertEqual(score(r,[row(),row(band='2400',time='15:00')],v).total,2)
  v=ctx(r,'2Y430');self.assertEqual(score(r,[row(),row(band='1200')],v).total,2)
  v['age']=19;self.assertIsNone(score(r,[row()],v).total);v.pop('age');self.assertIsNone(score(r,[row()],v).total)
 def test_young_fallback_and_comment_output_ui(self):
  r=urule();v=ctx(r,'2Y430');d=EventDialog(r['event'],v);self.assertIn('運用可能バンド',d.summary.text());d.use_fallback();self.assertEqual(d.category.currentData(),'2X430');d.apply();self.assertEqual(d.context['category'],'2X430');d.deleteLater()
  p,before,sel,draft,info=self.fixture(r,[row()],v);tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);fmt=QComboBox();fmt.addItem('JARL R1.0');w=SimpleNamespace(repo=Repository(tmp.name),format=fmt,selection=sel,draft=draft,loaded_scope=('JH1HST',),rule=r,result=score(r,[row()],v),event_context=lambda:v,activity_name='コンテスト');pane=SubmissionPane(w);pane.set_context();self.assertNotIn('R2.1を選択',pane.overview.text());self.assertIn('18歳',pane.overview.text());pane.deleteLater();fmt.deleteLater()
 def test_uhf_all_permitted_modes_no_digital_inference_or_extra_dupes(self):
  r=urule();v=ctx(r,'2XA');rows=[row(mode=m,call='JA1AA'+chr(65+i)) for i,m in enumerate(['CW','FM','SSB','RTTY','FT8','FT4','DV','C4FM','FUTUREMODE'])];s=score(r,rows,v);self.assertEqual(s.total,18,s.problems)
  rows=[row(mode=m) for m in ['CW','SSB','FT8','FUTUREMODE']];self.assertEqual([x['points'] for x in score(r,rows,v).rows],[2,0,0,0])
  # A different event with a fixed mode list still excludes non-CW modes.
  cw=rule('tokyo_cw');self.assertEqual(score(cw,[row(date='2026-10-25',time='06:00',mode='FT8')],context(cw,'1CA')).points,0)
 def test_youth_age_source_and_legacy_r21_unchanged(self):
  for r,q,code in [(urule(),row(),'2YA'),(srule(),srow(mode='SSB'),'2YA')]:
   v=ctx(r,code);p,before,sel,draft,info=self.fixture(r,[q],v,comments='試験')
   for i in range(2):self.assertEqual(plan(sel,r,draft,'JARL R1.0',info,context=v).preview().count('運用者年齢: 18歳'),1)
   self.assertEqual(info['comments'],'試験');self.assertEqual(p.read_bytes(),before)
  a=rule('all_ja_cg');v=context(a,'CS');p,before,sel,draft,info=self.fixture(a,[row(date='2026-10-10',time='21:00',band='7',sent='1319M',exchange='100116L')],v)
  with self.assertRaisesRegex(ValueError,'R2.1'):plan(sel,a,draft,'JARL R1.0',info,context=v)
 def test_awards_only_current_event_and_young_operation_restriction(self):
  r=urule();rows=[row(exchange=c,call='JA1AA'+chr(65+i)) for i,c in enumerate(['201','202','203','204','431'])];v=ctx(r,'2X430');self.assertTrue(candidates(r,rows,v)[2]['eligible'])
  self.assertFalse(candidates(srule(),rows,ctx(srule(),'2X21'))[2]['eligible'])
  rows[0]['band']='2400';self.assertFalse(candidates(r,rows,ctx(r,'2YA'))[2]['eligible'])
 def test_spring_year_boundaries_and_phone_requirement(self):
  r=srule();v=ctx(r,'2XA');self.assertIsNone(score(r,[srow()],v).total);self.assertEqual(score(r,[srow(mode='SSB')],v).total,2)
  rows=[srow(mode='SSB'),srow(mode='SSB',band='430'),srow(mode='SSB',time='15:00'),srow(mode='SSB',date='2027-05-03')];s=score(r,rows,v);self.assertEqual([x['points'] for x in s.rows],[2,0,0,0])
  self.assertNotIn('tokyo-contest@',r['event']['submission']['instructions']);db=json.loads((ROOT/'config/db/contest/tokyo_2026.json').read_text(encoding='utf-8'));self.assertEqual((db['year'],db['version']),(2026,'20240331'));self.assertIn('01',r['event']['exchange']['codes']);self.assertNotIn('48',r['event']['exchange']['codes'])
 def test_contest_code_directions_and_participant_distinct_from_opponent(self):
  cw=rule('tokyo_cw');self.assertEqual(score(cw,[row(date='2026-10-25',time='06:00')],context(cw,'1CA')).total,2)
  for r,q,code in [(urule(),row(),'2XA'),(srule(),srow(),'2CA')]:
   v=ctx(r,code);self.assertEqual(score(r,[dict(q,call='JA1RL')],v).total,2)
   self.assertIsNone(score(r,[dict(q,sent='002')],v).total);v['station_type']='club';self.assertIsNone(score(r,[q],v).total);v['submission_mode']='checklog';self.assertIsNone(score(r,[q],v).total)
 def test_schema_rejects_invalid_choice_and_age_output(self):
  for mutate in [lambda r:r['event'].update(band_choices={'10G':['10100']}),lambda r:r['event'].update(band_choices={'10G':['10100','7']}),lambda r:r['points'].update(cw=2),lambda r:r['event']['categories'][0].update(modes=['*','CW']),lambda r:next(c for c in r['event']['categories'] if 'Y' in c['id'])['qualification'].update(age_output='nowhere')]:
   spec=urule();mutate(spec)
   with self.assertRaises(ValueError):loads(dumps(spec))
 def test_combined_pack_keeps_cw_and_reimport_does_not_duplicate(self):
  import rule_pack
  with tempfile.TemporaryDirectory() as tmp:
   store=RuleStore(Path(tmp));base=ROOT/'distribution/rules';rule_pack.install(store,rule_pack.preview(store,base/'tokyo_cw_2026_r1.zip'));cw=next(p for p in store.files() if store.read(p)[0]['id']=='tokyo_cw');before=cw.read_bytes()
   pack=base/'tokyo_uhf_spring_2026_r1.zip';self.assertEqual(rule_pack.install(store,rule_pack.preview(store,pack)),2);self.assertEqual(cw.read_bytes(),before)
   self.assertEqual({store.read(p)[0]['id'] for p in store.files()},{'tokyo','tokyo_cw','tokyo_uhf'})
   for filename in ['tokyo_uhf_2026_r1.zip','tokyo_2026_r1.zip','tokyo_uhf_spring_2026_r1.zip']:self.assertEqual(rule_pack.install(store,rule_pack.preview(store,base/filename)),0)
   self.assertEqual(len(store.files()),3)
 def test_unknown_licensed_mode_r10_roundtrip_preserves_raw_log(self):
  r=urule();v=ctx(r,'2XA');p,before,sel,draft,info=self.fixture(r,[row(mode='NEXTMODE')],v);out=plan(sel,r,draft,'JARL R1.0',info,context=v).preview();self.assertIn(' NEXTMODE ',out);self.assertIn('<TOTALSCORE>2</TOTALSCORE>',out);self.assertEqual(p.read_bytes(),before)

if __name__=='__main__':unittest.main()
