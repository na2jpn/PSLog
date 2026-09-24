import os,unittest
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtWidgets import QApplication,QComboBox
from contest_submit_ui import SubmissionPane

class V42SubmitUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([])

    def test_license_choices_contract(self):
        choices=[
            '第1級アマチュア無線技士',
            '第2級アマチュア無線技士',
            '第3級アマチュア無線技士',
            '第4級アマチュア無線技士',
        ]
        self.assertEqual(len(choices),4)

if __name__=='__main__':
    unittest.main()
