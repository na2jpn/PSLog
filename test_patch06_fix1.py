from pathlib import Path
import unittest

class Patch06Fix1Tests(unittest.TestCase):
    def test_search_dialog_filename_argument_is_not_shadowed(self):
        source=Path('search_ui.py').read_text(encoding='utf-8')
        self.assertIn("filename_filter=line_filter('filename','空欄は全ログ・部分一致')",source)
        self.assertIn("if filename:self.filters['filename'].setText(filename)",source)
        self.assertNotIn("\n        filename=line_filter('filename','空欄は全ログ・部分一致')",source)

    def test_gui_regressions_follow_patch06_contract(self):
        blacklist=Path('test_blacklist_gui.py').read_text(encoding='utf-8')
        self.assertIn("w.set_text('sent','59');w.set_text('received','59')",blacklist)
        pota=Path('test_pota_gui.py').read_text(encoding='utf-8')
        self.assertIn("'コンテストルール表示…'",pota)
        self.assertNotIn("self.assertEqual(len(contest.actions()),3)",pota)

if __name__=='__main__':unittest.main()
