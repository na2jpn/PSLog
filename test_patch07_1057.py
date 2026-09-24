import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from record_time import drift_seconds, needs_confirmation
from storage import VERSION

JST=timezone(timedelta(hours=9))


class Patch071057Tests(unittest.TestCase):
    def test_version(self):
        self.assertEqual(VERSION,'1.14')

    def test_record_time_threshold_is_three_minutes_or_more(self):
        now=datetime(2026,9,21,7,10,0,tzinfo=JST)
        self.assertFalse(needs_confirmation('2026-09-21','07:08',now,3))
        self.assertTrue(needs_confirmation('2026-09-21','07:07',now,3))
        self.assertTrue(needs_confirmation('2026-09-21','07:13',now,3))
        self.assertEqual(drift_seconds('2026-09-21','07:07',now),180)

    def test_patch07_ui_sources(self):
        main=Path('main.py').read_text(encoding='utf-8')
        viewer=Path('rule_view_ui.py').read_text(encoding='utf-8')
        overview=Path('contest_overview.py').read_text(encoding='utf-8')
        rule_data=Path('rule_view_data.py').read_text(encoding='utf-8')
        self.assertIn('現在の時刻と3分以上ズレています。',main)
        self.assertIn("QPushButton('現時刻で記録')",main)
        self.assertIn("setObjectName('compactBlue')",main)
        self.assertIn('setFixedHeight(21)',main)
        self.assertIn('background-color:#dff0e4',main)
        self.assertIn("QColor(color['dark'])",main)
        self.assertIn('Qt.Key.Key_Return,Qt.Key.Key_Enter',viewer)
        self.assertIn("QPushButton('公式規約を開く')",viewer)
        self.assertNotIn('構造化',overview)
        self.assertNotIn('構造化',rule_data)


if __name__=='__main__':
    unittest.main()
