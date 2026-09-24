import tempfile,unittest,json
from pathlib import Path
from dataclasses import replace
from unittest.mock import patch
from model import QSO
from storage import Repository,ExternalChange,InvalidLog,StorageError
from importing import prepare,commit,ImportFailure
import importing

class ImportTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.repo=Repository(self.root/'data');self.source=self.root/'source.txt'
        self.q=QSO('2026-01-01','00:05','7','CW','JA1YYY','599','599','Japan','Soka Saitama Japan','BURO','')
    def input(self,records=None,extra=''):
        self.source.write_text('\n'.join(q.to_ps() for q in (records or [self.q]))+'\n'+extra)
    def test_annual_duplicate_and_raw_source(self):
        old=replace(self.q,date='2025-12-31');self.input([old,self.q,self.q]);raw=self.source.read_bytes()
        p=prepare(self.repo,self.source,'JH1HST/1');report,saved=commit(self.repo,p)
        self.assertEqual(len(saved),2);self.assertEqual(sum(len(t['records']) for t in p.targets.values()),2)
        for dest in saved:self.assertTrue(dest.read_bytes().startswith(b'\xef\xbb\xbf'));self.assertIn(b'\r\n',dest.read_bytes())
        self.assertEqual(self.source.read_bytes(),raw);self.assertEqual(json.loads(report.read_text(encoding='utf-8'))['status'],'completed')
        p=prepare(self.repo,self.source,'JH1HST/1');self.assertEqual(sum(t['skipped'] for t in p.targets.values()),3)
        duplicates=[(q.date,q.time,q.call,reason) for t in p.targets.values() for q,reason in t['duplicates']]
        self.assertEqual(len(duplicates),3);self.assertTrue(all(reason=='既存ログ' for *_,reason in duplicates))
        p=prepare(self.repo,self.source,'JH1HST/1',all_add=True);self.assertEqual(sum(len(t['duplicates']) for t in p.targets.values()),3);commit(self.repo,p)
        self.assertEqual(sum(len(self.repo.open(s).log.records) for s in saved),5)
    def test_duplicate_detail_distinguishes_input_duplicate(self):
        self.input([self.q,self.q]);p=prepare(self.repo,self.source,'JH1HST')
        rows=[(q.call,reason) for t in p.targets.values() for q,reason in t['duplicates']]
        self.assertEqual(rows,[('JA1YYY','入力ファイル内')]);self.assertEqual(sum(t['skipped'] for t in p.targets.values()),1)
    def test_invalid_exclusion_and_operation_marker(self):
        self.input(extra='broken\n----2026 /JD1\n')
        p=prepare(self.repo,self.source,'JH1HST')
        with self.assertRaises(InvalidLog):commit(self.repo,p,True)
        p=prepare(self.repo,self.source,'JH1HST',exclude_invalid=True)
        with self.assertRaises(StorageError):commit(self.repo,p)
        report,_=commit(self.repo,p,True);self.assertEqual(json.loads(report.read_text(encoding='utf-8'))['excluded_lines'][0]['line'],2)
    def test_external_source_and_destination(self):
        self.input();p=prepare(self.repo,self.source,'JH1HST');self.source.write_bytes(self.source.read_bytes()+b'\n')
        with self.assertRaises(ExternalChange):commit(self.repo,p)
        p=prepare(self.repo,self.source,'JH1HST');dest=next(iter(p.targets));dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(b'other')
        with self.assertRaises(ExternalChange):commit(self.repo,p)
        self.assertEqual(dest.read_bytes(),b'other')
    def test_partial_failure_report_and_retry_default(self):
        self.input([replace(self.q,date='2025-12-31'),self.q]);p=prepare(self.repo,self.source,'JH1HST')
        real=importing.replace_bytes
        def fail(path,*args):
            if path.name.startswith('2026_'):raise OSError('disk error')
            return real(path,*args)
        with patch('importing.replace_bytes',side_effect=fail):
            with self.assertRaises(ImportFailure) as error:commit(self.repo,p)
        e=error.exception;self.assertEqual(len(e.saved),1)
        state=json.loads(e.report.read_text(encoding='utf-8'));self.assertEqual([f['status'] for f in state['files']],['saved','attempting'])
        p=prepare(self.repo,self.source,'JH1HST');self.assertEqual(sum(t['skipped'] for t in p.targets.values()),1)
        self.repo.recover();self.repo.recover()
        self.assertEqual(sum(len(self.repo.open(f).log.records) for f in self.repo.files('JH1HST')),2)
        self.assertEqual(json.loads(e.report.read_text(encoding='utf-8'))['status'],'completed')
    def test_legacy_rst_and_existing_bytes_preserved(self):
        self.input();self.source.write_text(self.source.read_text(encoding='utf-8').replace('599','00'))
        p=prepare(self.repo,self.source,'JH1HST');dest=next(iter(p.targets))
        dest.parent.mkdir(parents=True,exist_ok=True);raw=(self.q.to_ps()+'\n').encode();dest.write_bytes(raw)
        p=prepare(self.repo,self.source,'JH1HST',all_add=True);commit(self.repo,p)
        self.assertTrue(dest.read_bytes().startswith(raw));self.assertEqual(self.repo.open(dest).log.records[-1][1].sent,'00')
    def test_backup_failure_before_any_replacement(self):
        self.input([replace(self.q,date='2025-12-31'),self.q]);p=prepare(self.repo,self.source,'JH1HST')
        with patch.object(self.repo,'backup',side_effect=OSError('backup failed')):
            with self.assertRaises(ImportFailure):commit(self.repo,p)
        self.assertFalse(list(self.repo.book.glob('*.txt')))
    def test_duplicate_qsl_markers_merge_into_existing_without_replacing_notes(self):
        existing=replace(self.q,remarks='memo BURO')
        dest=self.repo.path_for('JH1HST','',existing.date);self.repo.open(dest).append(existing)
        incoming=replace(self.q,remarks='other BURO.R hQSL.R');self.input([incoming])
        p=prepare(self.repo,self.source,'JH1HST')
        self.assertEqual(sum(t['skipped'] for t in p.targets.values()),1)
        self.assertEqual(sum(len(t['merges']) for t in p.targets.values()),1)
        report,saved=commit(self.repo,p);self.assertEqual(saved,[dest])
        q=self.repo.open(dest).log.records[0][1]
        self.assertIn('memo',q.remarks);self.assertIn('BURO.R',q.remarks);self.assertIn('hQSL.R',q.remarks)
        self.assertNotIn('other',q.remarks)
        state=json.loads(report.read_text(encoding='utf-8'));self.assertEqual(state['files'][0]['qsl_merged'],1)

    def test_duplicate_qsl_merge_can_be_only_action(self):
        dest=self.repo.path_for('JH1HST','',self.q.date);self.repo.open(dest).append(replace(self.q,remarks='memo'))
        self.input([replace(self.q,remarks='LoTW.R')]);p=prepare(self.repo,self.source,'JH1HST')
        self.assertEqual(sum(len(t['records']) for t in p.targets.values()),0)
        _,saved=commit(self.repo,p);self.assertEqual(saved,[dest]);self.assertIn('LoTW.R',self.repo.open(dest).log.records[0][1].remarks)

    def test_input_duplicate_qsl_is_folded_into_first_added_record(self):
        self.input([replace(self.q,remarks='BURO'),replace(self.q,remarks='BURO.R hQSL.R')])
        p=prepare(self.repo,self.source,'JH1HST');records=[q for t in p.targets.values() for q in t['records']]
        self.assertEqual(len(records),1);self.assertIn('BURO.R',records[0].remarks);self.assertIn('hQSL.R',records[0].remarks)
        commit(self.repo,p);q=self.repo.open(next(iter(p.targets))).log.records[0][1]
        self.assertIn('BURO.R',q.remarks);self.assertIn('hQSL.R',q.remarks)

