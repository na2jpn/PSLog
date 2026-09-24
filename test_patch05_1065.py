import tempfile,unittest
from dataclasses import replace
from pathlib import Path
from model import QSO
from qsl_marks import change,buro_judgement
from storage import Repository,VERSION
from qsl_batch import prepare,decisions

class Patch05V1065Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.repo=Repository(self.root/'data');self.source=self.root/'receive.txt'
        self.q=QSO('2026-09-21','10:00','7','CW','JA1AAA','599','599','Japan','Soka Saitama Japan','memo','')
    def add(self,q=None):
        q=q or self.q;self.repo.open(self.repo.path_for('JH1HST','',q.date)).append(q)
    def plan(self,line,method='hQSL.R'):
        self.source.write_text(line,encoding='utf-8');return prepare(self.repo,self.source,'JH1HST','JST',method)
    def test_version(self):self.assertEqual(VERSION,'1.14')
    def test_five_minute_window_and_six_minute_reason(self):
        self.add();p=self.plan('2026-09-21 09:55 JA1AAA');self.assertEqual(p.entries[0].pick,0)
        p=self.plan('2026-09-21 09:54 JA1AAA');self.assertIsNone(p.entries[0].pick);self.assertIn('許容±5分超過',p.entries[0].reason)
    def test_multiple_within_window_is_not_auto_selected(self):
        self.add(replace(self.q,time='10:01'));self.add(replace(self.q,time='10:04'))
        p=self.plan('2026-09-21 10:02 JA1AAA');self.assertEqual(len(p.entries[0].candidates),2);self.assertIsNone(p.entries[0].pick);self.assertEqual(decisions(p)[0]['state'],'複数候補')
    def test_existing_receipt_is_skip(self):
        self.add(replace(self.q,remarks='memo hQSL.R'));p=self.plan('2026-09-21 10:00 JA1AAA');r=decisions(p)[0]
        self.assertEqual(r['state'],'既受領スキップ');self.assertIn('既に hQSL.R 受領済み',r['reason'])
    def test_waiting_tag_promotes_and_duplicate_does_not_grow(self):
        self.assertEqual(change('memo BURO','BURO.R')[0],'memo BURO.R')
        self.assertEqual(change('memo BURO BURO.R','BURO.R')[0],'memo BURO.R')
        self.assertEqual(change('CARD LoTW.R','CARD.R')[0],'CARD.R LoTW.R')
    def test_buro_judgement(self):
        self.assertEqual(buro_judgement('memo'),'');self.assertEqual(buro_judgement('memo BURO'),'発送済');self.assertEqual(buro_judgement('memo BURO.R'),'発送/受領済')

    def test_ui_source_has_guarded_two_stage_flow(self):
        text=Path('qsl_ui.py').read_text(encoding='utf-8')
        self.assertIn('処理するTXTを「受領一覧TXT」で選択してください。',text)
        self.assertIn("['選択してください',*METHODS]",text)
        self.assertIn('処理の詳細へ進む',text)
        self.assertIn('class QSLDetailDialog',text)
        self.assertIn('BURO判定',text)
        self.assertNotIn('選択行の候補（複数候補は自動確定しません）',text)

if __name__=='__main__':unittest.main()
