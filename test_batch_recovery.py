import unittest,tempfile,json
from pathlib import Path
from dataclasses import replace
from unittest.mock import patch
from model import QSO
from storage import Repository,Snapshot,ExternalChange
from batch_recovery import create
import importing

class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.repo=Repository(self.tmp.name)
        self.q=QSO('2026-01-01','12:00','7','CW','JA1AAA','599','599','Japan','Soka Saitama Japan','BURO')
    def test_all_add_recovery_does_not_replay_import(self):
        source=Path(self.tmp.name)/'input.txt'
        source.write_text(self.q.to_ps()+'\n'+replace(self.q,date='2025-01-01').to_ps()+'\n')
        plan=importing.prepare(self.repo,source,'JH1HST',all_add=True)
        real=importing.replace_bytes
        def fail(path,*args):
            if path.name.startswith('2026_'):raise OSError('stop')
            return real(path,*args)
        with patch('importing.replace_bytes',side_effect=fail):
            with self.assertRaises(importing.ImportFailure):importing.commit(self.repo,plan)
        source.unlink() # Recovery must not depend on the input remaining available.
        repo=Repository(self.tmp.name);repo.recover();repo.recover()
        self.assertEqual(sum(len(repo.open(p).log.records) for p in repo.files('JH1HST')),2)
    def test_report_conflict_prevents_any_log_recovery(self):
        path=self.repo.path_for('JH1HST','',self.q.date)
        report=self.repo.bak/'result.csv';report.parent.mkdir(parents=True);report.write_bytes(b'initial')
        after=(self.q.to_ps()+'\r\n').encode()
        create(self.repo,'qsl',[(path,Snapshot(None,None),after)],{report:b'final'})
        report.write_bytes(b'user changed report')
        with self.assertRaises(ExternalChange):self.repo.recover()
        self.assertFalse(path.exists());self.assertEqual(report.read_bytes(),b'user changed report')
    def test_report_failure_after_logs_can_resume(self):
        path=self.repo.path_for('JH1HST','',self.q.date)
        report=self.repo.bak/'result.csv';report.parent.mkdir(parents=True);report.write_bytes(b'initial')
        after=(self.q.to_ps()+'\r\n').encode()
        create(self.repo,'qsl',[(path,Snapshot(None,None),after)],{report:b'final'})
        import batch_recovery
        real=batch_recovery.replace_bytes
        def fail(p,*args):
            if p==report:raise OSError('disk removed')
            return real(p,*args)
        with patch('batch_recovery.replace_bytes',side_effect=fail):
            with self.assertRaises(OSError):self.repo.recover()
        self.assertEqual(path.read_bytes(),after);self.assertEqual(report.read_bytes(),b'initial')
        self.repo.recover();self.assertEqual(report.read_bytes(),b'final')
