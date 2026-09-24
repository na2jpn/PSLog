import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import unittest,tempfile
from pathlib import Path
from unittest.mock import patch
from PySide6.QtWidgets import QApplication,QMessageBox
from storage import Repository
from import_ui import ImportDialog
from test_hamlog_import import BASE,csvbytes
class HamlogGuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def test_options_acknowledgement_and_import(self):
        with tempfile.TemporaryDirectory() as tmp:
            row=BASE.copy();row[2]='00:05';p=Path(tmp)/'hamlog.csv';p.write_bytes(csvbytes([row]));repo=Repository(Path(tmp)/'app')
            d=ImportDialog(repo,'JH1HST');d.source.setText(str(p));d.preview();self.assertFalse(d.save_button.isEnabled())
            d.csv_timezone.setCurrentIndex(1);d.preview();self.assertIn('OP:太郎',d.details.toPlainText())
            d.conversions.setChecked(True);self.assertTrue(d.save_button.isEnabled())
            with patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.Yes):d.save()
            self.assertEqual(len(repo.files('JH1HST')),1);d.close()
