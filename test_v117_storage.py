"""External TXT edits must survive stale writers, retries and later QSOs."""
import os
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from model import QSO
from search import Criteria, search
from storage import ExternalChange, InvalidLog, Repository


class ExternalLog117Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.repo=Repository(self.tmp.name)
        self.q=QSO('2026-10-18','12:00','7','CW','JA1AAA','599','599','Japan','Chiba','1201')
        self.path=self.repo.path_for('JH1HST/1','CHIBA202610',self.q.date)

    def calls(self,path=None):
        return [q.call for _,q in self.repo.open(path or self.path).log.records]

    def test_manual_merge_delete_old_and_continue_after_reload(self):
        old=self.repo.path_for('JH1HST','CHIBA202610',self.q.date)
        self.repo.open(old).append(self.q)
        stale=self.repo.open(self.path);stale.append(replace(self.q,call='JA1BBB',time='12:01'))
        self.path.write_bytes(self.path.read_bytes()+old.read_bytes().removeprefix(b'\xef\xbb\xbf'))
        merged=self.path.read_bytes();old.unlink()
        hits=search(self.repo,Criteria('JH1HST',portable=True,filename=self.path.name)).hits
        self.assertEqual({h.qso.call for h in hits},{'JA1AAA','JA1BBB'})
        with self.assertRaises(ExternalChange):stale.append(replace(self.q,call='JA1CCC',time='12:02'))
        self.assertEqual(self.path.read_bytes(),merged)
        self.assertIn(merged,[p.read_bytes() for p in self.repo.backups(self.path)])
        fresh=self.repo.open(self.path)
        for i,call in enumerate(('JA1CCC','JA1DDD','JA1EEE'),2):fresh.append(replace(self.q,call=call,time=f'12:0{i}'))
        self.assertEqual(set(self.calls()),{'JA1AAA','JA1BBB','JA1CCC','JA1DDD','JA1EEE'})
        self.assertFalse(old.exists())

    def test_every_append_protects_current_disk_bytes(self):
        s=self.repo.open(self.path);s.append(self.q)
        for i in range(1,4):
            before=self.path.read_bytes();s.append(replace(self.q,time=f'12:0{i}'))
            self.assertEqual(self.repo.backups(self.path)[-1].read_bytes(),before)

    def test_external_same_size_and_timestamp_is_detected_and_backed_up(self):
        s=self.repo.open(self.path);s.append(self.q);stat=self.path.stat()
        external=self.path.read_bytes().replace(b'JA1AAA',b'JA1ZZZ');self.path.write_bytes(external)
        os.utime(self.path,ns=(stat.st_atime_ns,stat.st_mtime_ns))
        with self.assertRaises(ExternalChange):s.append(self.q)
        self.assertEqual(self.path.read_bytes(),external)
        self.assertEqual(self.repo.backups(self.path)[-1].read_bytes(),external)

    def test_new_file_arriving_after_missing_snapshot_is_not_overwritten(self):
        s=self.repo.open(self.path);self.path.parent.mkdir(parents=True)
        external=('\ufeff'+self.q.to_ps()+'\r\n').encode();self.path.write_bytes(external)
        with self.assertRaises(ExternalChange):s.append(replace(self.q,call='JA1BBB'))
        self.assertEqual(self.path.read_bytes(),external)

    def test_deleted_file_is_not_resurrected_by_stale_session(self):
        s=self.repo.open(self.path);s.append(self.q);self.path.unlink()
        with self.assertRaises(ExternalChange):s.append(replace(self.q,call='JA1BBB'))
        self.assertFalse(self.path.exists())
        self.repo.open(self.path).append(replace(self.q,call='JA1BBB'))
        self.assertEqual(self.calls(),['JA1BBB'])

    def test_invalid_external_bytes_are_preserved(self):
        s=self.repo.open(self.path);s.append(self.q)
        external=self.path.read_bytes()+b'broken external row\r\n';self.path.write_bytes(external)
        with self.assertRaises(ExternalChange):s.append(self.q)
        self.assertEqual(self.path.read_bytes(),external)
        with self.assertRaises(InvalidLog):self.repo.open(self.path).append(self.q)
        self.assertEqual(self.repo.backups(self.path)[-1].read_bytes(),external)

    def test_backup_failure_blocks_append_without_altering_log(self):
        s=self.repo.open(self.path);s.append(self.q);before=self.path.read_bytes()
        with patch.object(self.repo,'backup',side_effect=OSError('disk full')):
            with self.assertRaises(OSError):s.append(replace(self.q,call='JA1BBB'))
        self.assertEqual(self.path.read_bytes(),before)

    def test_external_change_during_windows_retry_is_preserved(self):
        s=self.repo.open(self.path);s.append(self.q)
        external=self.path.read_bytes()+replace(self.q,call='JA1ZZZ').to_ps().encode()+b'\r\n'
        with patch('storage.os.replace',side_effect=PermissionError('sharing')), \
             patch('storage.time.sleep',side_effect=lambda _:self.path.write_bytes(external)):
            with self.assertRaises(ExternalChange):s.append(replace(self.q,call='JA1BBB'))
        self.assertEqual(self.path.read_bytes(),external)
        self.assertEqual(self.repo.backups(self.path)[-1].read_bytes(),external)

    def test_external_change_between_backup_and_replace_is_preserved(self):
        s=self.repo.open(self.path);s.append(self.q)
        external=self.path.read_bytes()+replace(self.q,call='JA1ZZZ').to_ps().encode()+b'\r\n'
        backup=self.repo.backup;first=True
        def changed(path,data):
            nonlocal first
            result=backup(path,data)
            if first:first=False;path.write_bytes(external)
            return result
        with patch.object(self.repo,'backup',side_effect=changed):
            with self.assertRaises(ExternalChange):s.append(replace(self.q,call='JA1BBB'))
        self.assertEqual(self.path.read_bytes(),external)
        self.assertEqual(self.repo.backups(self.path)[-1].read_bytes(),external)

    def test_independent_repositories_cannot_lose_each_others_qsos(self):
        s=self.repo.open(self.path);s.append(self.q)
        other=Repository(self.tmp.name).open(self.path);other.append(replace(self.q,call='JA1BBB'))
        with self.assertRaises(ExternalChange):s.append(replace(self.q,call='JA1CCC'))
        self.assertEqual(self.calls(),['JA1AAA','JA1BBB'])


if __name__=='__main__':unittest.main()
