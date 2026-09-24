import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import tempfile,unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtWidgets import QApplication,QMessageBox,QLabel

from model import QSO
from storage import Repository,save_settings
from log_merge_ui import LogMergeDialog
from main import Window


def write_log(path,qso):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(('\ufeff'+qso.to_ps()+'\r\n').encode('utf-8'))


class LogMergeGuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def test_check_is_required_before_execute(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=Repository(tmp);repo.book.mkdir(parents=True,exist_ok=True)
            target=repo.book/'2026_JH1HST_.txt';source=repo.book/'2026_JH1HST-1_TEST.txt'
            write_log(target,QSO('2026-01-02','00:00','7','CW','JA1AAA','599','599','Japan','Japan','',''))
            write_log(source,QSO('2026-01-01','00:00','7','CW','JA1BBB','599','599','Japan','Japan','',''))
            d=LogMergeDialog(repo);self.addCleanup(d.close)
            labels=[x.text() for x in d.findChildren(QLabel)]
            self.assertTrue(any('JX1XXX' in text for text in labels));self.assertFalse(any('JH1HST_.txt' in text for text in labels))
            self.assertFalse(d.execute_button.isEnabled())
            d.target.setText(str(target));d.source.setText(str(source));d.run_check()
            self.assertTrue(d.execute_button.isEnabled());self.assertIn('ファイルチェック OK',d.result.toPlainText())
            with patch.object(QMessageBox,'question',return_value=QMessageBox.Yes),patch.object(QMessageBox,'information'):
                d.run_execute()
            self.assertTrue(target.exists());self.assertFalse(source.exists());self.assertFalse(d.execute_button.isEnabled())

    def test_main_menu_and_tab_labels(self):
        with tempfile.TemporaryDirectory() as tmp:
            # Give Window a normal configured callsign so __init__ never queues
            # the first-start QInputDialog timer.  This is safer than patching the
            # callback and manually pumping the global Qt event queue, which can
            # leave native Qt cleanup in an unsafe state at interpreter shutdown
            # on Windows.
            save_settings(tmp,{'own':'JH1HST'})
            w=Window(tmp)
            try:
                self.assertEqual(w.add_session_button.text(),'＋タブ')
                self.assertIn('min-height: 24px',w.session_tabs.styleSheet())
                action=next(a for a in w.action_refs if a.text()=='ログファイル統合')
                self.assertTrue(action.isEnabled())
            finally:
                w.timer.stop()
                w.close()
                w.deleteLater()
                QApplication.sendPostedEvents()
                QApplication.processEvents()


if __name__=='__main__':unittest.main()
