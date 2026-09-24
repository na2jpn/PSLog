import os,tempfile,unittest
from pathlib import Path

from storage import Repository,VERSION,save_settings
from jccjcg_award_check import LocationStatus,PrefectureStatus,STATE_NONE,STATE_WORKED,STATE_QSL


class Patch051075CoreTests(unittest.TestCase):
    def test_version(self):
        self.assertEqual(VERSION,'1.14')

    @staticmethod
    def loc(kind,code,state):
        return LocationStatus(kind,code,code,'11','神奈川県',{'7':state,'*':state})

    def test_folded_badges_hide_worked_when_qsl_complete(self):
        pref=PrefectureStatus('11','神奈川県',(
            self.loc('JCC','1101',STATE_QSL),
            self.loc('JCC','1102',STATE_QSL),
            self.loc('JCG','11001',STATE_WORKED),
            self.loc('JCG','11002',STATE_WORKED),
        ))
        self.assertEqual(pref.badges(),['全JCC-QSL済','全JCG-交信済'])
        self.assertNotIn('全JCC-交信済',pref.folded_summary())

    def test_cfm_remaining_counts_unworked_and_worked_unconfirmed(self):
        pref=PrefectureStatus('11','神奈川県',(
            self.loc('JCC','1101',STATE_QSL),
            self.loc('JCC','1102',STATE_WORKED),
            self.loc('JCC','1103',STATE_NONE),
            self.loc('JCG','11001',STATE_QSL),
            self.loc('JCG','11002',STATE_WORKED),
        ))
        self.assertEqual(pref.cfm_remaining(),(('JCC',2),('JCG',1)))
        self.assertEqual(pref.folded_summary(),'全JCG-交信済　（CFM 残JCC 2　残JCG 1）')

    def test_cfm_summary_omits_zero_and_absent_kind(self):
        only_jcc=PrefectureStatus('10','東京都',(self.loc('JCC','1001',STATE_QSL),))
        self.assertEqual(only_jcc.folded_summary(),'全JCC-QSL済')
        mixed=PrefectureStatus('11','神奈川県',(
            self.loc('JCC','1101',STATE_QSL),
            self.loc('JCG','11001',STATE_WORKED),
        ))
        self.assertEqual(mixed.folded_summary(),'全JCC-QSL済　全JCG-交信済　（CFM 残JCG 1）')

    def test_main_source_has_bold_callsign_controls(self):
        text=Path(__file__).with_name('main.py').read_text(encoding='utf-8')
        self.assertIn("self.call_label=QLabel('相手コールサイン')",text)
        self.assertIn('call_label_font.setBold(True)',text)
        self.assertIn('call_font.setBold(True)',text)
        self.assertIn("self.c_call_label=QLabel('相手コールサイン')",text)
        self.assertIn('c_call_label_font.setBold(True)',text)
        self.assertIn('c_call_font.setBold(True)',text)


try:
    import PySide6  # noqa: F401
    HAVE_QT=True
except Exception:
    HAVE_QT=False

@unittest.skipUnless(HAVE_QT,'PySide6 not installed')
class Patch051075GuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
        from PySide6.QtWidgets import QApplication
        cls.app=QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.repo=Repository(Path(self.tmp.name))

    def test_standard_and_contest_callsign_labels_and_inputs_are_bold(self):
        from main import Window
        # Avoid scheduling the real first-start QInputDialog in the GUI test.
        # With an empty temporary data root, Window() intentionally schedules
        # first_start() via QTimer.singleShot(0, ...).  Under Qt's offscreen
        # test platform that modal dialog is invisible and can leave the suite
        # waiting indefinitely while the main clock timer continues to tick.
        save_settings(self.tmp.name,{'own':'JH1HST'})
        w=Window(self.tmp.name)
        self.assertTrue(w.call_label.font().bold());self.assertTrue(w.call.font().bold())
        self.assertTrue(w.c_call_label.font().bold());self.assertTrue(w.c_call.font().bold())
        w.close()


if __name__=='__main__':unittest.main()
