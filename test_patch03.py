import tempfile
import unittest
from pathlib import Path

from model import QSO
from search import session_rows,embedded_history_hit
from storage import Repository,VERSION

ROOT=Path(__file__).resolve().parent

class Patch03Tests(unittest.TestCase):
    def test_version(self):
        self.assertEqual(VERSION,'1.14')

    def test_rows_are_rebuilt_from_current_parsed_session_after_append(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=Repository(tmp);path=repo.path_for('JH1HST','', '2026-09-20');session=repo.open(path)
            a=QSO('2026-09-20','10:00','7','CW','JA1AAA','599','599','Japan','Soka Saitama Japan','001','')
            b=QSO('2026-09-20','10:01','7','CW','JA1BBB','599','599','Japan','Soka Saitama Japan','002','')
            session.append(a);rows=session_rows({path:session},'JH1HST');old=rows[0][1]
            session.append(b)
            current=[q for _,q in session.log.records]
            self.assertFalse(any(q is old for q in current))
            rows=session_rows({path:session},'JH1HST')
            self.assertEqual(len(rows),2)
            self.assertTrue(all(any(row_q is q for q in current) for _,row_q in rows))
            self.assertIsNotNone(embedded_history_hit({path:session},rows[0][0],rows[0][1]))

    def test_stale_history_reference_falls_back_only_when_unique(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=Repository(tmp);path=repo.path_for('JH1HST','TEST','2026-09-20');session=repo.open(path)
            q=QSO('2026-09-20','10:00','430','FM','JA1AAA','59','59','Japan','Soka Saitama Japan','001','')
            session.append(q);stale=q
            hit=embedded_history_hit({path:session},('JH1HST','TEST'),stale)
            self.assertIsNotNone(hit);self.assertEqual(hit.line,1)
            # Exact duplicate: stale value no longer uniquely identifies a line.
            session.append(QSO(**vars(q)))
            self.assertIsNone(embedded_history_hit({path:session},('JH1HST','TEST'),stale))

    def test_source_has_contest_empty_number_warning_and_new_default_size(self):
        main=(ROOT/'main.py').read_text(encoding='utf-8')
        geom=(ROOT/'window_geometry.py').read_text(encoding='utf-8')
        self.assertIn('コンテストナンバーが未入力ですが、このまま記録しますか？',main)
        self.assertIn('warning.setDefaultButton(QMessageBox.StandardButton.No)',main)
        self.assertIn('self.resize(1360, 850)',main)
        self.assertIn('default=(1360,850)',geom)

if __name__=='__main__':unittest.main()
