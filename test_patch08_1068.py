import unittest
from pathlib import Path
from storage import VERSION


class Patch08V1068Tests(unittest.TestCase):
    def test_version(self):
        self.assertEqual(VERSION,'1.14')

    def test_qsl_detail_allows_multiple_checkbox_candidate_selection(self):
        src=Path('qsl_ui.py').read_text(encoding='utf-8')
        self.assertNotIn('QRadioButton',src)
        self.assertNotIn('QButtonGroup',src)
        self.assertIn('複数候補・手動候補はチェックボックスで必要なQSOを複数選べます。',src)
        self.assertIn("self.table.setHorizontalHeaderLabels(['選択'",src)
        self.assertIn('def _check_toggled',src)
        self.assertIn('set_selected(entry,hit,checked)',src)

    def test_unique_qso_keeps_checkbox_selector(self):
        src=Path('qsl_ui.py').read_text(encoding='utf-8')
        self.assertIn('button_widget=QCheckBox()',src)
        self.assertIn("このQSOを処理対象にします。",src)


if __name__=='__main__':unittest.main()
