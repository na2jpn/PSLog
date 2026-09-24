import ast
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parent

class EmbeddedLogSearchRegressionTests(unittest.TestCase):
    def test_main_embedded_logsearch_double_click_opens_detail_path(self):
        source=(ROOT/'main.py').read_text(encoding='utf-8')
        ast.parse(source)
        self.assertIn("self.table.doubleClicked.connect(lambda index:self.show_standard_history_detail(index.row()))",source)
        self.assertIn("self.c_table.doubleClicked.connect(lambda index:self.show_contest_history_detail(index.row()))",source)
        self.assertIn("self._standard_history_visible=visible",source)
        self.assertIn("self._contest_history_visible=visible",source)
        self.assertIn("from search_ui import DetailDialog",source)
        self.assertIn("if dialog.saved:reload_callback()",source)

if __name__=='__main__':
    unittest.main()
