import os,tempfile,unittest
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtWidgets import QApplication
from unittest.mock import patch
from storage import Repository
from activity_ui import ActivityDialog

class V33AwardOutputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([])

    def test_award_output_preview_is_compact(self):
        with tempfile.TemporaryDirectory() as td:
            d=ActivityDialog(Repository(td),'JH1HST',award=True)
            self.assertLessEqual(d.output.maximumHeight(),300)
            self.assertGreaterEqual(d.output.minimumHeight(),180)
            self.assertEqual(d.save_button.text(),'ファイルに保存…')
            d.close()

if __name__=='__main__':
    unittest.main()
