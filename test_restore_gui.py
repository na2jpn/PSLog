import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import unittest,tempfile
from unittest.mock import patch
from dataclasses import replace
from PySide6.QtWidgets import QApplication,QMessageBox
from model import QSO
from storage import Repository
from restore_ui import RestoreDialog

class RestoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.repo=Repository(self.tmp.name)
        self.q=QSO('2026-01-01','00:05','7','CW','JA1YYY','599','599','Japan','Soka Saitama Japan','BURO','')
        self.path=self.repo.path_for('JH1HST/1','',self.q.date)
        s=self.repo.open(self.path);s.append(self.q);self.old=self.path.read_bytes()
        self.backup=self.repo.backup(self.path,self.old)
        s.append(replace(self.q,time='00:06'));self.current=self.path.read_bytes()
        self.d=RestoreDialog(self.repo);self.addCleanup(self.d.close);self.d.table.selectRow(0)
    def apply(self,answer=QMessageBox.StandardButton.Yes):
        with patch.object(QMessageBox,'question',return_value=answer):self.d.restore()
    def test_restore_and_return_to_pre_restore(self):
        self.assertTrue(self.d.restore_button.isEnabled());self.assertIn('2交信',self.d.details.toPlainText())
        signals=[];self.d.logs_changed.connect(lambda:signals.append(True));self.apply()
        self.assertEqual(self.path.read_bytes(),self.old);self.assertEqual(signals,[True])
        self.assertTrue(any(p.read_bytes()==self.current for p in self.repo.backups(self.path)))
        self.d.table.selectRow(0);self.apply();self.assertEqual(self.path.read_bytes(),self.current)
    def test_cancel_is_no_change(self):
        self.apply(QMessageBox.StandardButton.No);self.assertEqual(self.path.read_bytes(),self.current)
    def test_changed_target_blocks_restore(self):
        raw=self.current+b'\r\n';self.path.write_bytes(raw);self.apply()
        self.assertEqual(self.path.read_bytes(),raw);self.assertFalse(self.d.restore_button.isEnabled())
    def test_changed_backup_blocks_restore(self):
        self.backup.write_bytes(self.old+b'\r\n');self.apply()
        self.assertEqual(self.path.read_bytes(),self.current);self.assertFalse(self.d.restore_button.isEnabled())
    def test_deleted_original_and_corrupt_original(self):
        self.path.unlink();self.d.reload();self.d.table.selectRow(0);self.apply()
        self.assertEqual(self.path.read_bytes(),self.old)
        corrupt=b'\xff\xfe\x00';self.path.write_bytes(corrupt);self.d.reload();self.d.table.selectRow(0);self.apply()
        self.assertEqual(self.path.read_bytes(),self.old)
        self.assertTrue(any(p.read_bytes()==corrupt for p in self.repo.backups(self.path)))
    def test_invalid_backup_and_filter_clear_selection(self):
        self.d.filter.setText('notfound');self.assertFalse(self.d.pending);self.assertEqual(self.d.table.rowCount(),0)
        self.d.filter.clear();self.backup.write_bytes(b'invalid\n');self.d.table.selectRow(0)
        self.assertFalse(self.d.restore_button.isEnabled());self.assertEqual(self.path.read_bytes(),self.current)
    def test_backup_failure_keeps_original(self):
        with patch.object(self.repo,'backup',side_effect=OSError('disk full')):self.apply()
        self.assertEqual(self.path.read_bytes(),self.current);self.assertIn('disk full',self.d.status.text())
