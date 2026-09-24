import shutil
import tempfile
import unittest
from pathlib import Path

import jccjcg_batch
from contest_overview import _humanize_portable_sentence
from contest_rules import default_rule, score
from contest_scoring_v2 import steps as scoring_v2_steps
from jccjcg_batch import collect, MODE_CODE_TO_QTH
from model import QSO
from storage import Repository, VERSION


class Patch031063Tests(unittest.TestCase):
    def test_version_is_1063(self):
        self.assertEqual(VERSION, '1.14')

    def test_jccjcg_no_date_uses_latest_limit_but_explicit_date_does_not(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/'config/db').mkdir(parents=True);(root/'logbook').mkdir();(root/'bak').mkdir()
            shutil.copy2(Path(__file__).parent/'config/db/locations.json', root/'config/db/locations.json')
            repo=Repository(root);path=root/'logbook/2026_JH1HST_.txt'
            qsos=[QSO('2026-09-09',f'12:0{i}','430','FM',f'JA1A{i:02d}','59','59','Japan','Soka Saitama Japan','', '1321') for i in range(5)]
            path.write_bytes(b'\xef\xbb\xbf'+(('\r\n'.join(q.to_ps() for q in qsos)+'\r\n').encode('utf-8')))
            old=jccjcg_batch.DEFAULT_RECENT_LIMIT
            try:
                jccjcg_batch.DEFAULT_RECENT_LIMIT=3
                recent=collect(repo,[path],'JH1HST',MODE_CODE_TO_QTH)
                self.assertEqual([c.qso.time for c in recent],['12:02','12:03','12:04'])
                ranged=collect(repo,[path],'JH1HST',MODE_CODE_TO_QTH,'20260909','20260909')
                self.assertEqual(len(ranged),5)
            finally:
                jccjcg_batch.DEFAULT_RECENT_LIMIT=old
        self.assertEqual(jccjcg_batch.DEFAULT_RECENT_LIMIT,2000)

    def test_legacy_multiplier_marks_new_then_existing_per_band(self):
        rule=default_rule();rule['multi1']['kind']='whole';rule['multi1']['per_band']=True
        entries=[
            {'call':'JA1AAA','band':'7','mode':'CW','exchange':'11'},
            {'call':'JA1AAB','band':'7','mode':'CW','exchange':'11'},
            {'call':'JA1AAC','band':'14','mode':'CW','exchange':'11'},
        ]
        result=score(rule,entries)
        self.assertEqual(result.multi1,2)
        self.assertEqual([r.get('multiplier_judgement') for r in result.rows],['新規','既出','新規'])

    def test_schema2_multiplier_marks_new_then_existing_per_band(self):
        rule={
            'scoring':{'eligible':{'all':[]},'multipliers':[{'id':'region','source':'area','kind':'whole','start':0,'length':2,'per_band':True,'when':{'all':[]}}],'bonus':0},
            'points':{'phone':1,'cw':1,'digital':1},'conditions':[],
            'duplicate':{'enabled':True,'by_mode':False},
            'multi2':{'kind':'off','value':1,'condition':{'all':[]}},'formula':'total',
        }
        entries=[
            {'call':'JA1AAA','band':'7','mode':'CW','exchange':'11','area':'11'},
            {'call':'JA1AAB','band':'7','mode':'CW','exchange':'11','area':'11'},
            {'call':'JA1AAC','band':'14','mode':'CW','exchange':'11','area':'11'},
        ]
        work=scoring_v2_steps(rule,entries)
        while True:
            try:next(work)
            except StopIteration as done:
                result=done.value;break
        self.assertEqual(result.multi1,2)
        self.assertEqual([r.get('multiplier_judgement') for r in result.rows],['新規','既出','新規'])

    def test_portable_rule_display_humanizes_so_internal_wording(self):
        raw='SO移動の例外以外は場所を変更していない'
        text=_humanize_portable_sentence(raw)
        self.assertNotIn('SO移動',text)
        self.assertIn('シングルオペ',text)
        self.assertIn('運用場所',text)

    def test_ui_sources_have_requested_patch03_layout_and_labels(self):
        root=Path(__file__).parent
        batch=(root/'jccjcg_batch_ui.py').read_text(encoding='utf-8')
        self.assertIn('最新2,000QSO',batch)
        self.assertIn('confirm_row.addStretch(1);confirm_row.addWidget(self.confirmed)',batch)
        score_ui=(root/'contest_score_ui.py').read_text(encoding='utf-8')
        self.assertIn("'マルチ判定'",score_ui)


if __name__=='__main__':
    unittest.main()
