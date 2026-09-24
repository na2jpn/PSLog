"""Small explicit code dictionaries are test fixtures, not a distributable 6D rule."""
from copy import deepcopy
from pathlib import Path
import tempfile,unittest
from contest_rules import score,loads,dumps,family
from test_all_ja_2tx import rule as allja,entry
from contest_export import plan,key
from contest import select_logs
from storage import Repository
from model import QSO

def fixture():
 r=allja();r['id']='test_6d_foundation';r['event'].pop('band_modes',None)
 e=r['event'];bands=['1200','2400','10100','10400','24000']
 e['windows']=[dict(start='2026-07-04 21:00',end='2026-07-05 15:00',bands=bands)]
 e['categories']=[dict(id='TEST',name='試験専用・大会定義ではありません',bands=bands,modes=['CW','SSB','FM','DV'],max_power=None,min_bands=1,max_bands=5,min_calls=1,required_flags=[],operator='SO')]
 e['required_flags']=[]
 e['normalization']=dict(bands={'1.2G':'1200','2.4G':'2400','10.1G':'10100','10.4G':'10400','24G':'24000'},modes={'D-STAR':'DV','DSTAR':'DV','USB':'SSB','LSB':'SSB'},mode_families={'DV':'phone'})
 e['exchange']=dict(kind='jarl_band_power',same_sent_region=True,profiles=[dict(id='prefecture',bands=['1200'],codes=['10','13','106'],code_lengths=[2,3],m_threshold=20,points=1),dict(id='municipality',bands=bands[1:],codes=['120101','1120','13003','010101'],code_lengths=[4,5,6],m_threshold=20,points=2)])
 e['submission']=dict(formats=['JARL R1.0','JARL R2.1'],zone='JST',contest='試験専用',instructions='試験専用')
 return r

def ctx(power=20):return dict(category='TEST',power=power,flags={})
def qso(**kw):return entry(**dict(dict(date='2026-07-04',band='1200',sent='13L',exchange='106L'),**kw))

class BandExchangeTests(unittest.TestCase):
 def test_low_high_scores_and_full_codes(self):
  r=fixture();rows=[qso(),qso(band='2400',sent='1120L',exchange='120101P'),qso(band='2400',call='JA1BBB',sent='1120L',exchange='120101M')];old=deepcopy(rows)
  s=score(r,rows,ctx());self.assertEqual(s.total,10);self.assertEqual(s.multi1,2);self.assertEqual([v['points'] for v in s.rows],[1,2,2]);self.assertEqual(rows,old)
 def test_invalid_codes_and_wrong_band_parser_stop_output(self):
  for band,number in [('1200','120101P'),('2400','10L'),('2400','999999P'),('2400','12010P'),('2400','120101'),('2400','120101MM')]:
   self.assertIsNone(score(fixture(),[qso(band=band,sent='1120L' if band=='2400' else '13L',exchange=number)],ctx()).total)
 def test_power_boundaries(self):
  for power,letter,ok in [(5,'P',True),(5,'L',False),(5.001,'L',True),(20,'L',True),(20,'M',False),(20.001,'M',True),(100,'H',False),(100.001,'H',True)]:
   self.assertEqual(score(fixture(),[qso(sent='13'+letter)],ctx(power)).total is not None,ok)
 def test_same_sent_region_compared_within_number_system(self):
  self.assertEqual(score(fixture(),[qso(),qso(band='2400',sent='1120L',exchange='120101P')],ctx()).total,6)
  self.assertIsNone(score(fixture(),[qso(),qso(call='JA1BBB',sent='10L')],ctx()).total)
  self.assertIsNone(score(fixture(),[qso(band='2400',sent='1120L',exchange='120101P'),qso(band='2400',call='JA1BBB',sent='13003L',exchange='120101P')],ctx()).total)
 def test_alias_duplicates_and_distinct_actual_high_bands(self):
  rows=[qso(band=b,sent='1120L',exchange='120101P') for b in ['2.4G','2400','10.1G','10.4G','24G']]
  s=score(fixture(),rows,ctx());self.assertEqual([v['points'] for v in s.rows],[2,0,2,2,2]);self.assertEqual(s.multi1,4);self.assertEqual(s.total,32)
  self.assertIsNone(score(fixture(),[qso(band='10G')],ctx()).total)
 def test_dstar_phone_scoring_requirement_and_isolation(self):
  r=fixture();r['event']['categories'][0]['required_mode_families']=['phone'];r['event']['exchange']['profiles'][0]['points']=3
  self.assertEqual(score(r,[qso(mode='D-STAR')],ctx()).total,3)
  r['event'].pop('exchange');r['points']['phone']=7;r['points']['digital']=2
  self.assertEqual(score(r,[qso(mode='DSTAR',area='106')],ctx()).total,7)
  self.assertEqual(family('DV'),'digital')
  for mode in ['C4FM','DMR','FT8','FREEDV','NOTDSTAR']:self.assertIsNone(score(r,[qso(mode=mode)],ctx()).total)
 def test_all_modes_duplicate_and_no_ten_minute_rule(self):
  s=score(fixture(),[qso(),qso(mode='D-STAR',time='21:01'),qso(band='2400',time='21:02',sent='1120L',exchange='120101P')],ctx())
  self.assertEqual([v['points'] for v in s.rows],[1,0,2]);self.assertEqual(s.total,6)
 def test_profile_missing_and_area_conflict(self):
  r=fixture();r['event']['exchange']['profiles'][1]['bands'].remove('24000')
  self.assertIsNone(score(r,[qso(band='24G',sent='1120L',exchange='120101P')],ctx()).total)
  self.assertIsNone(score(fixture(),[qso(area='10')],ctx()).total)
 def test_strict_schema(self):
  self.assertEqual(loads(dumps(fixture())),fixture())
  for field,value in [('bands',['1200']),('codes',['999']),('code_lengths',[True]),('points',-1),('m_threshold',5)]:
   r=fixture();r['event']['exchange']['profiles'][1][field]=value
   with self.assertRaises(ValueError):loads(dumps(r))
  for spec in [dict(bands={'A':'B','B':'A'},modes={},mode_families={}),dict(bands={},modes={},mode_families={'DV':'data'})]:
   r=fixture();r['event']['normalization']=spec
   with self.assertRaises(ValueError):loads(dumps(r))
 def test_export_normalized_summary_log_and_original_unchanged(self):
  with tempfile.TemporaryDirectory() as tmp:
   repo=Repository(tmp);p=repo.path_for('JH1HST','','2026-07-04')
   for time,band,mode in [('21:00','2.4G','D-STAR'),('21:01','2400','SSB')]:repo.open(p).append(QSO('2026-07-04',time,band,mode,'JA1AAA','59','59','Japan','Soka Japan','',''))
   original=p.read_bytes();sel=select_logs(repo,[p],'JH1HST');draft={key(row):dict(sent='1120L',received='120101P',status='確認済み') for row in sel.rows}
   info=dict(contest='試験専用',category='TEST',name='試験',address='試験',power='20',date='2026-07-06',signature='試験',oath=True)
   for format in ('JARL R1.0','JARL R2.1'):
    out=plan(sel,fixture(),draft,format,info,context=ctx()).preview();self.assertIn('2400 DV',out);self.assertNotIn('D-STAR',out);self.assertIn('<TOTALSCORE>2</TOTALSCORE>',out)
    if format=='JARL R1.0':self.assertIn('<SCORE BAND=2400MHz>2,2,1</SCORE>',out);self.assertNotIn('2.4G',out)
   self.assertEqual(p.read_bytes(),original)

if __name__=='__main__':unittest.main()
