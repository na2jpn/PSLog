import tempfile,unittest
from model import QSO
from storage import Repository
from search import Criteria,search,hits_to_rows
from exporting import prepare_rows

class ExportSearchHandoffTests(unittest.TestCase):
    def test_exact_search_rows_are_exported_without_widening_to_whole_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=Repository(tmp);path=repo.path_for('JH1HST','','2026-01-01');session=repo.open(path)
            session.append(QSO('2026-01-01','00:01','7','CW','JA1AAA','599','599','Tokyo','Soka','POTA',''))
            session.append(QSO('2026-01-01','00:02','7','CW','JA1BBB','599','599','Osaka','Soka','OTHER',''))
            result=search(repo,Criteria(own='JH1HST',remarks='POTA'))
            self.assertEqual(len(result.hits),1)
            sessions,rows=hits_to_rows(result.hits)
            plan=prepare_rows(sessions,rows,'adx')
            self.assertEqual(len(plan.rows),1)
            self.assertEqual(plan.rows[0][1].call,'JA1AAA')
            self.assertIn(b'JA1AAA',plan.data)
            self.assertNotIn(b'JA1BBB',plan.data)

if __name__=='__main__':unittest.main()
