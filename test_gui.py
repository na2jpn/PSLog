"""Offscreen Qt integration check, no user data. Requires PySide6."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PySide6.QtWidgets import QApplication,QMessageBox
from main import Window
from storage import save_settings,parse

class GuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def test_record_restart_and_external_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_settings(tmp,{'own':'JH1HST/1','my_qth':'Soka Saitama Japan'})
            w=Window(tmp);w.show();self.app.processEvents()
            w.call.setText('JA1YYY');w.start_qso()
            w.set_text('date','2025-12-31');w.set_text('time','23:58')
            self.assertEqual(w.text('sent'),'59')
            with patch.object(w,'_confirm_record_time',return_value='normal'),patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.Yes):w.record()
            p=Path(tmp)/'logbook/2025_JH1HST-1_.txt'
            self.assertTrue(p.exists());self.assertEqual(len(parse(p.read_bytes()).records),1)
            w.close();self.app.processEvents()
            w=Window(tmp);self.assertEqual(len(w.rows),1)
            w.call.setText('JA1YYY');w.start_qso();w.set_text('date','2025-12-31');w.set_text('time','23:59')
            raw=p.read_bytes()+b'\r\n';p.write_bytes(raw)
            with patch.object(w,'_confirm_record_time',return_value='normal'),patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.Yes),patch.object(QMessageBox,'warning') as warning:
                w.record();self.assertTrue(warning.called)
            self.assertEqual(p.read_bytes(),raw)
            w.close();self.app.processEvents()

if __name__=='__main__':unittest.main()
