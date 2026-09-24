import shutil
import tempfile
import unittest
from pathlib import Path

from jccjcg_batch import (collect, prefecture_qth_from_rmks, MODE_CODE_TO_QTH,
    MODE_RMKS_TO_BOTH, MODE_RMKS_TO_PREF, MODE_QTH_TO_CODE, MODE_MISMATCH, MODE_LABELS)
from locations import load as load_locations
from model import QSO
from storage import Repository, VERSION

class Patch041064Tests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.root=Path(self.t.name)
        (self.root/'config/db').mkdir(parents=True);(self.root/'logbook').mkdir();(self.root/'bak').mkdir()
        here=Path(__file__).parent/'config/db'
        for name in ('locations.json','cty.dat','cty_meta.json'):shutil.copy2(here/name,self.root/'config/db'/name)
        self.repo=Repository(self.root);self.path=self.root/'logbook/2026_JH1HST_.txt'
    def tearDown(self):self.t.cleanup()
    def write(self,qsos):self.path.write_bytes(b'\xef\xbb\xbf'+(('\r\n'.join(q.to_ps() for q in qsos)+'\r\n').encode('utf-8')))
    def q(self,call='JA1AAA',his='Japan',code='',remarks=''):return QSO('2026-09-09','12:00','430','FM',call,'59','59',his,'Soka Saitama Japan',remarks,code)
    def test_version_and_labels_are_1064_a_to_e(self):
        self.assertEqual(VERSION,'1.14');modes=(MODE_CODE_TO_QTH,MODE_RMKS_TO_BOTH,MODE_RMKS_TO_PREF,MODE_QTH_TO_CODE,MODE_MISMATCH)
        self.assertEqual([MODE_LABELS[m][:3] for m in modes],['[A]','[B]','[C]','[D]','[E]'])
    def test_foreign_call_is_excluded_even_if_qth_blank_or_japan(self):
        self.write([self.q(call='HL1AAA',his='',code='1321'),self.q(call='K1ABC',his='Japan',code='1321')])
        self.assertEqual(collect(self.repo,[self.path],'JH1HST',MODE_CODE_TO_QTH,force=True),[])
    def test_force_a_and_b_allows_existing_domestic_qth(self):
        self.write([self.q(his='Tokyo Japan',code='1321')]);self.assertEqual(collect(self.repo,[self.path],'JH1HST',MODE_CODE_TO_QTH),[])
        rows=collect(self.repo,[self.path],'JH1HST',MODE_CODE_TO_QTH,force=True);self.assertEqual(len(rows),1);self.assertEqual(rows[0].proposal().his_qth,'Soka Saitama Japan')
        self.write([self.q(his='Tokyo Japan',remarks='1321')]);self.assertEqual(collect(self.repo,[self.path],'JH1HST',MODE_RMKS_TO_BOTH),[])
        rows=collect(self.repo,[self.path],'JH1HST',MODE_RMKS_TO_BOTH,force=True);self.assertEqual(len(rows),1);self.assertEqual(rows[0].proposal().code,'1321')
    def test_mode_c_uses_prefecture_number_and_does_not_touch_code(self):
        data=load_locations(self.root);self.assertEqual(prefecture_qth_from_rmks(data,'13'),'Saitama Japan');self.assertEqual(prefecture_qth_from_rmks(data,'130101'),'Saitama Japan')
        self.write([self.q(his='Japan',remarks='13')]);rows=collect(self.repo,[self.path],'JH1HST',MODE_RMKS_TO_PREF);self.assertEqual(len(rows),1);after=rows[0].proposal();self.assertEqual(after.his_qth,'Saitama Japan');self.assertEqual(after.code,'')
    def test_mode_c_supports_hokkaido_region_numbers(self):
        data=load_locations(self.root)
        self.assertEqual(prefecture_qth_from_rmks(data,'01'),'Hokkaido Japan')
        for code in ('101','102','103','104','105','106','107','108','109','110','111','112','113','114'):
            self.assertEqual(prefecture_qth_from_rmks(data,code),'Hokkaido Japan',code)
        self.write([self.q(his='Japan',remarks='106')]);rows=collect(self.repo,[self.path],'JH1HST',MODE_RMKS_TO_PREF);self.assertEqual(len(rows),1);after=rows[0].proposal();self.assertEqual(after.his_qth,'Hokkaido Japan');self.assertEqual(after.code,'')
    def test_mode_c_does_not_force_specific_qth(self):
        self.write([self.q(his='Tokyo Japan',remarks='13')]);self.assertEqual(collect(self.repo,[self.path],'JH1HST',MODE_RMKS_TO_PREF,force=True),[])
    def test_ui_sources_include_force_and_hide_final_next(self):
        root=Path(__file__).parent;batch=(root/'jccjcg_batch_ui.py').read_text(encoding='utf-8');self.assertIn('HIS QTHがJapanまたは空欄でなくても強制（[A][B]のみ）',batch);self.assertIn('MODE_RMKS_TO_PREF',batch)
        contest=(root/'contest_ui.py').read_text(encoding='utf-8');self.assertIn('self.next.setVisible(not final_stage)',contest)
if __name__=='__main__':unittest.main()
