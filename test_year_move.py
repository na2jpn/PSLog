import tempfile,unittest
from pathlib import Path
from dataclasses import replace
from unittest.mock import patch
from storage import Repository,StorageError,ExternalChange,replace_bytes,Snapshot
from model import QSO
from year_move import folder

class YearMoveTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.repo=Repository(self.tmp.name)
        self.q=QSO('2026-09-11','12:00','7','CW','JA1AAA','599','599','Japan','Soka Saitama Japan','BURO')
        self.path=self.repo.path_for('JH1HST/1','field',self.q.date)
        self.session=self.repo.open(self.path);self.session.append(self.q)
        self.target=self.repo.path_for('JH1HST/1','field','2025-09-11')
        self.original=self.path.read_bytes()
    def interrupt(self,after_write=False):
        def write(path,data,expected):
            if path==self.path:
                if after_write:replace_bytes(path,data,expected)
                raise OSError('simulated interruption')
            return replace_bytes(path,data,expected)
        with patch('year_move.replace_bytes',side_effect=write):
            with self.assertRaises(StorageError):self.session.edit(1,replace(self.q,date='2025-09-11'))
    def test_partial_commit_recovers_once_on_new_process(self):
        self.interrupt()
        self.assertEqual(self.path.read_bytes(),self.original)
        self.assertEqual(len(self.repo.open(self.target).log.records),1)
        other=Repository(self.tmp.name);other.recover();other.recover()
        self.assertEqual(len(other.open(self.path).log.records),0)
        self.assertEqual(len(other.open(self.target).log.records),1)
        self.assertFalse(list(folder(other.book).glob('*.pending.json')))
    def test_interruption_after_last_write_finishes_without_duplicate(self):
        self.interrupt(True);self.repo.recover()
        self.assertEqual(len(self.repo.open(self.target).log.records),1)
        self.assertEqual(len(self.repo.open(self.path).log.records),0)
    def test_conflict_stops_recovery_and_other_writes(self):
        self.interrupt();self.path.write_bytes(self.original+b'\r\n')
        before={p:p.read_bytes() for p in (self.path,self.target)}
        with self.assertRaises(ExternalChange):self.repo.recover()
        with self.assertRaises(ExternalChange):self.repo.open(self.target).append(replace(self.q,date='2025-09-11'))
        self.assertEqual(before,{p:p.read_bytes() for p in before})
    def test_existing_destination_and_unmodified_bytes(self):
        self.target.parent.mkdir(exist_ok=True)
        old=(replace(self.q,date='2025-01-01',call='JA2BBB').to_ps()+'\n').encode()
        self.target.write_bytes(old)
        self.session.edit(1,replace(self.q,date='2025-09-11'))
        self.assertTrue(self.target.read_bytes().startswith(old));self.assertFalse(self.target.read_bytes().startswith(b'\xef\xbb\xbf'))
        self.assertEqual(self.repo.backups(self.target)[-1].read_bytes(),old)
    def test_backup_failure_has_no_intent_or_log_change(self):
        with patch.object(self.repo,'backup',side_effect=OSError('full')):
            with self.assertRaises(OSError):self.session.edit(1,replace(self.q,date='2025-09-11'))
        self.assertEqual(self.original,self.path.read_bytes());self.assertFalse(self.target.exists())
        self.assertFalse(list(folder(self.repo.book).glob('*.pending.json')))
    def test_prewrite_interruption_is_recoverable(self):
        def write(path,data,expected):
            if path==self.target:raise OSError('stopped before first log')
            return replace_bytes(path,data,expected)
        with patch('year_move.replace_bytes',side_effect=write):
            with self.assertRaises(StorageError):self.session.edit(1,replace(self.q,date='2025-09-11'))
        self.assertFalse(self.target.exists());self.repo.recover()
        self.assertEqual(len(self.repo.open(self.target).log.records),1)
    def test_corrupt_journal_blocks_without_modifying_logs(self):
        self.interrupt();p=next(folder(self.repo.book).glob('*.pending.json'));p.write_text('{}')
        with self.assertRaises(StorageError):self.repo.recover()
        self.assertEqual(self.path.read_bytes(),self.original)
    def test_edit_screen_confirms_year_destination(self):
        from PySide6.QtWidgets import QApplication,QMessageBox
        from search import search,Criteria
        from search_ui import EditDialog
        app=QApplication.instance() or QApplication([])
        hit=search(self.repo,Criteria('JH1HST/1')).hits[0]
        dialog=EditDialog(hit);self.addCleanup(dialog.deleteLater)
        dialog.inputs['date'].setText('2025-09-11')
        with patch.object(QMessageBox,'question',return_value=QMessageBox.No):dialog.save()
        self.assertFalse(dialog.saved);self.assertFalse(self.target.exists())
        with patch.object(QMessageBox,'question',return_value=QMessageBox.Yes):dialog.save()
        self.assertTrue(dialog.saved);self.assertEqual(len(self.repo.open(self.target).log.records),1)
