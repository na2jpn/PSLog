from pathlib import Path
from copy import deepcopy
import unittest

from contest_rules import loads,dumps
from rule_view_data import contest_sections,contest_call_method,contest_frequency

ROOT=Path(__file__).parent


def load_rule(name):
    return loads((ROOT/'config'/'rules'/name).read_text(encoding='utf-8-sig'))


class Patch09Fix1Tests(unittest.TestCase):
    def test_ai_rule_view_is_explicit_and_official_source_grounded(self):
        rule=load_rule('ai_chikyu_2026.txt')
        view=rule['event']['rule_view']
        self.assertEqual(view['call_method'],'電話：CQ AIコンテスト（またはCQ 愛コンテスト）\n電信：CQ AI TEST')
        self.assertIn('管外局同士の交信も有効',view['counterparts'])
        self.assertIn('JARLコンテスト使用周波数帯',view['frequency'])
        self.assertIn('シンプレックス',view['restrictions'])
        self.assertIn('運用開始時のマルチプライヤー内',view['movement'])
        self.assertEqual(rule['event']['required_flags'],[])
        source=(ROOT/'docs'/'contest-research'/'sources'/'ai_chikyuhaku_2026.html').read_bytes().decode('cp932',errors='replace')
        for needle in ('ＣＱ ＡＩコンテスト','ＣＱ 愛コンテスト','ＣＱ ＡＩ ＴＥＳＴ','管外局同士の交信も有効','ＪＡＲＬコンテスト使用周波数帯','コンテスト中の運用場所の変更を禁止','DVモード（デジタル音声通信）かつシンプレックス'):
            self.assertIn(needle,source)

    def test_ai_viewer_shows_explicit_facts_without_submission_inference(self):
        rule=load_rule('ai_chikyu_2026.txt')
        rows={label:text for _,_,items in contest_sections(rule) for label,text,_ in items}
        self.assertIn('CQ AIコンテスト',rows['呼び出し方法'])
        self.assertIn('CQ AI TEST',rows['呼び出し方法'])
        self.assertIn('管外局同士',rows['交信対象'])
        self.assertNotIn('周波数制限',rows)
        self.assertIn('D-STAR',rows['特殊なルール'])
        self.assertIn('日本国内の陸上',rows['参加できる局'])
        self.assertIn('20W以下',rows['送信出力'])
        self.assertIn('市区町村名まで',rows['移動運用'])
        self.assertNotIn('セルフスポット','\n'.join(rows.values()))
        self.assertNotIn('レピータ・クロスバンド','\n'.join(rows.values()))

    def test_rule_view_schema_roundtrip(self):
        rule=load_rule('ai_chikyu_2026.txt')
        again=loads(dumps(rule))
        self.assertEqual(again['event']['rule_view'],rule['event']['rule_view'])

    def test_call_and_frequency_do_not_scrape_unrelated_confirmation_text(self):
        for name in ('cq-wpx-rtty_2026.txt','cq-ww-rtty_2026.txt'):
            rule=load_rule(name)
            self.assertEqual('公式規約に定型のCQ呼び出し指定なし。',contest_call_method(rule))
            self.assertNotIn('相手呼出',contest_call_method(rule))
            # Exercise the missing-data fallback explicitly: registered display
            # facts must not be removed just to retain this older test fixture.
            missing=deepcopy(rule)
            event=missing.setdefault('event',{})
            view=event.setdefault('rule_view',{})
            view.pop('call_method',None)
            view.pop('frequency',None)
            event['required_flags']=['相手呼出を確認した','周波数変更の条件を確認した']
            self.assertIn('未登録',contest_call_method(missing))
            self.assertNotIn('相手呼出',contest_call_method(missing))
            self.assertIn('未登録',contest_frequency(missing))
            self.assertNotIn('周波数変更',contest_frequency(missing))

    def test_ai_builder_owns_display_facts(self):
        text=(ROOT/'devtools'/'build_ai_chikyuhaku_2026.py').read_text(encoding='utf-8')
        self.assertIn("e['rule_view']",text)
        self.assertIn("'call_method':'電話：CQ AIコンテスト",text)
        self.assertIn("e['required_flags']=[]",text)


if __name__=='__main__':unittest.main()
