from copy import deepcopy
from pathlib import Path
import tempfile,unittest
from PySide6.QtWidgets import QApplication
from contest_rules import loads,dumps,score
from contest_export import plan,key
from contest import select_logs
from contest_timing import HISTORY_FLAG
from contest_qualification import operator_text
from contest_event_ui import EventDialog
from storage import Repository
from model import QSO
ROOT=Path(__file__).parent

def rule(ident):return loads((ROOT/f'config/rules/{ident}_2026.txt').read_text(encoding='utf-8'))
def context(r,code,power=None):
 c=next(c for c in r['event']['categories'] if c['id']==code)
 if power is None:power=200 if c.get('min_power_exclusive')==100 else c['max_power'] or 50
 ctx=dict(category=code,power=power,flags={f:True for f in r['event']['required_flags']+c['required_flags']+[HISTORY_FLAG]})
 if c.get('power_by_band'):ctx['power_by_band']=deepcopy(c['power_by_band'])
 q=c.get('qualification',{})
 if 'license_since' in q:ctx['licensedate']=q['license_since']
 if 'min_age' in q:ctx['age']=q['min_age']
 if 'operators_max_age' in q:ctx['operators']=[dict(name='JH1HST',age=q['operators_max_age'])]
 if r['event'].get('entrant',{}).get('station_types'):ctx['station_type']='individual'
 return ctx

def row(**kw):return dict(dict(date='2026-10-10',time='21:00',band='7',mode='CW',call='JA1AAA',sent='1319M',exchange='100116L'),**kw)

class ExportFixture(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
 def fixture(self,r,rows,ctx,**overrides):
  tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);repo=Repository(tmp.name);own=overrides.pop('own','JH1HST');p=repo.path_for(own,'',rows[0]['date'])
  for v in rows:
   rst='595' if v['mode']=='SSTV' else '599' if v['mode'] in ('CW','RTTY') else '59';repo.open(p).append(QSO(v['date'],v['time'],v['band'],v['mode'],v['call'],rst,rst,'Japan','Soka Japan','',''))
  before=p.read_bytes();sel=select_logs(repo,[p],own);draft={key(rec):dict(sent=v['sent'],received=v['exchange'],tx=v.get('tx',''),checklog=v.get('checklog',False),status='確認済み') for rec,v in zip(sel.rows,rows)}
  c=next(c for c in r['event']['categories'] if c['id']==ctx['category'])
  info=dict(contest=r['event']['submission']['contest'],category=c['id'],name='試験',address='試験',power=str(ctx['power']),date='2026-10-26',signature='試験',oath=True,email='test@example.com',multiop=c['operator']=='MO',multioplist=operator_text(ctx['operators']) if 'operators' in ctx else 'JH1HST' if c['operator']=='MO' else '',age=str(ctx.get('age','')),licensedate=ctx.get('licensedate',''))
  info.update(overrides);return p,before,sel,draft,info

class ACAGTests(ExportFixture):
 def test_all_80_categories_score_and_jarl_output(self):
  r=rule('all_ja_cg');expected={'PA','PN','PMA','XMJ'}|{'P'+b for b in ['19','35','7','21','28','50']}
  for p in 'CX':
   expected|={p+b+power for b in ['A','19','35','7','14','21','28','50'] for power in 'HMP'}|{p+b for b in ['144','430','1200','2400','5600','10G','S']}|{p+b+power for b in ['MA','M2'] for power in 'HM'}
  self.assertEqual({c['id'] for c in r['event']['categories']},expected);self.assertEqual(len(expected),80)
  for c in r['event']['categories']:
   with self.subTest(category=c['id']):
    ctx=context(r,c['id']);b=c['bands'][0];power=ctx.get('power_by_band',{}).get(b,ctx['power']);threshold=20 if b in ('50','144','430') else 10;letter='P' if power<=5 else 'L' if power<=threshold else 'M' if power<=100 else 'H'
    v=row(band=b,mode='SSB' if c.get('required_mode_families') else c['modes'][0],sent='1319'+letter,tx='1');s=score(r,[v],ctx);self.assertEqual(s.total,1,s.problems)
    p,before,sel,draft,info=self.fixture(r,[v],ctx)
    for f in ['JARL R2.1'] if c['id'] in ('PN','CS','XS') else ['JARL R1.0','JARL R2.1']:
     out=plan(sel,r,draft,f,info,context=ctx).preview();self.assertIn('<TOTALSCORE>1</TOTALSCORE>',out);self.assertNotIn('FDCOEFF',out)
     line=next(x for x in out.splitlines() if x.startswith('2026-10-10 '));self.assertEqual(len(line.split()),12 if c.get('timing') else 11)
    self.assertEqual(p.read_bytes(),before)
 def test_full_municipal_multiplier_and_thresholds(self):
  r=rule('all_ja_cg');ctx=context(r,'CAM',15)
  s=score(r,[row(band='144',sent='1319L'),row(band='1200',sent='1319M'),row(band='2400',sent='1319M',call='JA1BBB',exchange='100116M'),row(band='2400',sent='1319M',call='JA1CCC',exchange='100117L')],ctx)
  self.assertEqual((s.points,s.multi1,s.total),(4,4,16));self.assertEqual(s.rows[0]['multiplier_values'],['100116'])
  self.assertIsNone(score(r,[row(band='144',sent='1319M')],ctx).total)
  self.assertEqual(score(r,[row(band='1200',sent='1319M')],ctx).total,1)
  self.assertIsNone(score(r,[row(exchange='1001M')],ctx).total)
  self.assertIsNone(score(r,[row(sent='1319M'),row(band='144',sent='1320L')],ctx).total)
 def test_qualifications_and_two_wave_boundaries(self):
  r=rule('all_ja_cg');ctx=context(r,'PN');ctx['licensedate']='2023-10-09';self.assertIsNone(score(r,[row(mode='SSB',sent='1319L')],ctx).total)
  ctx['licensedate']='2023-10-10';self.assertEqual(score(r,[row(mode='SSB',sent='1319L')],ctx).total,1)
  self.assertEqual({c['id'] for c in r['event']['categories'] if c.get('timing')},{'CM2H','CM2M','XM2H','XM2M'})
  rows=[row(tx='1'),row(band='14',time='21:01',tx='2'),row(band='21',time='21:09',tx='1'),row(band='21',time='21:10',tx='1')]
  s=score(r,rows,context(r,'CM2M'));self.assertEqual([v['points'] for v in s.rows],[1,1,0,1]);self.assertEqual(s.total,9)
  self.assertEqual(score(r,rows,context(r,'CMAM')).total,9)
 def test_same_station_different_mode_and_high_bands(self):
  r=rule('all_ja_cg');rows=[row(band='10100'),row(band='10.4G'),row(band='10100',mode='SSB')]
  s=score(r,rows,context(r,'X10G'));self.assertEqual([x['points'] for x in s.rows],[1,1,0]);self.assertEqual(s.total,4)
  self.assertIsNone(score(r,[row()],context(r,'XAM')).total)
  self.assertEqual(score(r,[row()],context(r,'XMJ')).total,1)
 def test_schema_and_ui(self):
  r=rule('all_ja_cg');d=EventDialog(r['event'],context(r,'CM2M'));self.assertEqual(d.category.count(),80);self.assertIn('10分',d.time_summary.text());d.deleteLater()
  r['event']['exchange']['same_sent_region_across_profiles']='yes'
  with self.assertRaises(ValueError):loads(dumps(r))

def xrow(**kw):return row(**dict(dict(date='2026-09-21',time='06:00',sent='13',exchange='10'),**kw))

class XPOTests(ExportFixture):
 def test_28_categories_and_every_jarl_output(self):
  r=rule('xpo');self.assertEqual({c['id'] for c in r['event']['categories']},{p+s for p in 'CF' for s in ['A','H','19','35','7','14','21','28','50','144','430','1200','2400','C']})
  for c in r['event']['categories']:
   with self.subTest(category=c['id']):
    ctx=context(r,c['id']);bands=['144','430'] if c['id'].endswith('A') else c['bands'][:c['min_bands']];rows=[xrow(band=b,mode='SSB' if c['id'].startswith('F') else 'CW') for b in bands];s=score(r,rows,ctx);self.assertEqual(s.total,len(rows)**2,s.problems)
    p,before,sel,draft,info=self.fixture(r,rows,ctx)
    for f in ('JARL R1.0','JARL R2.1'):
     out=plan(sel,r,draft,f,info,context=ctx).preview();self.assertIn(f'<TOTALSCORE>{len(rows)**2}</TOTALSCORE>',out)
    self.assertEqual(p.read_bytes(),before)
 def test_category_band_combinations(self):
  r=rule('xpo')
  for code,bands,ok in [('CA',['7','14'],False),('CH',['7','14'],True),('CA',['144','430'],True),('CA',['2400','5600'],False),('C2400',['5600'],True),('CC',['7'],True),('CA',['7'],False),('CH',['7'],False),('FA',['144','430'],False)]:
   with self.subTest(code=code,bands=bands):self.assertEqual(score(r,[xrow(band=b) for b in bands],context(r,code)).total is not None,ok)
  self.assertEqual(score(r,[xrow(band='144',mode='FM'),xrow(band='430',mode='SSB')],context(r,'FA')).total,4)
 def test_10ghz_normalization_dedup_and_region_48(self):
  r=rule('xpo');rows=[xrow(band='10.1G',exchange='48'),xrow(band='10400',exchange='48'),xrow(band='10.4GHz',exchange='48',call='JA1BBB')]
  s=score(r,rows,context(r,'C2400'));self.assertEqual([v['points'] for v in s.rows],[1,0,1]);self.assertEqual((s.multi1,s.total),(1,2))
  p,before,sel,draft,info=self.fixture(r,rows,context(r,'C2400'));out=plan(sel,r,draft,'JARL R1.0',info,context=context(r,'C2400')).preview();self.assertEqual(out.count(' 10G CW '),3);self.assertIn('<SCORE BAND=10G>3,2,1</SCORE>',out);self.assertEqual(p.read_bytes(),before)
 def test_exclusions_do_not_reserve_dupes_and_commemorative_is_one(self):
  r=rule('xpo');rows=[xrow(time='05:59'),xrow(call='8J1AAA'),xrow(call='8J1AAA',mode='SSB'),xrow(mode='RTTY'),xrow(time='18:00'),xrow(band='3.5')]
  s=score(r,rows,context(r,'C7'));self.assertEqual([v['points'] for v in s.rows],[0,1,0,0,0,0]);self.assertEqual(s.total,1)
  ctx=context(r,'C7');p,before,sel,draft,info=self.fixture(r,rows,ctx);out=plan(sel,r,draft,'JARL R1.0',info,context=ctx).preview();self.assertEqual(sum(x.startswith('2026-09-21 ') for x in out.splitlines()),6);self.assertNotIn('\nX ',out);self.assertEqual(p.read_bytes(),before)
 def test_numeric_exchange_validation_and_guest_mo(self):
  r=rule('xpo');ctx=context(r,'C7')
  for value in ('10M','1','010','999',''):
   self.assertIsNone(score(r,[xrow(exchange=value)],ctx).total)
  self.assertIsNone(score(r,[xrow(),xrow(sent='14',call='JA1BBB')],ctx).total)
  for code,ok in [('C7',False),('CC',True)]:
   v=context(r,code);p,before,sel,draft,info=self.fixture(r,[xrow()],v,guest=True,opcall='JA1BBB')
   if ok:plan(sel,r,draft,'JARL R1.0',info,context=v)
   else:
    with self.assertRaisesRegex(ValueError,'マルチオペ'):plan(sel,r,draft,'JARL R1.0',info,context=v)
 def test_schema_and_ui(self):
  r=rule('xpo');d=EventDialog(r['event'],context(r,'CA'));self.assertIn('全帯種目の除外構成',d.summary.text());self.assertEqual(d.category.count(),28);d.deleteLater()
  for group in ([],[['18']],['7']):
   bad=deepcopy(r);bad['event']['categories'][0]['excluded_band_subsets']=group
   with self.assertRaises(ValueError):loads(dumps(bad))
  r['event']['exchange']['codes'].append(r['event']['exchange']['codes'][0])
  with self.assertRaises(ValueError):loads(dumps(r))

def trow(**kw):return row(**dict(dict(date='2026-10-25',time='06:00',sent='13',exchange='101'),**kw))
def tcalls(codes):return [trow(call='JA1A'+chr(65+i//26)+chr(65+i%26),exchange=c) for i,c in enumerate(codes)]

class TokyoCWTests(ExportFixture):
 def test_18_categories_and_every_r10_output(self):
  r=rule('tokyo_cw');self.assertEqual({c['id'] for c in r['event']['categories']},{p+'C'+b for p in '12' for b in ['A','35','7','14','21','28','50','144','430']})
  for c in r['event']['categories']:
   with self.subTest(category=c['id']):
    ctx=context(r,c['id']);v=trow(band=c['bands'][0],sent='002' if c['id'].startswith('2') else '13');s=score(r,[v],ctx);self.assertEqual(s.total,2,s.problems)
    p,before,sel,draft,info=self.fixture(r,[v],ctx);out=plan(sel,r,draft,'JARL R1.0',info,context=ctx).preview();self.assertIn('<TOTALSCORE>2</TOTALSCORE>',out);self.assertIn(' 101 101 2',out);self.assertNotIn('申請します',out)
    with self.assertRaises(ValueError):plan(sel,r,draft,'JARL R2.1',info,context=ctx)
    self.assertEqual(p.read_bytes(),before)
 def test_108_codes_and_points_without_jcc_guess(self):
  import json
  r=rule('tokyo_cw');db=json.loads((ROOT/'config/db/contest/tokyo_cw_2026.json').read_text(encoding='utf-8'));groups=db['groups'];self.assertEqual([len(groups[k]) for k in ['city','ward','town','island','outside']],[26,23,4,9,46])
  self.assertEqual(groups['ward']['101'],'千代田区');self.assertEqual(groups['island']['431'],'小笠原村');self.assertEqual(groups['outside']['01'],'北海道')
  codes=r['event']['exchange']['codes'];s=score(r,tcalls(codes),context(r,'1CA'));self.assertEqual((s.points,s.multi1,s.total),(170,108,18360))
  self.assertEqual(score(r,[trow(exchange='11'),trow(exchange='16',call='JA1BBB')],context(r,'1CA')).total,4)
  for value in ('10','48','017','018','027','100101','1001','2','101M','1140'):
   with self.subTest(value=value):self.assertIsNone(score(r,[trow(exchange=value)],context(r,'1CA')).total)
 def test_self_location_and_entrant_differ_from_opponent(self):
  r=rule('tokyo_cw');ctx=context(r,'1CA')
  self.assertIsNone(score(r,[trow(sent='002')],ctx).total)
  self.assertIsNone(score(r,[trow(sent='13')],context(r,'2CA')).total)
  self.assertEqual(score(r,[trow(call='JA1RL'),trow(call='8J1AAA')],ctx).total,4)
  for kind in ('club','special',''):
   v=dict(ctx,station_type=kind);self.assertIsNone(score(r,[trow()],v).total)
   v['submission_mode']='checklog';self.assertIsNone(score(r,[trow()],v).total)
  p,before,sel,draft,info=self.fixture(r,[trow()],ctx,guest=True,opcall='JA1BBB')
  with self.assertRaisesRegex(ValueError,'ゲスト'):plan(sel,r,draft,'JARL R1.0',info,context=ctx)
  info['guest']=False
  with self.assertRaisesRegex(ValueError,'ゲスト'):plan(sel,r,draft,'JARL R1.0',info,context=ctx)
 def test_bounds_duplicate_and_actual_band_multis(self):
  r=rule('tokyo_cw');rows=[trow(time='05:59'),trow(),trow(),trow(band='144'),trow(band='1200'),trow(time='12:00'),trow(mode='SSB')]
  s=score(r,rows,context(r,'1CA'));self.assertEqual([v['points'] for v in s.rows],[0,2,0,2,0,0,0]);self.assertEqual(s.total,8)
 def test_awards_band_independent_and_missing_codes(self):
  from contest_awards import candidates
  r=rule('tokyo_cw');ctx=context(r,'1C7');spec=r['event']['awards'];city=spec[0]['groups'][0]['codes'];rows=tcalls(city)
  for i,v in enumerate(rows):v['band']='7' if i%2 else '144'
  self.assertTrue(candidates(r,rows,ctx)[0]['eligible']);self.assertFalse(candidates(r,rows[:-1],ctx)[0]['eligible'])
  rows[-1]['checklog']=True;self.assertFalse(candidates(r,rows,ctx)[0]['eligible'])
  ward=spec[1]['groups'][0]['codes'];self.assertTrue(candidates(r,tcalls(ward),ctx)[1]['eligible'])
  towns=spec[2]['groups'][0]['codes'];self.assertFalse(candidates(r,tcalls(towns),ctx)[2]['eligible'])
  rows=tcalls(towns+['431']);self.assertTrue(candidates(r,rows,ctx)[2]['eligible'])
  rows[-1]['time']='12:00';self.assertFalse(candidates(r,rows,ctx)[2]['eligible'])
 def test_award_optional_output_and_stale_request_block(self):
  from contest_awards import submission_info
  r=rule('tokyo_cw');ctx=context(r,'1C7');rows=tcalls(['201','202','203','204','431']);rows[0]['band']='144';p,before,sel,draft,info=self.fixture(r,rows,ctx,comments='元の意見',award_requests=['towns_island'])
  original=deepcopy(info);out=plan(sel,r,draft,'JARL R1.0',info,context=ctx).preview();self.assertIn('<COMMENTS>元の意見 全郡・島賞を申請します。</COMMENTS>',out);self.assertEqual(info,original);self.assertEqual(p.read_bytes(),before)
  self.assertIn('<TOTALSCORE>32</TOTALSCORE>',out)  # 7MHz only; 144MHz counts for the award, not score.
  draft[key(sel.rows[-1])]['received']='401';self.assertIn('全郡・島賞を申請',plan(sel,r,draft,'JARL R1.0',info,context=ctx).preview())
  draft[key(sel.rows[-1])]['received']='13'
  with self.assertRaisesRegex(ValueError,'達成条件'):plan(sel,r,draft,'JARL R1.0',info,context=ctx)
  for bad in (['unknown'],['towns_island','towns_island'],'towns_island',[[]]):
   with self.assertRaises(ValueError):submission_info(r,rows,ctx,dict(award_requests=bad))
 def test_award_panel_and_schema(self):
  from contest_award_ui import AwardPane
  r=rule('tokyo_cw');ctx=context(r,'1CA');rows=tcalls(['201','202','203','204','431']);p,before,sel,draft,info=self.fixture(r,rows,ctx);changed=[]
  pane=AwardPane(lambda:changed.append(True));pane.refresh(r,sel,draft,ctx,'scope');self.assertEqual(pane.requests(),[]);self.assertTrue(pane.checks['towns_island'].isEnabled());self.assertFalse(pane.checks['all_cities'].isEnabled());pane.checks['towns_island'].setChecked(True);self.assertEqual(pane.requests(),['towns_island']);self.assertTrue(changed)
  pane.refresh(r,sel,draft,ctx,'scope');self.assertEqual(pane.requests(),['towns_island']);pane.refresh(r,sel,draft,ctx,'new-scope');self.assertEqual(pane.requests(),[]);self.assertLessEqual(pane.maximumHeight(),180);pane.deleteLater()
  d=EventDialog(r['event'],ctx);self.assertEqual(d.station_type.currentData(),'individual');self.assertEqual(d.category.count(),18);self.assertIn('ゲスト',d.summary.text());d.deleteLater()
  for mutate in [lambda r:r['event']['awards'][0]['groups'][0].update(min_count=27),lambda r:r['event']['awards'][0]['groups'][0]['codes'].append('017'),lambda r:r['event']['entrant'].update(station_types=[{}]),lambda r:r['event']['categories'][0].update(sent_codes=['10'])]:
   bad=deepcopy(r);mutate(bad)
   with self.assertRaises(ValueError):loads(dumps(bad))
 def test_submission_pane_connects_choice_to_output(self):
  from types import SimpleNamespace
  from PySide6.QtWidgets import QComboBox
  from contest_submit_ui import SubmissionPane
  r=rule('tokyo_cw');ctx=context(r,'1C7');rows=tcalls(['201','202','203','204','431']);p,before,sel,draft,info=self.fixture(r,rows,ctx)
  tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);fmt=QComboBox();fmt.addItem('JARL R1.0')
  wizard=SimpleNamespace(repo=Repository(tmp.name),format=fmt,selection=sel,draft=draft,loaded_scope=('JH1HST',),rule=r,result=score(r,rows,ctx),event_context=lambda:ctx,activity_name='コンテスト')
  pane=SubmissionPane(wizard);pane.set_context()
  for k,v in info.items():
   if k not in pane.fields:continue
   w=pane.fields[k]
   if isinstance(v,bool):w.setChecked(v)
   else:w.setText(v)
  pane.awards.checks['towns_island'].setChecked(True);self.assertEqual(pane.info()['award_requests'],['towns_island'])
  self.assertIn('全郡・島賞を申請します。',plan(sel,r,draft,'JARL R1.0',pane.info(),context=ctx).preview())
  pane.resize(1100,680);pane.show();self.app.processEvents();self.assertTrue(pane.awards.isVisible());self.assertLessEqual(pane.awards.height(),180)
  self.assertEqual(p.read_bytes(),before);pane.close();pane.deleteLater();fmt.deleteLater()

class BatchPackTests(unittest.TestCase):
 def test_three_rules_install_and_reimport_without_duplicate(self):
  from contest_rules import RuleStore
  import rule_pack
  with tempfile.TemporaryDirectory() as tmp:
   store=RuleStore(Path(tmp));base=ROOT/'distribution/rules';pack=base/'batch10_acag_xpo_tokyo_cw_2026_r1.zip'
   self.assertEqual(rule_pack.install(store,rule_pack.preview(store,pack)),3)
   loaded={store.read(p)[0]['id']:store.read(p)[0] for p in store.files()};self.assertEqual({k:len(v['event']['categories']) for k,v in loaded.items()},{'all_ja_cg':80,'xpo':28,'tokyo_cw':18})
   for name in ('acag_2026_r1.zip','xpo_2026_r1.zip','tokyo_cw_2026_r1.zip','batch10_acag_xpo_tokyo_cw_2026_r1.zip'):
    proposal=rule_pack.preview(store,base/name);self.assertTrue(all(i.status=='変更なし' for i in proposal.items));self.assertEqual(rule_pack.install(store,proposal),0)
   self.assertEqual(len(store.files()),3)
   # Tokyo scoring is self-contained: installation does not require a side DB.
   self.assertEqual(score(loaded['tokyo_cw'],[trow()],context(loaded['tokyo_cw'],'1CA')).total,2)

if __name__=='__main__':unittest.main()
