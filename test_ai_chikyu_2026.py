from copy import deepcopy
from pathlib import Path
import unittest,tempfile,re,html
from PySide6.QtWidgets import QComboBox
from test_contest_batch10 import ExportFixture,rule,context
from contest_rules import score,loads,dumps,RuleStore
from contest_export import plan,key
from contest_event_ui import EventDialog
from contest_participation import HISTORY,parse,check,operator_text
ROOT=Path(__file__).parent
def r():return rule('ai_chikyu')
def row(**kw):return dict(dict(date='2026-09-22',time='21:00',band='144',mode='CW',call='JA1AAA',sent='13',exchange='10'),**kw)
def operator(name='JH1HST',age=20,qsos=1,role=''):return dict(name=name,age=age,qsos=qsos,role=role)
def ctx(code='XA',power=None,ops=None):
 v=context(r(),code,power);v['flags'].update({f:True for f in r()['event']['mode_confirmations'].values()});v['flags'][HISTORY]=True
 if code in ('XJ','XMJ','PMMK'):
  v['qso_operators']=ops if ops is not None else [operator()]
  if code=='PMMK' and ops is None:v['qso_operators']=[operator(role='子'),operator('JA1BBB',50,0,'父')]
  v['child_call']='JH1HST'
 return v

class AiTests(ExportFixture):
 def test_all_33_codes_source_and_r10_output(self):
  spec=r();codes={c['id'] for c in spec['event']['categories']};source=(ROOT/'docs/contest-research/sources/ai_chikyuhaku_2026.html').read_bytes().decode('cp932');tokens=set(re.findall(r'\b[CPX][A-Z0-9]{1,6}\b',html.unescape(re.sub('<[^>]*>',' ',source))))
  self.assertEqual(len(codes),33);self.assertFalse(codes-tokens)
  self.assertEqual(codes,{'CA','CHL','CHH','CHF','CVU','CMA','XA','X19','X35','X7','X14','X21','X28','X50','X144','X430','XG','XHL','XHH','XHF','XVU','XQRP','XJ','XMA','XMJ','PA','PHL','PHH','PHF','PVU','PD','PMA','PMMK'})
  for c in spec['event']['categories']:
   with self.subTest(code=c['id']):
    v=ctx(c['id']);q=row(band=c['bands'][0],mode=c['modes'][0]);s=score(spec,[q],v);self.assertEqual(s.total,1,s.problems)
    p,before,sel,draft,info=self.fixture(spec,[q],v,opplace='Soka Saitama Japan')
    if c.get('participation') and c['operator']=='MO':info['multioplist']=operator_text(v)
    out=plan(sel,spec,draft,'JARL R1.0',info,context=v).preview();self.assertIn('<TOTALSCORE>1</TOTALSCORE>',out)
    if c.get('participation'):self.assertIn('20歳 1交信',out)
    if c['id']=='PMMK':self.assertIn('父',out);self.assertIn('子のコールサイン JH1HST',out)
    self.assertEqual(p.read_bytes(),before)
 def test_three_groups_common_multis_and_submodes(self):
  rows=[row(mode=m) for m in ['CW','SSB','FM','D-STAR','DSTAR','DV']];s=score(r(),rows,ctx());self.assertEqual([q['points'] for q in s.rows],[1,1,0,1,0,0]);self.assertEqual((s.multi1,s.total),(1,3))
  rows.append(row(band='430',mode='DV'));self.assertEqual(score(r(),rows,ctx()).total,8)
  self.assertEqual(score(r(),[row(mode='CW')],ctx('XA')).total,1)
  self.assertEqual(score(r(),[row(mode='SSB')],ctx('XA')).total,1)
  self.assertEqual(score(r(),[row(mode='FM'),row(mode='DV')],ctx('PD')).total,1)
 def test_dv_confirmation_required_and_other_digital_excluded(self):
  v=ctx();v['flags'].pop(next(iter(r()['event']['mode_confirmations'].values())))
  self.assertIsNone(score(r(),[row(mode='DV')],v).total);self.assertEqual(score(r(),[row()],v).total,1)
  rows=[row(mode='CW'),row(mode='FT8'),row(mode='RTTY'),row(mode='FreeDV')];s=score(r(),rows,ctx());self.assertEqual([x['points'] for x in s.rows],[1,0,0,0])
 def test_pause_and_end_boundary(self):
  rows=[row(time='20:59'),row(),row(date='2026-09-23',time='00:00',call='JA1BBB'),row(date='2026-09-23',time='05:59',call='JA1CCC'),row(date='2026-09-23',time='06:00',call='JA1BBB'),row(date='2026-09-23',time='11:59',call='JA1CCC'),row(date='2026-09-23',time='12:00',call='JA1DDD')]
  s=score(r(),rows,ctx());self.assertEqual([x['points'] for x in s.rows],[0,1,0,0,1,1,0]);self.assertEqual(s.total,3)
 def test_phone_limits_do_not_spread_to_mixed(self):
  v=ctx('PA',20);rows=[row(band='7',mode='SSB'),row(band='1200',mode='FM')];self.assertEqual(score(r(),rows,v).total,4)
  v['power_by_band']['7']=11;self.assertIsNone(score(r(),rows,v).total)
  v=ctx('PA',21);self.assertIsNone(score(r(),[row(mode='FM')],v).total)
  self.assertEqual(score(r(),[row(band='7',mode='SSB')],ctx('XA',100)).total,1)
  self.assertEqual(score(r(),[row()],ctx('XQRP',5)).total,1);self.assertIsNone(score(r(),[row()],ctx('XQRP',5.001)).total)
 def test_youth_exact_80_and_20_age(self):
  rows=[row(call='JA1A'+chr(65+i//26)+chr(65+i%26)) for i in range(100)]
  v=ctx('XMJ',ops=[operator(qsos=80),operator('JA1BBB',50,20)])
  self.assertEqual(score(r(),rows,v).total,100)
  v['qso_operators'][0]['qsos']=79;v['qso_operators'][1]['qsos']=21;self.assertIsNone(score(r(),rows,v).total)
  v['qso_operators'][0]['qsos']=80;v['qso_operators'][1]['qsos']=20;v['qso_operators'][0]['age']=21;self.assertIsNone(score(r(),rows,v).total)
  # Nine young operators do not qualify if the adult operates most contacts.
  v=ctx('XMJ',ops=[operator('JA1'+chr(65+i)+'AA',20,1) for i in range(9)]+[operator('JA1ZZZ',50,91)])
  self.assertIsNone(score(r(),rows,v).total)
 def test_counts_cover_duplicate_zero_rows_and_full_history(self):
  rows=[row(),row(),row(mode='SSB',checklog=True),row(mode='RTTY'),row(call='JA1BBB')]
  v=ctx('XMJ',ops=[operator(qsos=4),operator('JA1BBB',50,1)]);s=score(r(),rows,v);self.assertEqual(s.total,2,s.problems)
  v['qso_operators'][0]['qsos']=1;self.assertIsNone(score(r(),rows,v).total)
  v['qso_operators'][0]['qsos']=4;v['flags'][HISTORY]=False;self.assertIsNone(score(r(),rows,v).total)
  self.assertIsNone(score(r(),[row()],ctx('XJ',ops=[operator(),operator('JA1BBB',20,0)])).total)
 def test_pmmk_family_and_child_callsign(self):
  for relation in ('父','母','祖父','祖母'):
   v=ctx('PMMK',ops=[operator(role='子'),operator('JA1BBB',60,0,relation)]);self.assertEqual(score(r(),[row(mode='FM')],v).total,1)
  for ops in [[operator(role='子')],[operator(role='子'),operator('JA1BBB',50,0,'父'),operator('JA1CCC',50,0,'母')],[operator(age=21,role='子'),operator('JA1BBB',50,0,'父')],[operator(role='子'),operator('JA1BBB',50,0,'兄')]]:
   self.assertIsNone(score(r(),[row(mode='FM')],ctx('PMMK',ops=ops)).total)
  v=ctx('PMMK');p,before,sel,draft,info=self.fixture(r(),[row(mode='FM')],v,opplace='Soka Japan',multioplist=operator_text(v))
  v['child_call']='JA1XYZ'
  with self.assertRaisesRegex(ValueError,'子のコール'):plan(sel,r(),draft,'JARL R1.0',info,context=v)
 def test_comments_preserved_and_declarations_match(self):
  v=ctx('XMJ');p,before,sel,draft,info=self.fixture(r(),[row()],v,opplace='Soka Japan',multioplist=operator_text(v),comments='元の意見');original=deepcopy(info)
  out=plan(sel,r(),draft,'JARL R1.0',info,context=v).preview();self.assertIn('元の意見 担当交信: JH1HST 20歳 1交信',out);self.assertEqual(info,original);self.assertEqual(p.read_bytes(),before)
  info['multioplist']='JA1ZZZ'
  with self.assertRaisesRegex(ValueError,'運用者一覧'):plan(sel,r(),draft,'JARL R1.0',info,context=v)
 def test_band_sorted_output_preserves_score_alignment(self):
  rows=[row(band='430',time='21:00'),row(band='7',time='21:01'),row(band='430',time='21:02'),row(band='144',time='21:03'),row(band='7',time='21:04',call='JA1BBB')];v=ctx();p,before,sel,draft,info=self.fixture(r(),rows,v,opplace='Soka Japan')
  out=plan(sel,r(),draft,'JARL R1.0',info,context=v).preview();lines=[s.split() for s in out.splitlines() if s.startswith('2026-09-22 ')];self.assertEqual([x[2] for x in lines],['7','7','144','430','430']);self.assertEqual([int(x[-1]) for x in lines],[1,1,1,1,0]);self.assertIn('<TOTALSCORE>12</TOTALSCORE>',out)
  info['sort_band_time']=False;out=plan(sel,r(),draft,'JARL R1.0',info,context=v).preview();lines=[s.split() for s in out.splitlines() if s.startswith('2026-09-22 ')];self.assertEqual([x[2] for x in lines],['430','7','430','144','7'])
  info['sort_band_time']=True;out=plan(sel,r(),draft,'JARL R1.0',info,context=v).preview();lines=[s.split() for s in out.splitlines() if s.startswith('2026-09-22 ')];self.assertEqual([x[2] for x in lines],['7','7','144','430','430']);self.assertEqual(p.read_bytes(),before)
 def test_ui_counts_fallback_and_rechecks_power(self):
  d=EventDialog(r()['event'],ctx('PMMK'));self.assertEqual(d.category.count(),33);self.assertEqual(d.category.currentData(),'PMMK');self.assertIn('100.0',d.participation.summary.text());d.use_fallback();self.assertEqual(d.category.currentData(),'PMA');d.apply();self.assertEqual(d.context['category'],'PMA');d.deleteLater()
  self.assertIsNone(score(r(),[row(mode='FM')],ctx('PMA',21)).total)
  d=EventDialog(r()['event'],ctx('XMJ'));d.participation.ops.setPlainText('JH1HST / 20 / 4\nJA1BBB / 50 / 1');self.assertIn('80.0',d.participation.summary.text());d.apply();self.assertEqual(d.context['qso_operators'][0]['qsos'],4);d.deleteLater()
 def test_invalid_schema_and_counts(self):
  for change in [lambda s:s['event'].update(mode_groups={}),lambda s:s['event']['submission'].update(order='random'),lambda s:next(c for c in s['event']['categories'] if c['id']=='PMMK').update(fallback_category='missing'),lambda s:next(c for c in s['event']['categories'] if c['id']=='XJ')['participation'].update(min_percent=80.0)]:
   spec=r();change(spec)
   with self.assertRaises(ValueError):loads(dumps(spec))
  for value in ['JA1AAA / 20 / -1','JA1AAA / 20 / 1.5','JA1AAA / age / 1']:
   with self.assertRaises(ValueError):parse(value)
  for ops in [[operator(),operator()],[operator(qsos=True)],[operator(age=-1)]]:
   self.assertIsNone(score(r(),[row()],ctx('XMJ',ops=ops)).total)
 def test_submission_pane_age_family_and_no_comment_accumulation(self):
  from types import SimpleNamespace
  from storage import Repository
  from contest_submit_ui import SubmissionPane
  v=ctx('PMMK');rows=[row(mode='FM')];p,before,sel,draft,info=self.fixture(r(),rows,v,opplace='Soka Japan',multioplist=operator_text(v),comments='元の意見')
  tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);fmt=QComboBox();fmt.addItem('JARL R1.0');wizard=SimpleNamespace(repo=Repository(tmp.name),format=fmt,selection=sel,draft=draft,loaded_scope=('JH1HST',),rule=r(),result=score(r(),rows,v),event_context=lambda:v,activity_name='コンテスト')
  pane=SubmissionPane(wizard);pane.set_context();self.assertEqual(pane.fields['multioplist'].text(),'JH1HST JA1BBB');self.assertTrue(pane.fields['multioplist'].isReadOnly());self.assertTrue(pane.fields['sort_band_time'].isChecked());self.assertEqual(pane.fields['zone'].currentText(),'JST')
  for k,value in info.items():
   if k not in pane.fields:continue
   w=pane.fields[k]
   if isinstance(value,bool):w.setChecked(value)
   else:w.setText(value)
  for repeat in range(2):
   output=plan(sel,r(),draft,'JARL R1.0',pane.info(),context=v).preview();self.assertEqual(output.count('担当交信:'),1);self.assertIn('50歳 0交信 父',output)
  self.assertEqual(pane.fields['comments'].text(),'元の意見');self.assertEqual(p.read_bytes(),before);pane.deleteLater();fmt.deleteLater()
 def test_import_pack_is_self_contained_and_deduplicated(self):
  import rule_pack
  with tempfile.TemporaryDirectory() as tmp:
   store=RuleStore(Path(tmp));pack=ROOT/'distribution/rules/ai_chikyu_2026_r2.zip';self.assertEqual(rule_pack.install(store,rule_pack.preview(store,pack)),1)
   loaded=store.read(store.files()[0])[0];self.assertEqual(len(loaded['event']['categories']),33);self.assertEqual(score(loaded,[row(mode='DV')],ctx()).total,1)
   self.assertEqual(rule_pack.install(store,rule_pack.preview(store,pack)),0);self.assertEqual(len(store.files()),1)

if __name__=='__main__':unittest.main()
