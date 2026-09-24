import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from dataclasses import replace
from model import QSO, default_rst
from storage import *

class StorageTests(unittest.TestCase):
    def test_same_content_metadata_change_is_not_external_change(self):
        import os
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'same.txt';p.write_bytes(b'abc')
            snap=Snapshot.read(p)
            st=p.stat()
            os.utime(p,ns=(st.st_atime_ns,st.st_mtime_ns+1000000))
            snap.check(p)

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.repo=Repository(self.tmp.name)
        self.q=QSO('2026-01-01','00:05','7','CW','JA1YYY','599','599','Japan','Soka Saitama Japan','BURO','')
        self.path=self.repo.path_for('JH1HST/1','','2026-01-01')
    def create(self):
        session=self.repo.open(self.path);session.append(self.q);return session
    def test_new_bytes_and_year(self):
        self.create();b=self.path.read_bytes()
        self.assertTrue(b.startswith(b'\xef\xbb\xbf'));self.assertTrue(b.endswith(b'\\\\\r\n'))
        self.assertEqual(len(b.decode('utf-8-sig').split('|')),11)
        self.assertEqual(self.path.name,'2026_JH1HST-1_.txt')
    def test_legacy_ten_columns_and_raw_preservation(self):
        line=self.q.to_ps();legacy=' | '.join(line[:-3].split(' | ')[:10])+' '+TERMINATOR+'\n'
        raw=('DATE | TIME | test\n\n'+legacy).encode()
        self.path.parent.mkdir();self.path.write_bytes(raw)
        s=self.repo.open(self.path);self.assertEqual(len(s.log.records),1)
        self.assertEqual(s.log.records[0][1].code,'');s.append(replace(self.q,time='00:06'))
        self.assertTrue(self.path.read_bytes().startswith(raw));self.assertNotIn(b'\r',self.path.read_bytes())
    def test_invalid_blocks_all_write(self):
        self.path.parent.mkdir();raw=(self.q.to_ps()+'\ninvalid\n').encode();self.path.write_bytes(raw)
        s=self.repo.open(self.path)
        with self.assertRaises(InvalidLog):s.append(self.q)
        self.assertEqual(raw,self.path.read_bytes())
    def test_snapshot_other_writer(self):
        s=self.create();other=self.repo.open(self.path);other.append(replace(self.q,time='00:06'))
        raw=self.path.read_bytes()
        with self.assertRaises(ExternalChange):s.append(self.q)
        self.assertEqual(raw,self.path.read_bytes())
    def test_same_size_same_mtime_changed_content(self):
        s=self.create();st=self.path.stat();data=self.path.read_bytes().replace(b'BURO',b'CARD');self.path.write_bytes(data)
        os.utime(self.path,ns=(st.st_atime_ns,st.st_mtime_ns))
        with self.assertRaises(ExternalChange):s.append(self.q)
    def test_new_destination_created_after_read(self):
        s=self.repo.open(self.path);self.path.parent.mkdir();self.path.write_bytes(b'other')
        with self.assertRaises(ExternalChange):s.append(self.q)
        self.assertEqual(self.path.read_bytes(),b'other')
    def test_backup_failure_keeps_original(self):
        s=self.create();before=self.path.read_bytes()
        with patch.object(self.repo,'backup',side_effect=OSError('disk full')):
            with self.assertRaises(OSError):s.edit(1,replace(self.q,remarks='hQSL.R'))
        self.assertEqual(before,self.path.read_bytes())
    def test_replace_failure_keeps_original_and_cleans_temp(self):
        s=self.create();before=self.path.read_bytes()
        with patch('storage.os.replace',side_effect=OSError('denied')):
            with self.assertRaises(OSError):s.edit(1,replace(self.q,remarks='hQSL.R'))
        self.assertEqual(before,self.path.read_bytes());self.assertFalse(list(self.path.parent.glob('.pslog-*')))
    def test_delete_restore_preserves_replaced_state(self):
        s=self.create();before=self.path.read_bytes();s.edit(1)
        deleted=self.path.read_bytes();bak=next(self.repo.bak.glob('*.bak'));s.restore(bak)
        self.assertEqual(before,self.path.read_bytes())
        self.assertIn(deleted,[p.read_bytes() for p in self.repo.bak.glob('*.bak')])
    def test_wrong_backup_rejected(self):
        s=self.create();wrong=Path(self.tmp.name)/'other.bak';wrong.write_bytes(b'')
        with self.assertRaises(StorageError):s.restore(wrong)
    def test_cross_year_edit_moves(self):
        s=self.create();before=self.path.read_bytes()
        target=s.edit(1,replace(self.q,date='2025-12-31'))
        self.assertEqual(len(self.repo.open(self.path).log.records),0)
        self.assertEqual(self.repo.open(target).log.records[0][1].date,'2025-12-31')
        self.assertEqual(self.repo.backups(self.path)[-1].read_bytes(),before)
    def test_retention_and_dedup(self):
        s=self.create()
        for i in range(35):s.edit(1,replace(self.q,remarks=str(i)))
        self.assertEqual(len(list(self.repo.bak.glob('*.bak'))),30)
        self.repo.close();n=len(list(self.repo.bak.glob('*.bak')));self.repo.close()
        self.assertEqual(n,len(list(self.repo.bak.glob('*.bak'))))
    def test_submodes_unknown_and_fullwidth(self):
        self.assertEqual(default_rst('FT8 AS'),'-01');self.assertEqual(default_rst('RTTY'),'599')
        self.assertEqual(default_rst('FT2'),'-01');self.assertEqual(default_rst('FreeDV'),'+00')
        q=replace(self.q,date='２０２６－０１－０１',time='００：０５',mode='NewMode',sent='任意',received='M 7');q.validate()
        self.assertEqual(q.time,'00:05')
    def test_plan_no_mutations_duplicates_and_years(self):
        src=Path(self.tmp.name)/'input.txt';src.write_text(self.q.to_ps()+'\n'+self.q.to_ps()+'\n'+replace(self.q,date='2025-12-31').to_ps())
        log,plans=import_plan(self.repo,src,'JH1HST')
        self.assertEqual(len(plans),2);self.assertEqual(sum(p['skipped'] for p in plans.values()),1)
        self.assertFalse(self.repo.book.exists())
    def test_station_scope(self):
        self.create()
        self.assertEqual(self.repo.files('JH1HST'),[])
        self.assertEqual(self.repo.files('JH1HST/1'),[self.path])
    def test_bad_dates_and_delimiters(self):
        for kw in [{'date':'2026-02-30'},{'time':'24:00'},{'remarks':'a|b'}]:
            with self.assertRaises(ValueError):replace(self.q,**kw).validate()

if __name__=='__main__':unittest.main()
