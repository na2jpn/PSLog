import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import tempfile,unittest
from unittest.mock import patch
from PySide6.QtWidgets import QApplication,QMessageBox
from blacklist import Blacklist,Entry
from blacklist_ui import BlacklistDialog,EntryDialog
from storage import save_settings,parse
from main import Window
class BlacklistGuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def test_warning_ok_keeps_record_and_remarks(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_settings(tmp,{'own':'JH1HST'});Blacklist(tmp).update(Entry('JA1YYY','test'))
            w=Window(tmp);w.call.setText('ja1yyy')
            with patch.object(QMessageBox,'warning',return_value=QMessageBox.StandardButton.Ok) as warning,patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.Yes):
                w.start_qso();w.set_text('remarks','hQSL');w.record();self.assertEqual(warning.call_count,1)
            self.assertEqual(w.rows[-1][1].remarks,'hQSL');self.assertTrue(w.repo.files('JH1HST'));w.close()
    def test_direct_record_warning_and_corrupt_list_nonblocking(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_settings(tmp,{'own':'JH1HST'});store=Blacklist(tmp);store.update(Entry('JA1YYY'))
            w=Window(tmp);w.call.setText('JA1YYY');w.set_text('date','2026-01-01');w.set_text('time','00:05');w.set_text('sent','59');w.set_text('received','59')
            with patch.object(w,'_confirm_record_time',return_value='normal'),patch.object(QMessageBox,'warning') as warning,patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.Yes):w.record();self.assertEqual(warning.call_count,1)
            store.path.write_bytes(b'broken');w.call.setText('JA2YYY')
            with patch.object(w,'_confirm_record_time',return_value='normal'),patch.object(QMessageBox,'warning') as warning,patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.Yes):w.record();self.assertTrue(warning.called)
            self.assertEqual(len(w.rows),2);w.close()
    def test_management_filter_edit_and_confirm_delete(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=BlacklistDialog(tmp);e=EntryDialog(d.store);e.call.setText('JA1YYY');e.memo.setPlainText('memo');e.save();self.assertTrue(e.saved)
            d.reload();d.table.selectRow(0);self.assertTrue(d.edit_button.isEnabled())
            d.filter.setText('notfound');self.assertFalse(d.delete_button.isEnabled());d.filter.clear();d.table.selectRow(0)
            with patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.No):d.delete()
            self.assertEqual(len(d.store.entries),1)
            with patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.Yes):d.delete()
            self.assertFalse(d.store.entries);d.close()
