import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import radio_control


class RadioFix3Tests(unittest.TestCase):
    def test_radio_manager_reports_worker_state(self):
        mgr=radio_control.RadioManager(Path('.'))
        self.assertFalse(mgr.is_running())

    def test_setupc_search_includes_program_files_x86(self):
        source=Path('radio_control.py').read_text(encoding='utf-8')
        self.assertIn("os.environ.get('ProgramFiles(x86)','')",source)
        self.assertIn("Path(root)/'com0com'/'setupc.exe'",source)

    def test_fix3_ui_hooks_are_present(self):
        main=Path('main.py').read_text(encoding='utf-8')
        settings=Path('settings_ui.py').read_text(encoding='utf-8')
        self.assertIn("('設定',['設定','無線機設定','ブラックリスト管理'])",main)
        self.assertIn("self.radio_connection_button=QPushButton('接続')",main)
        self.assertIn("initial_tab='無線機設定'",main)
        self.assertIn('sourceforge.net/projects/com0com/',settings)
        self.assertIn(r'C:\Program Files (x86)\com0com\setupc.exe',settings)
        self.assertIn("self.radio_connect=QPushButton('接続')",settings)


if __name__=='__main__':
    unittest.main()
