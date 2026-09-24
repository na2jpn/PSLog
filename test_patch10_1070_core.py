import json
from pathlib import Path
import tempfile
import unittest

from contest_export import submission_band_sort_default
from contest_rules import RuleStore,management_rule_label
from storage import VERSION

ROOT=Path(__file__).resolve().parent

class Patch1070CoreTests(unittest.TestCase):
    def test_version(self):
        self.assertEqual(VERSION,'1.14')

    def test_management_label_adds_start_month(self):
        rule=json.loads((ROOT/'config/rules/ai_chikyu_2026.txt').read_text(encoding='utf-8-sig'))
        self.assertEqual(management_rule_label(rule,'愛・地球博記念コンテスト（2026）'),'愛・地球博記念コンテスト（2026/9）')

    def test_management_label_leaves_old_rule_without_windows_unchanged(self):
        rule={'name':'旧ルール','year':2026}
        self.assertEqual(management_rule_label(rule,'旧ルール（2026）'),'旧ルール（2026）')

    def test_band_sort_default_is_rule_driven(self):
        rule=json.loads((ROOT/'config/rules/ai_chikyu_2026.txt').read_text(encoding='utf-8-sig'))
        self.assertTrue(submission_band_sort_default(rule))
        rule['event']['submission']['order']='time'
        self.assertFalse(submission_band_sort_default(rule))

if __name__=='__main__':unittest.main()
