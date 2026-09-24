import os,tempfile,unittest
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtWidgets import QApplication,QFormLayout
from activity_ui import ActivityDialog
from storage import Repository

class V40UiRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([])

    def test_award_history_inner_form_is_available_to_defaults(self):
        with tempfile.TemporaryDirectory() as td:
            d=ActivityDialog(Repository(td),'JH1HST',award=True)
            self.assertIsInstance(d.history_form,QFormLayout)
            d.close()

if __name__=='__main__':
    unittest.main()
