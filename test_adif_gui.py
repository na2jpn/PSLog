import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import unittest,tempfile
from pathlib import Path
from unittest.mock import patch
from PySide6.QtWidgets import QApplication,QMessageBox
from storage import Repository
from import_ui import ImportDialog
from test_adif_import import adi,BASE
class AdifGuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def test_acknowledgement_and_save(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'sample.adi';source.write_bytes(adi(**BASE));repo=Repository(Path(tmp)/'data')
            d=ImportDialog(repo,'JH1HST/1');d.source.setText(str(source));d.preview()
            self.assertFalse(d.save_button.isEnabled());self.assertIn('150512',d.details.toPlainText())
            d.conversions.setChecked(True);self.assertTrue(d.save_button.isEnabled())
            d.suffix.setText('test');self.assertFalse(d.conversions.isChecked());d.preview();d.conversions.setChecked(True)
            with patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.Yes):d.save()
            self.assertEqual(len(repo.files('JH1HST/1')),1);d.close()
