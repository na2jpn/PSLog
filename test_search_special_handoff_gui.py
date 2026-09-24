import tempfile,unittest
from PySide6.QtWidgets import QApplication
from model import QSO
from storage import Repository
from search import Criteria,search
from pota_ui import PotaDialog
from sota_ui import SotaDialog

class SearchSpecialHandoffGuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([])

    def make_hits(self,repo):
        path=repo.path_for('JH1HST','','2026-09-17')
        repo.open(path).append(QSO('2026-09-17','10:00','7','CW','JA1AAA','599','599','Tokyo','Soka','POTA TEST',''))
        return search(repo,Criteria(own='JH1HST',remarks='POTA')).hits

    def test_pota_search_handoff_is_visually_distinct_and_source_filters_hidden(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=Repository(tmp);hits=self.make_hits(repo)
            d=PotaDialog(repo,'JH1HST',hits=hits)
            self.assertTrue(d.source_panel.isHidden())
            self.assertIn('ログ検索結果を使用中',d.source_note.text())
            self.assertIn('#b00020',d.source_note.styleSheet())
            self.assertIn('ログ・期間・RMKSの再指定は行いません',d.source_note.text())
            d.close()

    def test_sota_search_handoff_is_visually_distinct_and_source_filters_hidden(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=Repository(tmp);hits=self.make_hits(repo)
            d=SotaDialog(repo,'JH1HST',hits=hits)
            self.assertTrue(d.source_panel.isHidden())
            self.assertIn('ログ検索結果を使用中',d.source_note.text())
            self.assertIn('#b00020',d.source_note.styleSheet())
            self.assertIn('ログ・期間・RMKSの再指定は行いません',d.source_note.text())
            d.close()

if __name__=='__main__':unittest.main()
