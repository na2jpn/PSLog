import tempfile,unittest
from pathlib import Path
from dataclasses import replace
from unittest.mock import patch
from model import QSO
from storage import Repository,ExternalChange,StorageError
from adif_import import read_adi
import pota_export as pota

class PotaTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.repo=Repository(self.tmp.name);self.q=QSO('2026-01-01','08:59','7','FT4','JA1YYY','-01','+00','足立区','草加市','POTA 日本語メモ','JCC 100121')
        self.path=self.repo.path_for('JH1HST/1','',self.q.date);self.repo.open(self.path).append(self.q)
    def plan(self,**kwargs):
        args=dict(repo=self.repo,paths=[self.path],source_own='JH1HST/1',station='JH1HST/1',operator='JH1HST',parks='JA-1222');args.update(kwargs);return pota.prepare(**args)
    def test_twofer_utc_dates_and_tag_lengths(self):
        self.repo.open(self.path).append(replace(self.q,time='09:00',call='JA2YYY'));raw=self.path.read_bytes()
        p=self.plan(parks='JA-1222, JP-12345',my_state='JP-11');self.assertEqual(len(p.files),4);self.assertEqual(p.qsos,2)
        values={}
        for name,data in p.files.items():
            records=read_adi(data);self.assertEqual(len(records),1);r=records[0];values[name]=r
            self.assertEqual(r['STATION_CALLSIGN'],'JH1HST/1');self.assertEqual(r['OPERATOR'],'JH1HST');self.assertEqual(r['MY_SIG'],'POTA');self.assertEqual(r['MY_STATE'],'JP-11')
            self.assertEqual(r['MODE'],'MFSK');self.assertEqual(r['SUBMODE'],'FT4');self.assertNotIn('FREQ',r);self.assertNotIn('COMMENT',r);self.assertNotIn('SIG_INFO',r)
        for park in ['JA-1222','JP-12345']:
            self.assertEqual(values[f'JH1HST-1@{park}-20251231.adi']['TIME_ON'],'235900');self.assertEqual(values[f'JH1HST-1@{park}-20260101.adi']['TIME_ON'],'000000')
        self.assertEqual(raw,self.path.read_bytes())
    def test_exact_preselected_rows_do_not_expand_to_whole_file(self):
        other=replace(self.q,time='09:00',call='JA2YYY',remarks='OTHER')
        self.repo.open(self.path).append(other)
        session=self.repo.open(self.path);rows=[('JH1HST/1',self.q,self.path,1)]
        p=pota.prepare_selected([session],rows,'JH1HST/1','JH1HST/1','JH1HST','JA-1222')
        self.assertEqual(p.qsos,1)
        records=read_adi(next(iter(p.files.values())))
        self.assertEqual([r['CALL'] for r in records],['JA1YYY'])
    def test_period_and_rmks_and_mode_family(self):
        self.repo.open(self.path).append(replace(self.q,time='09:00',mode='FT8 AS',remarks='pota 公園'))
        p=self.plan(start='20260101090000',end='20260101090000',remarks='POTA')
        self.assertEqual(p.qsos,1);r=read_adi(next(iter(p.files.values())))[0];self.assertEqual(r['MODE'],'FT8');self.assertTrue(p.warnings)
        with self.assertRaises(ValueError):self.plan(remarks='no match')
        with self.assertRaises(ValueError):self.plan(start='20260101090000',end='20260101080000')
    def test_direct_prepare_keeps_submission_validation_before_empty_selection(self):
        with self.assertRaisesRegex(ValueError,'公園番号'):
            pota.prepare(self.repo,[], 'JH1HST/1','JH1HST/1','JH1HST','')

    def test_validation_before_writes(self):
        for parks in ['', 'JA1222','JA-1222 JA-1222','../JA-1222']:
            with self.assertRaises(ValueError):self.plan(parks=parks)
        self.assertEqual(pota.park_numbers('ｊａ－１２２２'),['JA-1222'])
        with self.assertRaises(ValueError):self.plan(operator='')
        with self.assertRaises(ValueError):self.plan(source_own='JH1HST')
        self.repo.open(self.path).edit(1,replace(self.q,mode='UNKNOWN'))
        with self.assertRaises(ValueError):self.plan()
        self.assertFalse(list(Path(self.tmp.name).glob('*.adi')))
    def test_save_collision_external_change_and_source_unchanged(self):
        p=self.plan();raw=self.path.read_bytes();a=pota.save(p,self.tmp.name);b=pota.save(p,self.tmp.name)
        self.assertNotEqual(a,b);self.assertTrue(b[0].stem.endswith('_001'));self.assertEqual(a[0].read_bytes(),b[0].read_bytes());self.assertEqual(self.path.read_bytes(),raw)
        self.path.write_bytes(raw+b'\n')
        with self.assertRaises(ExternalChange):pota.save(p,self.tmp.name)
    def test_partial_output_failure_reports_created_files(self):
        p=self.plan(parks='JA-1222 JA-1234');real=pota.replace_bytes
        def fail(path,*args):
            if 'JA-1234' in path.name:raise OSError('disk error')
            return real(path,*args)
        raw=self.path.read_bytes()
        with patch('pota_export.replace_bytes',side_effect=fail):
            with self.assertRaises(pota.PotaSaveFailure) as err:pota.save(p,self.tmp.name)
        self.assertEqual(len(err.exception.saved),1);self.assertEqual(self.path.read_bytes(),raw)
