import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import tempfile,unittest
from PySide6.QtWidgets import QApplication
from main import Window
from storage import load_settings
from location_ui import LocationDialog

class V22Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([])

    def test_set_station_persists_immediately(self):
        with tempfile.TemporaryDirectory() as root:
            w=Window(root)
            w.own.setText('JH1HST')
            w.suffix.setText('JP1220')
            w.set_station()
            saved=load_settings(root)
            self.assertEqual(saved.get('own'),'JH1HST')
            self.assertEqual(saved.get('suffix'),'JP1220')
            w.deleteLater()

    def test_location_row_prefills_candidate_and_can_apply_immediately(self):
        with tempfile.TemporaryDirectory() as root:
            d=LocationDialog(root,'東京都墨田区')
            self.assertGreater(d.table.rowCount(),0)
            d.table.selectRow(0)
            self.assertTrue(d.qth.currentText().strip())
            self.assertTrue(d.apply_button.isEnabled())
            chosen=d.qth.currentText()
            d.apply()
            self.assertEqual(d.result_value[0],chosen)
            d.deleteLater()

if __name__=='__main__':
    unittest.main()
