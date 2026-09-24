import json, unittest
from pathlib import Path

class V39GigahertzDuplicateTests(unittest.TestCase):
    def test_gigahertz_different_modes_are_not_duplicates(self):
        p=Path(__file__).parent/'config'/'rules'/'gigahertz_2026.txt'
        r=json.loads(p.read_text(encoding='utf-8'))
        self.assertTrue(r['duplicate']['enabled'])
        self.assertTrue(r['duplicate']['by_mode'])
        self.assertEqual(r['event']['duplicate_fields'],['call','band','mode_group'])
        self.assertEqual(r['event']['mode_groups']['CW'],'cw')
        self.assertEqual(r['event']['mode_groups']['SSB'],'ssb')
        self.assertEqual(r['event']['mode_groups']['FM'],'fm')

if __name__=='__main__':
    unittest.main()
