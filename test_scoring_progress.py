import unittest,tempfile
from pathlib import Path
from types import SimpleNamespace
from dataclasses import replace
from PySide6.QtWidgets import QApplication
from contest_rules import default_rule,score,score_steps,RuleStore
from contest_ui import ContestDialog
from model import QSO
from storage import Repository

class ProgressTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def test_chunked_scores_equal_normal_scores(self):
        r=default_rule();data=[dict(call=f'JA1A{i}',mode='CW',band='7',exchange='001') for i in range(1250)]
        work=score_steps(r,data);progress=[]
        while True:
            try:progress.append(next(work))
            except StopIteration as done:result=done.value;break
        self.assertEqual(progress,list(range(100,1201,100)));self.assertEqual(result,score(r,data))
    def setup_dialog(self,root):
        repo=Repository(root);r=default_rule();r['multi1']['kind']='off';path,_=RuleStore(root).save(r)
        d=ContestDialog(repo);self.addCleanup(d.deleteLater)
        q=QSO('2026-09-11','12:00','7','CW','JA1AAA','599','599','','','')
        d.selection=SimpleNamespace(rows=[('JH1HST',replace(q,call=f'JA1A{i}'),Path(root)/'sample.txt',i+1) for i in range(1250)],sessions=[])
        d.rules.setCurrentIndex(d.rules.findData(str(path)));d.timer.stop();return d,path
    def test_cancel_and_new_calculation(self):
        with tempfile.TemporaryDirectory() as root:
            d,path=self.setup_dialog(root);d.calculate();self.assertIsNotNone(d.score_job);self.assertIsNone(d.result)
            d.score_chunk();self.assertIn('100',d.result_label.text());d.schedule();self.assertIsNone(d.score_job);self.assertIsNone(d.result)
            d.timer.stop();d.calculate()
            for _ in range(14):d.score_chunk()
            self.assertIsNotNone(d.result);self.assertEqual(d.result.total,1250)
            d.cancel_score();d.timer.stop()
    def test_external_rule_change_discards_result(self):
        with tempfile.TemporaryDirectory() as root:
            d,path=self.setup_dialog(root);d.calculate();d.score_chunk();path.write_bytes(path.read_bytes()+b' ')
            for _ in range(14):d.score_chunk()
            self.assertIsNone(d.result);self.assertIn('集計できません',d.result_label.text());self.assertEqual(d.score_table.rowCount(),0)
