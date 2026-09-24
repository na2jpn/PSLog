import json,tempfile,unittest
from dataclasses import replace
from pathlib import Path
from model import QSO
from storage import Repository,VERSION
from qsl_batch import prepare,commit,report_paths,call_difference

class Patch06V1066Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.repo=Repository(self.root/'data');self.source=self.root/'receive.txt';self.out=self.root/'results'
        self.base=QSO('2026-09-13','06:29','7','CW','JA7VTE','599','599','Japan','Soka Saitama Japan','hQSL','')
    def add(self,q=None):
        q=q or self.base;self.repo.open(self.repo.path_for('JH1HST','',q.date)).append(q)
    def plan(self,text,method='hQSL.R'):
        self.source.write_text(text,encoding='utf-8');return prepare(self.repo,self.source,'JH1HST','JST',method)

    def test_version(self):self.assertEqual(VERSION,'1.14')

    def test_nearby_clock_window_ignores_call_and_explains_call_difference(self):
        self.add(self.base)
        self.add(replace(self.base,time='06:31',call='JH7VTF'))
        p=self.plan('2026-09-13 06:29 JH7VTE');e=p.entries[0]
        self.assertFalse(e.candidates)
        self.assertEqual([(h.qso.time,h.qso.call) for h in e.around],[('06:29','JA7VTE'),('06:31','JH7VTF')])
        self.assertIn('プリフィックス差',call_difference('JH7VTE','JA7VTE'))
        self.assertIn('サフィックス差',call_difference('JH7VTE','JH7VTF'))
        self.assertIn('移動表記差',call_difference('JH7VTE','JH7VTE/7'))

    def test_result_report_and_reusable_unprocessed_txt(self):
        self.add(replace(self.base,call='JA1AAA',time='10:00',remarks='hQSL'))
        p=self.plan('2026-09-13 10:00 JA1AAA\n2026-09-13 10:03 JA1AAB\n')
        csv,journal,saved=commit(self.repo,p,self.out)
        result,unprocessed=report_paths(journal)
        self.assertTrue(result and result.exists());self.assertTrue(unprocessed and unprocessed.exists())
        text=result.read_text(encoding='utf-8-sig')
        self.assertIn('更新 1件',text);self.assertIn('未処理 1件',text)
        self.assertIn('入力時刻±3分のQSO',text)
        pending=unprocessed.read_text(encoding='utf-8-sig')
        self.assertEqual(pending,'2026-09-13 10:03 JA1AAB\n')
        state=json.loads(journal.read_text(encoding='utf-8'))
        self.assertEqual(state['report_counts']['unprocessed'],1)
        self.assertEqual(Path(state['result_report']),result)
        self.assertEqual(Path(state['unprocessed_report']),unprocessed)
        self.assertIn(self.source.stem+'_result_',result.name)
        self.assertIn(self.source.stem+'_unprocessed_',unprocessed.name)

    def test_no_unprocessed_file_when_every_input_is_handled(self):
        self.add(replace(self.base,call='JA1AAA',time='10:00',remarks='hQSL.R'))
        p=self.plan('2026-09-13 10:00 JA1AAA\n')
        _,journal,saved=commit(self.repo,p,self.out)
        self.assertFalse(saved)
        result,unprocessed=report_paths(journal)
        self.assertTrue(result.exists());self.assertIsNone(unprocessed)
        text=result.read_text(encoding='utf-8-sig')
        self.assertIn('未処理 0件',text);self.assertIn('未処理TXTは作成しません',text)

    def test_ui_source_has_final_result_screen_and_three_minute_investigation(self):
        text=Path('qsl_ui.py').read_text(encoding='utf-8')
        self.assertIn('class QSLResultDialog',text)
        self.assertIn('入力時刻±3分のQSO（コール違い確認用）',text)
        self.assertIn('結果レポート',text)
        self.assertIn('未処理（のこり）',text)
        self.assertIn('結果保存先',text)

if __name__=='__main__':unittest.main()
