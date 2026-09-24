import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import tempfile,unittest
from PySide6.QtWidgets import QApplication
from location_ui import LocationDialog

class V23Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([])

    def test_his_qth_remember_defaults_off(self):
        with tempfile.TemporaryDirectory() as root:
            d=LocationDialog(root,'',remember_default=False)
            self.assertFalse(d.remember.isChecked())
            d.deleteLater()

    def test_my_qth_remember_defaults_on_and_stays_on_after_selection(self):
        with tempfile.TemporaryDirectory() as root:
            d=LocationDialog(root,'',remember_default=True)
            self.assertTrue(d.remember.isChecked())
            if d.table.rowCount():
                d.table.selectRow(0)
                self.assertTrue(d.remember.isChecked())
            d.deleteLater()

if __name__=='__main__':
    unittest.main()
