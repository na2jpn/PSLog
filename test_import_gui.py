import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import unittest,tempfile
from pathlib import Path
from unittest.mock import patch
from PySide6.QtWidgets import QApplication,QMessageBox
from storage import Repository
from model import QSO
from import_ui import ImportDialog

class ImportGuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def test_preview_invalidation_confirm_and_repeat(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=Repository(Path(tmp)/'data');source=Path(tmp)/'pslog.txt'
            q=QSO('2026-01-01','00:05','7','CW','JA1YYY','599','599','Japan','Japan','BURO','')
            source.write_text(q.to_ps()+'\n');d=ImportDialog(repo,'JH1HST');d.source.setText(str(source));d.preview()
            self.assertTrue(d.save_button.isEnabled());d.suffix.setText('test');self.assertFalse(d.save_button.isEnabled());d.preview()
            with patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.No):d.save()
            self.assertFalse(list(repo.book.glob('*.txt')))
            signals=[];d.logs_changed.connect(lambda:signals.append(True))
            with patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.Yes):d.save()
            self.assertEqual(signals,[True]);self.assertFalse(d.save_button.isEnabled())
            d.preview();self.assertFalse(d.save_button.isEnabled());d.close()
