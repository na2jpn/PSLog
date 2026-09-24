import tempfile, unittest
from pathlib import Path

from model import QSO
from storage import Repository, StorageError, ExternalChange, parse
from log_merge import check, execute


def write_log(path, rows, bom=True, newline='\r\n'):
    text=newline.join(q.to_ps() for q in rows)
    if text:text+=newline
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes((b'\xef\xbb\xbf' if bom else b'')+text.encode('utf-8'))


class LogMergeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.repo=Repository(self.tmp.name);self.repo.book.mkdir(parents=True,exist_ok=True)
        self.target=self.repo.book/'2026_JH1HST_.txt'
        self.source=self.repo.book/'2026_JH1HST-1_CONTEST.txt'

    def q(self,date,time,call,remarks=''):
        return QSO(date,time,'7','CW',call,'599','599','Japan','Soka Saitama Japan',remarks,'')

    def test_check_execute_sorts_skips_duplicates_backs_up_and_deletes_source(self):
        target_rows=[self.q('2026-09-02','10:00','JA1BBB','target wins'),self.q('2026-09-01','10:00','JA1AAA')]
        source_rows=[self.q('2026-09-02','10:00','JA1BBB','source duplicate'),self.q('2026-08-31','09:00','JA1CCC')]
        write_log(self.target,target_rows,bom=True,newline='\r\n')
        write_log(self.source,source_rows,bom=False,newline='\n')
        plan=check(self.repo,self.target,self.source)
        self.assertEqual(plan.duplicate_skipped,1);self.assertEqual(plan.added_records,1);self.assertEqual(plan.merged_records,3)
        self.assertTrue(any('BOM' in w for w in plan.warnings));self.assertTrue(any('改行コード' in w for w in plan.warnings))
        result=execute(self.repo,plan)
        self.assertTrue(self.target.exists());self.assertFalse(self.source.exists())
        self.assertTrue(result.target_backup.exists());self.assertTrue(result.source_backup.exists())
        self.assertEqual(result.target_backup.parent,self.repo.bak/'logbook_bak')
        self.assertEqual(result.source_backup.parent,self.repo.bak/'logbook_bak')
        data=self.target.read_bytes();self.assertTrue(data.startswith(b'\xef\xbb\xbf'))
        log=parse(data);self.assertFalse(log.issues)
        rows=[q for _,q in log.records]
        self.assertEqual([(q.date,q.time,q.call) for q in rows],[
            ('2026-08-31','09:00','JA1CCC'),('2026-09-01','10:00','JA1AAA'),('2026-09-02','10:00','JA1BBB')])
        self.assertEqual(rows[-1].remarks,'target wins')

    def test_different_year_or_call_family_is_rejected(self):
        write_log(self.target,[self.q('2026-01-01','00:00','JA1AAA')])
        other_year=self.repo.book/'2027_JH1HST_.txt';write_log(other_year,[self.q('2027-01-01','00:00','JA1BBB')])
        with self.assertRaisesRegex(StorageError,'同じ年'):check(self.repo,self.target,other_year)
        other_call=self.repo.book/'2026_JA1XYZ_.txt';write_log(other_call,[self.q('2026-01-02','00:00','JA1BBB')])
        with self.assertRaisesRegex(StorageError,'同じ自局コールサイン系統'):check(self.repo,self.target,other_call)

    def test_record_year_mismatch_is_rejected(self):
        write_log(self.target,[self.q('2026-01-01','00:00','JA1AAA')])
        write_log(self.source,[self.q('2027-01-01','00:00','JA1BBB')])
        with self.assertRaisesRegex(StorageError,'ファイル年 2026 と異なるQSO'):check(self.repo,self.target,self.source)

    def test_invalid_utf8_and_notice_lines_are_rejected(self):
        write_log(self.target,[self.q('2026-01-01','00:00','JA1AAA')])
        self.source.write_bytes(b'\xff\xfe\x00')
        with self.assertRaisesRegex(StorageError,'UTF-8'):check(self.repo,self.target,self.source)
        self.source.write_text('DATE | TIME | BAND | MODE\r\n'+self.q('2026-01-02','00:00','JA1BBB').to_ps()+'\r\n',encoding='utf-8')
        with self.assertRaisesRegex(StorageError,'見出し・区切り行'):check(self.repo,self.target,self.source)

    def test_changed_after_check_requires_recheck_and_keeps_both_files(self):
        write_log(self.target,[self.q('2026-01-01','00:00','JA1AAA')])
        write_log(self.source,[self.q('2026-01-02','00:00','JA1BBB')])
        plan=check(self.repo,self.target,self.source)
        self.source.write_bytes(self.source.read_bytes()+b'\r\n')
        with self.assertRaises(ExternalChange):execute(self.repo,plan)
        self.assertTrue(self.target.exists());self.assertTrue(self.source.exists())
        self.assertFalse((self.repo.bak/'logbook_bak').exists())

    def test_same_source_and_empty_source_are_rejected(self):
        write_log(self.target,[self.q('2026-01-01','00:00','JA1AAA')])
        with self.assertRaisesRegex(StorageError,'同じファイル'):check(self.repo,self.target,self.target)
        self.source.write_bytes(b'\xef\xbb\xbf')
        with self.assertRaisesRegex(StorageError,'交信記録がありません'):check(self.repo,self.target,self.source)


if __name__=='__main__':unittest.main()
