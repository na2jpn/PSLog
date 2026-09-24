import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import tempfile,unittest
from datetime import datetime,timedelta
from pathlib import Path
from unittest.mock import patch

from storage import VERSION,save_settings
from session_state import easy_session,session_title
from record_time import needs_confirmation


class Patch071077CoreTests(unittest.TestCase):
    def test_version(self):
        self.assertEqual(VERSION,'1.14')

    def test_easy_title_ignores_log_suffix_but_keeps_callsign_portable_part(self):
        self.assertEqual(session_title(easy_session(1,{'own':'JH1HST/1','suffix':'JP1220'})),'[E]JH1HST/1')
        self.assertEqual(session_title(easy_session(1,{'own':''})),'EASYタブ')

    def test_easy_time_rule_uses_five_minutes(self):
        now=datetime(2026,9,24,20,10)
        self.assertFalse(needs_confirmation('2026-09-24','20:06',now,5))
        self.assertTrue(needs_confirmation('2026-09-24','20:05',now,5))

    def test_source_has_two_easy_pages_and_large_logsearch(self):
        text=Path(__file__).with_name('main.py').read_text(encoding='utf-8')
        self.assertIn("p1_head=QLabel('1 / 2 ページ')",text)
        self.assertIn("p2_head=QLabel('2 / 2 ページ')",text)
        self.assertIn("self.e_back=QPushButton('最初に戻る')",text)
        self.assertIn("self.e_code_to_qth=QPushButton('JCC/JCGから名称を入れる')",text)
        self.assertIn("QGroupBox('LogSearch')",text)
        self.assertIn("record_time_needs_confirmation(qso.date,qso.time,now,5)",text)

    def test_about_explains_pipe_separate_and_cabrillo(self):
        text=Path(__file__).with_name('help_ui.py').read_text(encoding='utf-8')
        self.assertIn('Pipe Separate（パイプセパレート）',text)
        self.assertIn('Cabrillo形式',text)
        self.assertIn("if topic=='PSLogについて'",text)


try:
    import PySide6  # noqa: F401
    HAVE_QT=True
except Exception:
    HAVE_QT=False


@unittest.skipUnless(HAVE_QT,'PySide6 not installed')
class Patch071077GuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app=QApplication.instance() or QApplication([])

    def test_easy_page_navigation_and_persistence_fields(self):
        from main import Window
        with tempfile.TemporaryDirectory() as tmp:
            save_settings(tmp,{'own':'JH1HST','my_qth':'Soka Saitama Japan','confirm_record':False})
            w=Window(tmp);w._add_easy_workspace()
            self.assertIs(w.page_stack.currentWidget(),w.easy_scroll)
            self.assertEqual(w.e_pages.currentIndex(),0)
            w.e_call.setText('JA1AAA');w.e_band.setCurrentText('7');w.easy_set_mode('CW');w.e_sent.setText('599');w.e_received.setText('599')
            w.easy_next_page();self.assertEqual(w.e_pages.currentIndex(),1)
            self.assertEqual(w.e_my_qth.text(),'Soka Saitama Japan')
            self.assertIn('JA1AAA',w.e_page1_summary.text())
            w.easy_back_page();self.assertEqual(w.e_pages.currentIndex(),0)
            w.close()

    def test_easy_record_keeps_band_mode_myqth_and_returns_page1(self):
        from main import Window
        with tempfile.TemporaryDirectory() as tmp:
            save_settings(tmp,{'own':'JH1HST','my_qth':'Soka Saitama Japan','confirm_record':False})
            w=Window(tmp);w._add_easy_workspace();w.e_call.setText('JA1AAA');w.e_band.setCurrentText('7');w.easy_set_mode('CW');w.e_sent.setText('599');w.e_received.setText('599');w.easy_next_page()
            with patch.object(w,'_easy_time_choice',return_value='normal'),patch.object(w,'_easy_confirm_record',return_value=True):w.easy_record()
            self.assertEqual(w.e_pages.currentIndex(),0);self.assertEqual(w.e_band.currentText(),'7');self.assertEqual(w.easy_mode_value(),'CW');self.assertEqual(w.e_my_qth.text(),'Soka Saitama Japan')
            self.assertEqual(w.e_call.text(),'');self.assertEqual(w.e_his_qth.text(),'');self.assertEqual(w.e_code.text(),'');self.assertEqual(w.e_remarks.text(),'')
            w.close()


if __name__=='__main__':unittest.main()
