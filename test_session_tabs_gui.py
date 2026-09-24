import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import tempfile,unittest
from unittest.mock import patch
from pathlib import Path

from PySide6.QtWidgets import QApplication,QMessageBox
from main import Window
from session_state import contest_session
from storage import save_settings,parse


class SessionTabsGuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([])

    def test_standard_add_close_and_last_tab_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_settings(tmp,{'own':'JH1HST','confirm_record':False})
            w=Window(tmp)
            self.assertEqual(len(w.workspace_sessions),1)
            self.assertEqual(w.session_tabs.tabText(0),'[A]JH1HST')
            self.assertFalse(w.session_tabs.tabsClosable())
            w._add_standard_workspace()
            self.assertEqual(len(w.workspace_sessions),2)
            self.assertEqual(w.session_tabs.tabText(1),'[A]JH1HST')
            self.assertTrue(w.session_tabs.tabsClosable())
            w._close_workspace(1)
            self.assertEqual(len(w.workspace_sessions),1)
            self.assertFalse(w.session_tabs.tabsClosable())
            self.assertEqual(len(w.recent_workspace_sessions),1)
            w._close_workspace(0)  # last tab must survive
            self.assertEqual(len(w.workspace_sessions),1)
            w.close()

    def test_contest_fast_record_filename_and_rmks(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_settings(tmp,{'own':'JH1HST','confirm_record':True})
            w=Window(tmp)
            s=contest_session('AADX','202609','JH1HST','14','CW','Japan')
            w.workspace_sessions.append(s);w.active_workspace_index=1
            w._rebuild_session_tabs();w._load_workspace(1)
            self.assertEqual(w.c_name.text(),'AADX')
            self.assertTrue(w.c_limited.isChecked())
            self.assertEqual(w.c_sent.text(),'599');self.assertEqual(w.c_received.text(),'599')
            w.c_call.setText('JA1AAA');w.contest_start_qso();w.c_exchange.setText('001');w.contest_record()
            path=Path(tmp)/'logbook/2026_JH1HST_AADX202609.txt'
            self.assertTrue(path.is_file())
            rows=[q for _,q in parse(path.read_bytes()).records]
            self.assertEqual(len(rows),1);self.assertEqual(rows[0].remarks,'001')
            self.assertEqual(rows[0].his_qth,'Japan')
            self.assertEqual(w.c_sent.text(),'599')
            w.close()

    def test_contest_empty_exchange_requires_explicit_yes(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_settings(tmp,{'own':'JH1HST','confirm_record':True})
            w=Window(tmp)
            s=contest_session('AADX','202609','JH1HST','14','CW','Japan')
            w.workspace_sessions.append(s);w.active_workspace_index=1
            w._rebuild_session_tabs();w._load_workspace(1)
            w.c_call.setText('JA1AAA');w.contest_start_qso();w.c_exchange.clear()
            with patch('main.QMessageBox.exec',return_value=QMessageBox.StandardButton.No):
                w.contest_record()
            path=Path(tmp)/'logbook/2026_JH1HST_AADX202609.txt'
            self.assertFalse(path.exists())
            self.assertIn('未入力',w.c_status.text())
            with patch('main.QMessageBox.exec',return_value=QMessageBox.StandardButton.Yes):
                w.contest_record()
            self.assertTrue(path.is_file())
            rows=[q for _,q in parse(path.read_bytes()).records]
            self.assertEqual(len(rows),1);self.assertEqual(rows[0].remarks,'')
            w.close()

    def test_open_sessions_restore_after_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_settings(tmp,{'own':'JH1HST','confirm_record':False})
            w=Window(tmp)
            w.workspace_sessions.append(contest_session('JA0','202609','JH1HST','7','CW','Japan'))
            w.active_workspace_index=1;w._rebuild_session_tabs();w._load_workspace(1)
            w.persist_settings();w.close()
            other=Window(tmp)
            self.assertEqual(len(other.workspace_sessions),2)
            self.assertEqual(other.active_workspace_index,1)
            self.assertEqual(other._active_workspace()['contest_name'],'JA0')
            self.assertEqual(other.session_tabs.tabText(0),'[A]JH1HST')
            self.assertEqual(other.session_tabs.tabText(1),'JA0')
            other.close()


if __name__=='__main__':unittest.main()
