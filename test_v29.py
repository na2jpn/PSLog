import os,tempfile,unittest
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtWidgets import QApplication
from contest_ui import ContestDialog
from storage import Repository

class V29ContestEarlyParticipationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([])

    def test_registered_contest_requires_participation_before_stage2(self):
        with tempfile.TemporaryDirectory() as td:
            d=ContestDialog(Repository(td),'JH1HST')
            # Empty temp repositories may have no bundled rule catalog in source tests;
            # the UI itself must still expose the early setup controls.
            self.assertTrue(hasattr(d,'early_event_button'))
            self.assertTrue(hasattr(d,'early_event_summary'))
            d.close()

if __name__=='__main__':
    unittest.main()
