import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import tempfile,unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from storage import VERSION,save_settings
from session_state import MAX_EASY,easy_session,next_easy_slot,restore,session_title,standard_session
from jccjcg_batch import qth_from_code
from locations import load,find,candidates


class Patch061076CoreTests(unittest.TestCase):
    def test_version(self):
        self.assertEqual(VERSION,'1.14')

    def test_easy_title_slots_limit_and_restore(self):
        empty=easy_session(1,{'own':''})
        named=easy_session(2,{'own':'JH1HST'})
        self.assertEqual(session_title(empty),'EASYタブ')
        self.assertEqual(session_title(named),'[E]JH1HST')
        self.assertIsNone(next_easy_slot([easy_session(1),easy_session(2)]))
        raw=[standard_session(1,{'own':'JH1HST'})]
        raw += [easy_session((i%2)+1,{'own':f'JH1HS{i}'}) for i in range(5)]
        sessions,_,_=restore({'workspace_sessions':raw},datetime(2026,9,24))
        self.assertEqual(sum(s['type']=='easy' for s in sessions),MAX_EASY)

    def test_jcg_qth_joins_county_and_gun_for_human_output(self):
        root=Path(__file__).parent
        self.assertEqual(qth_from_code(root,'16001'),'Agatsumagun Gumma Japan')
        self.assertEqual(qth_from_code(root,'16001H'),'Nakanojo Agatsumagun Gumma Japan')
        self.assertEqual(qth_from_code(root,'11002'),'Ashigarakamigun Kanagawa Japan')
        data=load(root)
        row=find(data,'群馬県吾妻郡中之条町')[0]
        shown=[qth for qth,_ in candidates(data,row)]
        self.assertIn('Nakanojo Agatsumagun Gumma Japan',shown)
        self.assertTrue(all(' gun ' not in qth.casefold() for qth in shown if 'agatsuma' in qth.casefold()))

    def test_main_source_has_easy_add_menu(self):
        text=Path(__file__).with_name('main.py').read_text(encoding='utf-8')
        self.assertIn("menu.addAction('EASYタブを追加')",text)
        self.assertIn("self._easy_workspace_count()<MAX_EASY",text)


try:
    import PySide6  # noqa: F401
    HAVE_QT=True
except Exception:
    HAVE_QT=False


@unittest.skipUnless(HAVE_QT,'PySide6 not installed')
class Patch061076GuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app=QApplication.instance() or QApplication([])

    def test_easy_workspace_has_dedicated_page_and_allows_two(self):
        from main import Window
        with tempfile.TemporaryDirectory() as tmp:
            save_settings(tmp,{'own':'JH1HST','my_qth':'Soka Saitama Japan','confirm_record':False})
            w=Window(tmp)
            w._add_easy_workspace()
            self.assertEqual(w._active_workspace()['type'],'easy')
            self.assertEqual(w.session_tabs.tabText(w.active_workspace_index),'[E]JH1HST')
            self.assertIs(w.page_stack.currentWidget(),w.easy_scroll)
            w._add_easy_workspace()
            self.assertEqual(sum(s['type']=='easy' for s in w.workspace_sessions),2)
            self.assertIsNone(next_easy_slot(w.workspace_sessions))
            w.close()

    def test_standard_record_clears_his_qth_and_code_but_keeps_my_qth(self):
        from PySide6.QtWidgets import QMessageBox
        from main import Window
        with tempfile.TemporaryDirectory() as tmp:
            save_settings(tmp,{'own':'JH1HST','my_qth':'Soka Saitama Japan','confirm_record':False})
            w=Window(tmp)
            w.call.setText('JA1AAA');w.start_qso()
            w.set_text('his_qth','Tokyo Japan');w.set_text('code','1001');w.set_text('my_qth','Soka Saitama Japan')
            with patch.object(w,'_confirm_record_time',return_value='normal'),patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.Yes):
                w.record()
            self.assertEqual(w.text('his_qth'),'')
            self.assertEqual(w.text('code'),'')
            self.assertEqual(w.text('my_qth'),'Soka Saitama Japan')
            w.close()


if __name__=='__main__':unittest.main()
