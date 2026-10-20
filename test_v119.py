import json,tempfile,unittest
from pathlib import Path
from award_applications import Applications
from storage import StorageError
from contest_rules import loads,score
from test_contest_batch10 import context,trow
import rule_pack
ROOT=Path(__file__).parent
class V119Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.store=Applications(self.root)
 def test_scope_persistence_clear_and_portable_base(self):
  self.store.set('JH1HST/1','JCC','1319','7',True)
  self.assertTrue(Applications(self.root).checked('JH1HST','JCC','1319','7'))
  for args in [('JH1HST','JCC','1319','*'),('JH1HST','JCG','1319','7'),('JQ7FIU','JCC','1319','7'),('JH1HST','JCC','1318','7')]:self.assertFalse(self.store.checked(*args))
  self.store.set('JH1HST','JCC','1319','7',False);self.assertFalse(self.store.checked('JH1HST','JCC','1319','7'))
 def test_two_instances_preserve_other_changes(self):
  other=Applications(self.root);self.store.set('JH1HST','DXCC','K','*',True);other.set('JH1HST','DXCC','JA','7',True)
  self.assertTrue(self.store.checked('JH1HST','DXCC','K'));self.assertTrue(self.store.checked('JH1HST','DXCC','JA','7'))
 def test_corrupt_state_preserved(self):
  self.store.path.parent.mkdir();self.store.path.write_bytes(b'broken');before=self.store.path.read_bytes()
  with self.assertRaises(StorageError):self.store.set('JH1HST','DXCC','K','*',True)
  self.assertEqual(self.store.path.read_bytes(),before)
 def test_tokyo_new_direction_and_number_validation(self):
  r=loads((ROOT/'config/rules/tokyo_cw_2026.txt').read_text(encoding='utf-8-sig'))
  for code,sent in [('1C7','002'),('2C7','13')]:self.assertEqual(score(r,[trow(sent=sent)],context(r,code)).total,2)
  for code,sent in [('2C7','002'),('1C7','13')]:self.assertIsNone(score(r,[trow(sent=sent)],context(r,code)).total)
 def test_new_years_and_old_definitions_both_available(self):
  for ident in ('cq-ww-cw','cq-ww-ssb','kcwa_cw','all_ja0_160m'):
   for year in (2025,2026):self.assertEqual(loads((ROOT/f'config/rules/{ident}_{year}.txt').read_text(encoding='utf-8-sig'))['year'],year)
 def test_dates_deadlines_and_human_operation(self):
  expected={'cq-ww-cw':('2026-11-28 00:00','2026-11-30 00:00'),'cq-ww-ssb':('2026-10-24 00:00','2026-10-26 00:00'),'kcwa_cw':('2026-12-06 10:00','2026-12-06 20:00'),'all_ja0_160m':('2026-12-19 21:00','2026-12-19 23:00')}
  for ident,pair in expected.items():
   r=loads((ROOT/f'config/rules/{ident}_2026.txt').read_text(encoding='utf-8-sig'));e=r['event'];self.assertEqual((e['windows'][0]['start'],e['windows'][0]['end']),pair)
   if ident.startswith('cq-ww'):self.assertIn('48時間',e['submission']['instructions']);self.assertTrue(any('人間' in x for x in e['required_flags']))
   if ident=='kcwa_cw':self.assertIn('kcwa2026@',e['submission']['instructions']);self.assertIn('43',r['name'])
 def test_packs_validate_and_updated_tokyo_bytes(self):
  for filename in ('pslog_119_rules_2026_r1.zip','tokyo_cw_2026_r1.zip','batch10_acag_xpo_tokyo_cw_2026_r1.zip','cq-ww-cw_2026_r1.zip','cq-ww-ssb_2026_r1.zip','kcwa_cw_2026_r1.zip','all_ja0_160m_2026_r1.zip'):
   _,items=rule_pack.read_archive(ROOT/'distribution/rules'/filename)
   for r,entry,raw in items:
    if r['id']=='tokyo_cw':self.assertEqual(raw,(ROOT/'config/rules/tokyo_cw_2026.txt').read_bytes())
if __name__=='__main__':unittest.main()
