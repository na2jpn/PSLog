import json
from pathlib import Path
import tempfile
import unittest
from dataclasses import replace

from contest_overview import overview_rows
from model import QSO
from search import Criteria,search
from storage import Repository,VERSION

ROOT=Path(__file__).resolve().parent

class Patch10Tests(unittest.TestCase):
    def test_version(self):
        self.assertEqual(VERSION,'1.14')

    def test_search_jccjcg_accepts_code_and_historical_prefix(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=Repository(tmp)
            base=QSO('2026-09-19','12:00','430','FM','JJ1AAA','59','59','Chiyoda Tokyo Japan','Soka Saitama Japan','','100101')
            other=replace(base,time='12:01',call='JJ1BBB',code='17008C')
            p=repo.path_for('JH1HST','',base.date);p.parent.mkdir(exist_ok=True)
            p.write_bytes(('\ufeff'+base.to_ps()+'\r\n'+other.to_ps()+'\r\n').encode())
            self.assertEqual([h.qso.call for h in search(repo,Criteria('JH1HST',jccjcg='100101')).hits],['JJ1AAA'])
            self.assertEqual([h.qso.call for h in search(repo,Criteria('JH1HST',jccjcg='JCC 100101')).hits],['JJ1AAA'])
            self.assertEqual([h.qso.call for h in search(repo,Criteria('JH1HST',jccjcg='17008')).hits],['JJ1BBB'])

    def test_all_ja_overview_has_requested_core_information(self):
        rule=json.loads((ROOT/'config/rules/all_ja_2026.txt').read_text(encoding='utf-8-sig'))
        rows={label:(text,important) for label,text,important in overview_rows(rule)}
        self.assertEqual(rows['主催'][0],'JARL')
        self.assertIn('2026-04-25 21:00 JST',rows['開催日時'][0])
        self.assertEqual(rows['提出締切'][0],'2026-05-06')
        self.assertIn('1.9',rows['対象バンド'][0]);self.assertIn('CW',rows['対象モード'][0])
        self.assertTrue(rows['マルチバンド／オールバンド部門'][0].startswith('あり'))
        self.assertIn('10分間',rows['10分間ルール・時間制限'][0]);self.assertTrue(rows['10分間ルール・時間制限'][1])
        self.assertIn('都府県支庁ナンバー',rows['ナンバー交換'][0])
        self.assertTrue(rows['送信出力'][1]);self.assertTrue(rows['特記事項'][1])

    def test_every_registered_event_rule_can_build_overview(self):
        count=0
        for path in (ROOT/'config/rules').glob('*.txt'):
            try:rule=json.loads(path.read_text(encoding='utf-8-sig'))
            except Exception:continue
            if not rule.get('event'):continue
            rows=overview_rows(rule);self.assertGreaterEqual(len(rows),10,path.name);count+=1
        self.assertGreater(count,50)

    def test_ui_sources_include_search_field_and_scrollable_overview(self):
        search_ui=(ROOT/'search_ui.py').read_text(encoding='utf-8')
        contest_ui=(ROOT/'contest_ui.py').read_text(encoding='utf-8')
        self.assertIn("line_filter('jccjcg','コード・部分一致')",search_ui)
        self.assertIn("QLabel('JCC/JCG')",search_ui)
        self.assertIn("QGroupBox('コンテスト概要')",contest_ui)
        self.assertIn('self.overview_scroll=QScrollArea()',contest_ui)
        self.assertIn('self.update_contest_overview(r)',contest_ui)

if __name__=='__main__':unittest.main()
