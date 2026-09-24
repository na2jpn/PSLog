import tempfile
import unittest
from pathlib import Path

from model import QSO
from search import Criteria, search
from storage import Repository, VERSION

ROOT=Path(__file__).resolve().parent


class Patch04Tests(unittest.TestCase):
    def test_version(self):
        self.assertEqual(VERSION,'1.14')

    def test_reset_window_flag_ignores_saved_geometry_at_restore(self):
        source=(ROOT/'main.py').read_text(encoding='utf-8')
        self.assertIn("Window(root,reset_window='--reset-window' in sys.argv)",source)
        self.assertIn("saved={} if self._reset_window_on_start else self.settings.get('window_geometry',{})",source)
        self.assertIn("if not self._reset_window_on_start and isinstance(saved,dict) and saved.get('maximized') is True",source)

    def test_search_edit_source_has_delete_and_rearranged_filter_groups(self):
        source=(ROOT/'search_ui.py').read_text(encoding='utf-8')
        self.assertIn("self.delete_button=button('この交信を削除',self.delete_record)",source)
        self.assertIn("'この交信を削除しますか？",source)
        self.assertIn("QLabel('対象ログファイル')",source)
        self.assertIn("button('参照…',self.browse_log_file)",source)
        self.assertIn("separator.setFrameShape(QFrame.Shape.VLine)",source)
        self.assertIn("QLabel('JCC/JCG')",source)
        self.assertIn("QLabel('MY QTH')",source)

    def test_single_hit_delete_removes_only_selected_original_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=Repository(tmp)
            session=repo.open(repo.path_for('JH1HST','TEST','2026-09-20'))
            q1=QSO('2026-09-20','10:00','7','CW','JA1AAA','599','599','Japan','Soka Saitama Japan','001','')
            q2=QSO('2026-09-20','10:01','7','CW','JA1BBB','599','599','Japan','Soka Saitama Japan','002','')
            session.append(q1);session.append(q2)
            result=search(repo,Criteria(own='JH1HST',filename=session.path.name,call='JA1AAA'))
            self.assertEqual(len(result.hits),1)
            result.hits[0].apply()
            reopened=repo.open(session.path)
            self.assertEqual([q.call for _,q in reopened.log.records],['JA1BBB'])
            self.assertTrue(repo.backups(session.path))

    def test_full_filename_filter_targets_one_log_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=Repository(tmp)
            q=QSO('2026-09-20','10:00','7','CW','JA1AAA','599','599','Japan','Soka Saitama Japan','001','')
            a=repo.path_for('JH1HST','A','2026-09-20');b=repo.path_for('JH1HST','B','2026-09-20')
            repo.open(a).append(q);repo.open(b).append(q)
            result=search(repo,Criteria(own='JH1HST',filename=a.name))
            self.assertEqual(result.files,1)
            self.assertEqual({hit.path.name for hit in result.hits},{a.name})


if __name__=='__main__':
    unittest.main()
