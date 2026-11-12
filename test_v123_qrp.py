"""All bundled QRP categories must reach both JARL exporters."""
from pathlib import Path
from test_contest_batch10 import ExportFixture
from contest_rules import loads,score
from contest_export import plan
ROOT=Path(__file__).parent
class QRP123Tests(ExportFixture):
 def test_all_16_categories_export_formal_name_and_original_unchanged(self):
  r=loads((ROOT/'config/rules/jarl_qrp_club_2026.txt').read_text(encoding='utf-8'));self.assertEqual(len(r['event']['categories']),16)
  for cat in r['event']['categories']:
   with self.subTest(category=cat['id']):
    v=dict(category=cat['id'],entry_categories=[cat['id']],power=4,station_type='individual',flags={k:True for k in r['event']['required_flags']+cat['required_flags']});q=dict(date='2026-11-03',time='13:00',band=cat['bands'][0],mode='CW',own='JX1XXX',call='JX2XXX',sent='13P',exchange='106P');p,original,sel,draft,info=self.fixture(r,[q],v)
    for fmt in ['JARL R1.0','JARL R2.1']:
     text=plan(sel,r,draft,fmt,info,context=v).preview();self.assertIn('<CONTESTNAME>JARL QRP CLUB 2026年 QRP コンテスト</CONTESTNAME>',text);self.assertIn('<CATEGORYCODE>'+cat['id']+'</CATEGORYCODE>',text);self.assertIn('<TOTALSCORE>1</TOTALSCORE>',text)
    self.assertEqual(p.read_bytes(),original)
