import tempfile
import unittest
from pathlib import Path

from contest import select_logs
from contest_export import key, plan
from contest_rules import default_rule
from model import QSO
from storage import Repository, VERSION
from contest_club import submission_info


class V104InitialRegressionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Repository(self.tmp.name)
        self.q = QSO('2026-09-17','12:00','1200','FM','JA1AAA','59','59','Japan','Tokyo Japan','001A','')
        self.path = self.repo.path_for('JH1HST','',self.q.date)
        self.repo.open(self.path).append(self.q)
        self.selection = select_logs(self.repo,[self.path],'JH1HST')
        self.rule = default_rule()
        self.draft = {key(self.selection.rows[0]): {'sent':'09009','received':'001A','status':'確認済み'}}
        self.info = dict(contest='TEST',category='X',name='Test',address='Japan',power='5',date='2026-09-17',signature='Test',oath=True,licenseclass='第2級アマチュア無線技士')

    def test_version_and_default_contest_output_path(self):
        self.assertEqual(VERSION,'1.14')
        self.assertEqual(self.repo.contest_output,Path(self.tmp.name).resolve()/'output'/'contest')
        self.assertEqual(self.repo.export_output,Path(self.tmp.name).resolve()/'output'/'export')
        self.assertEqual(self.repo.pota_output,Path(self.tmp.name).resolve()/'output'/'pota')
        self.assertEqual(self.repo.sota_output,Path(self.tmp.name).resolve()/'output'/'sota')

    def test_editable_submission_callsign_changes_jarl_only(self):
        info=dict(self.info,callsign='JH1HST/0')
        p=plan(self.selection,self.rule,self.draft,'JARL R1.0',info)
        text=p.preview()
        self.assertIn('<CALLSIGN>JH1HST/0</CALLSIGN>',text)
        self.assertEqual(p.filename,'JH1HST-0.txt')
        self.assertEqual(self.selection.rows[0][0],'JH1HST')

    def test_club_eligibility_mismatch_is_not_a_submission_error(self):
        spec={'prefix':'12-','station_types':['individual']}
        info={'clubnumber':'13-01-01','clubname':'毎回記載するクラブ'}
        self.assertEqual(submission_info(spec,{'station_type':'individual'},info),info)
        self.assertEqual(submission_info(spec,{'station_type':'club'},info),info)


if __name__=='__main__':
    unittest.main()
