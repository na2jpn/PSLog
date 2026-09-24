import unittest
from pathlib import Path
from contest_ui import rule_number_candidates,sync_rule_exchange_fields
from contest_rules import loads

ROOT=Path(__file__).parent

class V25ContestRuleExtractionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rule=loads((ROOT/'config/rules/gigahertz_2026.txt').read_text(encoding='utf-8'))

    def test_gigahertz_rule_filters_rmks_candidates_and_derives_area(self):
        valid,raw=rule_number_candidates(self.rule,'BURO 36 0901')
        self.assertEqual(valid,['0901'])
        self.assertIn('36',raw)
        d={'received':'0901'}
        sync_rule_exchange_fields(self.rule,d)
        self.assertEqual(d['area'],'0901')

    def test_unrelated_number_does_not_become_gigahertz_exchange(self):
        valid,raw=rule_number_candidates(self.rule,'BURO 36')
        self.assertEqual(valid,[])
        self.assertEqual(raw,['36'])

if __name__=='__main__':
    unittest.main()
