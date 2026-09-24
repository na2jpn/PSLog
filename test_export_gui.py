import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import unittest,tempfile
from pathlib import Path
from PySide6.QtWidgets import QApplication
from model import QSO
from storage import Repository
from export_ui import ExportDialog
class ExportGuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def test_check_filters_preview_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=Repository(tmp);q=QSO('2026-01-01','00:05','7','CW','JA1YYY','599','599','Japan','Japan','BURO','')
            repo.open(repo.path_for('JH1HST/1','','2026-01-01')).append(q)
            repo.open(repo.path_for('JH1HST/P','','2026-01-01')).append(q)
            repo.open(repo.path_for('JJ1VMP','','2026-01-01')).append(q)
            d=ExportDialog(repo,'JH1HST/P');self.assertEqual(d.own.currentText(),'JH1HST');self.assertEqual(d.logs.count(),2)
            self.assertEqual([d.own.itemText(i) for i in range(d.own.count())],['JH1HST','JJ1VMP'])
            d.check_all(True);d.preview();self.assertTrue(d.save_button.isEnabled())
            d.start.setText('20260101');self.assertFalse(d.save_button.isEnabled());d.preview();self.assertTrue(d.save_button.isEnabled())
            d.end.setText('20260101');d.preview();d.write();self.assertEqual(len(list((Path(tmp)/'output'/'export').glob('*.adi'))),1)
            self.assertFalse(d.save_button.isEnabled());d.own.setCurrentText('JJ1VMP');self.assertEqual(d.logs.count(),1);d.close()
