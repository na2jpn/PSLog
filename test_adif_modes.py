import unittest,tempfile
from dataclasses import replace
from model import QSO
from storage import Repository
from exporting import adif,adif_fields
from adif_import import convert
from test_adif_import import adi,BASE
import pota_export


class AdifModeTests(unittest.TestCase):
    def setUp(self):
        self.q=QSO('2026-09-11','12:00','7','FT2 AS','JA1YYY','-01','+00','PM95','Japan','','')

    def test_ft2_roundtrip_both_formats(self):
        for adx in (False,True):
            data,warnings=adif([('JH1HST',self.q,None,1)],adx)
            self.assertIn(b'3.1.7',data);self.assertTrue(warnings)
            log,_=convert(data,'adx' if adx else 'adi','JH1HST')
            self.assertFalse(log.issues)
            self.assertEqual(log.records[0][1].mode,'FT2 AS')

    def test_additional_known_modes_and_ambiguous_labels(self):
        for mode,parent in [('Q65','MFSK'),('JS8','MFSK'),('M17','DIGITALVOICE'),('JT65B','JT65'),('PSK63','PSK'),('FREEDATA','DYNAMIC')]:
            f=adif_fields('JH1HST',replace(self.q,mode=mode),set())
            self.assertEqual((f['MODE'],f['SUBMODE']),(parent,mode))
        with self.assertRaises(ValueError):adif_fields('JH1HST',replace(self.q,mode='FT8 FT4'),set())
        f=adif_fields('JH1HST',replace(self.q,mode='VARA HF AS'),set())
        self.assertEqual((f['MODE'],f['SUBMODE'],f['APP_PSLOG_MODE']),('DYNAMIC','VARA HF','VARA HF AS'))

    def test_known_conflicts_and_unknown_preservation(self):
        for mode,sub in [('SSB','FT2'),('MFSK','USB'),('FT4','FT2')]:
            log,_=convert(adi(**(BASE|{'MODE':mode,'SUBMODE':sub})),'adi','JH1HST/1')
            self.assertTrue(log.issues)
        log,_=convert(adi(**(BASE|{'MODE':'FUTURE','SUBMODE':'FUTURE2'})),'adi','JH1HST/1')
        self.assertFalse(log.issues)
        q=log.records[0][1]
        self.assertEqual(q.mode,'FUTURE2')
        self.assertIn('"MODE":"FUTURE"',q.remarks)

    def test_pota_ft2_header_and_standard_fields(self):
        with tempfile.TemporaryDirectory() as root:
            repo=Repository(root);path=repo.path_for('JH1HST','',self.q.date)
            repo.open(path).append(self.q)
            plan=pota_export.prepare(repo,[path],'JH1HST','JH1HST','JH1HST','JA-1222')
            data=next(iter(plan.files.values()))
            self.assertIn(b'<ADIF_VER:5>3.1.7',data)
            self.assertIn(b'<SUBMODE:3>FT2',data)
            self.assertIn(b'<MODE:4>MFSK',data)
