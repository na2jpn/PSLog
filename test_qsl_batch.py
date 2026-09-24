import csv,io,json,tempfile,unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
from model import QSO
from storage import Repository,ExternalChange,StorageError,parse
import qsl_batch as batch

class QSLTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.repo=Repository(self.root/'data');self.source=self.root/'input.txt';self.out=self.root/'results'
        self.q=QSO('2026-01-01','00:05','7','CW','JA1YYY','599','599','Adachi Tokyo Japan','Soka Saitama Japan','BURO','JCC 100121')
    def add(self,q=None,own='JH1HST'):
        q=q or self.q;p=self.repo.path_for(own,'',q.date);self.repo.open(p).append(q);return p
    def plan(self,text='2026-1-1 0:05 JA1YYY',method='BURO.R',zone='JST'):
        self.source.write_text(text,encoding='utf-8');return batch.prepare(self.repo,self.source,'JH1HST',zone,method)
    def csvrows(self,path):return list(csv.DictReader(io.StringIO(path.read_text(encoding='utf-8-sig'))))
    def test_parser_permutations_fullwidth_invalid_and_utc(self):
        text='2026-2-5 12:01 JA1YYY\n2026-09-10 1:02 YA1AAA\n10:12 2026/10/1 DL5TI\n2:05 2025-10-10 JA3TTT\nＪＡ１ＡＡＡ　２０２５/１０/１０　５：１０\n2026-02-30 1:01 JA1YYY\n\n2026-1-1 0:00 JA1YYY extra'
        rows=batch.read_entries(text.encode(),'JST','utf-8-sig');self.assertEqual(len(rows),8);self.assertTrue(all(r.stamp for r in rows[:5]));self.assertTrue(all(r.stamp is None for r in rows[5:]))
        self.assertEqual(batch.read_entries(b'2025-12-31 15:05 JA1YYY','UTC','utf-8-sig')[0].stamp.isoformat(),'2026-01-01T00:05:00')
        with self.assertRaises(StorageError):batch.read_entries(b'','', 'utf-8-sig')
    def test_nearby_window_allows_multiple_qsos_at_same_timestamp(self):
        self.add(self.q)
        self.add(replace(self.q,call='JA1ZZZ'))
        p=self.plan('2026-1-1 0:05 JA9XXX');e=p.entries[0]
        self.assertEqual(len(e.around),2)
        self.assertEqual({h.qso.call for h in e.around},{'JA1YYY','JA1ZZZ'})

    def test_boundaries_suffix_and_ambiguity(self):
        self.add(replace(self.q,date='2025-12-31',time='23:59'),own='JH1HST/1')
        self.add(replace(self.q,time='00:01'),own='JH1HST/P')
        self.add(replace(self.q,time='00:10'))
        self.add(replace(self.q,time='00:00'),own='JH1HSTX')
        p=self.plan('2026-1-1 0:00 JA1YYY');e=p.entries[0]
        self.assertEqual({h.own for h in e.candidates},{'JH1HST/1','JH1HST/P'});self.assertIsNone(e.pick)
        e.pick=0;self.assertEqual(batch.decisions(p)[0]['state'],'更新予定')
    def test_match_window_is_inclusive_five_minutes_and_reason_is_explicit(self):
        self.add(replace(self.q,time='10:00'))
        p=self.plan('2026-1-1 09:55 JA1YYY');self.assertEqual(len(p.entries[0].candidates),1);self.assertEqual(p.entries[0].pick,0)
        p=self.plan('2026-1-1 09:54 JA1YYY');self.assertEqual(p.entries[0].candidates,[]);self.assertIn('時刻差 +6分',p.entries[0].reason);self.assertIn('許容±5分超過',p.entries[0].reason)

    def test_markers_flags_card_and_boundaries(self):
        for before,first,buro in [('BURO',True,False),('BURO hQSL.R',False,False),('hQSL.R',False,True),('メモ',True,True),('BURO.R',False,False)]:
            after,f,b=batch.change(before,'BURO.R');self.assertEqual((f,b),(first,buro));self.assertEqual(after.count('BURO.R'),1)
        self.assertEqual(batch.change('CARD LoTW.R','CARD.R'),('CARD.R LoTW.R',False,False))
        self.assertEqual(batch.change('BURO BURO.R','BURO.R')[0],'BURO.R')
        self.assertEqual(batch.change('メモ (buro),hQSL.R; 11M','BURO.R'),('メモ (BURO.R),hQSL.R; 11M',False,False))
        for text in ['notBURO.R','BURO.Rなし','UNKNOWN.R','https://BURO.R','BURO.R/test']:
            self.assertTrue(batch.change(text,'eQSL.R')[1])
        self.assertTrue(replace(self.q,remarks='(lotw.r)').confirmed)
    def test_commit_results_dedup_all_fields_and_replay(self):
        dest=self.add(replace(self.q,remarks='メモ hQSL.R'));before=dest.read_bytes()
        plan=self.plan('2026-1-1 0:05 JA1YYY\nJA1YYY 2026/1/1 0:05\nbroken\n2026-1-1 0:05 JA9ZZZ\n')
        csvpath,journal,saved=batch.commit(self.repo,plan,self.out);rows=self.csvrows(csvpath)
        self.assertEqual(len(rows),4);self.assertEqual(rows[0]['初回QSL確認'],'0');self.assertEqual(rows[0]['BURO発送記録なし'],'1')
        self.assertEqual(rows[0]['MY_QTH'],'Soka Saitama Japan');self.assertEqual(rows[0]['JCCJCG'],'100121');self.assertEqual(rows[0]['更新状態'],'保存済み');self.assertEqual(rows[1]['重複元入力行'],'1')
        self.assertEqual(rows[2]['更新状態'],'更新対象外');self.assertTrue(Path(rows[0]['バックアップ']).read_bytes()==before)
        self.assertEqual(self.repo.open(dest).log.records[0][1].remarks,'メモ hQSL.R BURO.R')
        self.assertEqual(json.loads(journal.read_text(encoding='utf-8'))['status'],'完了')
        with self.assertRaises(StorageError):batch.commit(self.repo,plan,self.out)
        plan=self.plan();csvpath,_,saved=batch.commit(self.repo,plan,self.out);self.assertFalse(saved);self.assertEqual(self.csvrows(csvpath)[0]['照合状態'],'既受領スキップ')
    def test_only_rmks_changes_in_legacy_line(self):
        dest=self.add();raw=dest.read_bytes().removeprefix(b'\xef\xbb\xbf').replace(b'599',b'00').replace(b'\r\n',b'\n');dest.write_bytes(raw)
        batch.commit(self.repo,self.plan(),self.out)
        self.assertEqual(dest.read_bytes(),raw.replace(b'BURO',b'BURO.R'))
        # Older 10-column records retain structure and terminator too.
        raw=raw.replace(b' | JCC 100121',b'');dest.write_bytes(raw)
        batch.commit(self.repo,self.plan(),self.out);self.assertEqual(dest.read_bytes(),raw.replace(b'BURO',b'BURO.R'))
    def test_external_source_target_and_added_file(self):
        dest=self.add();p=self.plan();self.source.write_text('changed')
        with self.assertRaises(ExternalChange):batch.commit(self.repo,p,self.out)
        p=self.plan();dest.write_bytes(dest.read_bytes()+b'\n')
        with self.assertRaises(ExternalChange):batch.commit(self.repo,p,self.out)
        p=self.plan();self.add(own='JH1HST/P')
        with self.assertRaises(ExternalChange):batch.commit(self.repo,p,self.out)
    def test_result_failure_and_backup_failure_keep_original(self):
        dest=self.add();before=dest.read_bytes();real=batch.replace_bytes
        def fail_csv(path,*args):
            if path.name=='result.csv':raise OSError('CSV disk failure')
            return real(path,*args)
        with patch('qsl_batch.replace_bytes',side_effect=fail_csv):
            with self.assertRaises(batch.BatchFailure):batch.commit(self.repo,self.plan(),self.out)
        self.assertEqual(dest.read_bytes(),before)
        with patch.object(self.repo,'backup',side_effect=OSError('backup failure')):
            with self.assertRaises(batch.BatchFailure):batch.commit(self.repo,self.plan(),self.out)
        self.assertEqual(dest.read_bytes(),before)
    def test_partial_failure_reports_actual_status(self):
        old=self.add(replace(self.q,date='2025-12-30',time='23:58'));new=self.add()
        real=batch.replace_bytes
        def fail(path,*args):
            if path==new:raise OSError('write failure')
            return real(path,*args)
        with patch('qsl_batch.replace_bytes',side_effect=fail):
            with self.assertRaises(batch.BatchFailure) as err:batch.commit(self.repo,self.plan('2025-12-30 23:58 JA1YYY\n2026-1-1 0:05 JA1YYY'),self.out)
        rows=self.csvrows(err.exception.csv)
        self.assertEqual([r['更新状態'] for r in rows],['保存済み','未保存'])
        self.assertEqual(err.exception.saved,[old]);self.assertIn('BURO.R',old.read_text(encoding='utf-8'));self.assertNotIn('BURO.R',new.read_text(encoding='utf-8'))
        self.repo.recover();self.repo.recover()
        recovered=self.csvrows(err.exception.csv)
        self.assertEqual([r['更新状態'] for r in recovered],['保存済み','保存済み'])
        self.assertEqual([r['初回QSL確認'] for r in recovered],['1','1'])
        self.assertEqual(recovered[0]['MY_QTH'],'Soka Saitama Japan')
        self.assertIn('BURO.R',new.read_text(encoding='utf-8'))
    def test_post_save_csv_failure_stops_before_next_file(self):
        old=self.add(replace(self.q,date='2025-12-30',time='23:58'));new=self.add();real=batch.replace_bytes
        def fail(path,*args):
            if path.name=='result.csv' and b'BURO.R' in old.read_bytes():raise OSError('CSV unavailable after first save')
            return real(path,*args)
        with patch('qsl_batch.replace_bytes',side_effect=fail):
            with self.assertRaises(batch.BatchFailure) as err:batch.commit(self.repo,self.plan('2025-12-30 23:58 JA1YYY\n2026-1-1 0:05 JA1YYY'),self.out)
        rows=self.csvrows(err.exception.csv);self.assertEqual(rows[0]['更新状態'],'処理中・成否要確認')
        state=json.loads(err.exception.journal.read_text(encoding='utf-8'));self.assertEqual(state['files'][str(old)]['status'],'保存済み')
        self.assertNotIn('BURO.R',new.read_text(encoding='utf-8'))
