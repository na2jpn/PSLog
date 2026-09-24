import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import tempfile, unittest
from pathlib import Path

from storage import VERSION, save_settings


class Patch081078CoreTests(unittest.TestCase):
    def test_version(self):
        self.assertEqual(VERSION,'1.14')

    def test_easy_band_label_and_green_groupbox_are_in_source(self):
        text=Path(__file__).with_name('main.py').read_text(encoding='utf-8')
        self.assertIn("band_label=QLabel('バンド（MHz）')",text)
        self.assertIn("self.easy_entry.setObjectName('easyEntryBox')",text)
        self.assertIn('QGroupBox#easyEntryBox {border:1px solid #6fa37d;',text)


try:
    import PySide6  # noqa: F401
    HAVE_QT=True
except Exception:
    HAVE_QT=False


@unittest.skipUnless(HAVE_QT,'PySide6 not installed')
class Patch081078GuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app=QApplication.instance() or QApplication([])

    def test_easy_label_and_groupbox_style(self):
        from PySide6.QtWidgets import QLabel
        from main import Window
        with tempfile.TemporaryDirectory() as tmp:
            save_settings(tmp,{'own':'JH1HST','my_qth':'Soka Saitama Japan','confirm_record':False})
            w=Window(tmp);w._add_easy_workspace()
            labels=[x.text() for x in w.easy_entry.findChildren(QLabel)]
            self.assertIn('バンド（MHz）',labels)
            self.assertEqual(w.easy_entry.objectName(),'easyEntryBox')
            self.assertIn('#6fa37d',w.easy_entry.styleSheet())
            w.close()


if __name__=='__main__':unittest.main()
