import unittest
from pathlib import Path


class Patch07Fix2Tests(unittest.TestCase):
    def test_fixed_date_gui_tests_bypass_unrelated_time_dialog(self):
        blacklist=Path("test_blacklist_gui.py").read_text(encoding="utf-8")
        gui=Path("test_gui.py").read_text(encoding="utf-8")
        self.assertIn("patch.object(w,'_confirm_record_time',return_value='normal')",blacklist)
        self.assertGreaterEqual(gui.count("patch.object(w,'_confirm_record_time',return_value='normal')"),2)


if __name__=='__main__':
    unittest.main()
