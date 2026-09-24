"""Source-grounded, display-only checks for the other 71 contest entries."""
from copy import deepcopy
from pathlib import Path
import json
import unittest

from contest_rules import loads
from rule_view_data import contest_sections,is_contest_rule
from devtools.rule_view_verified_remaining71 import apply,DATA

ROOT=Path(__file__).parent
RULES=ROOT/'config/rules'
SOURCES=ROOT/'docs/contest-research/sources'

def rows(rule):
    return {label:value for _,_,section in contest_sections(rule) for label,value,_ in section}

class Remaining71ViewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.items=json.loads(DATA.read_text(encoding='utf-8'))
        cls.rules={rule['id']:rule for rule in
                   (loads(p.read_text(encoding='utf-8-sig')) for p in RULES.glob('*.txt'))}

    def test_all_rules_render_with_core_on_air_facts(self):
        self.assertEqual(len(self.rules),87)
        self.assertEqual(len(self.items),71)
        self.assertEqual(sum(is_contest_rule(r) for r in self.rules.values()),86)
        for ident,rule in self.rules.items():
            if not is_contest_rule(rule):continue
            with self.subTest(ident=ident):
                displayed=rows(rule)
                for label in ('呼び出し方法','交信対象','通常得点','送信出力'):
                    self.assertTrue(displayed[label].strip())
                    self.assertNotIn('未登録',displayed[label])
                self.assertNotIn('周波数制限',displayed)

    def test_remaining_records_have_documented_primary_facts(self):
        for ident,item in self.items.items():
            with self.subTest(ident=ident):
                rule=self.rules[ident]
                self.assertEqual(item['year'],rule['year'])
                self.assertTrue((SOURCES/item['source_file']).is_file())
                self.assertTrue(item['source_url'] or item.get('source_note'),ident)
                expected=item['rule_view']
                self.assertTrue(expected['points_display'])
                self.assertEqual(rule['event']['rule_view']['points_display'],expected['points_display'])
                for field,value in expected.items():
                    self.assertEqual(rule['event']['rule_view'][field],value)

    def test_representative_differences_and_official_url(self):
        def view(ident):return rows(self.rules[ident])
        self.assertIn('CQ JA7 TEST',view('all_tohoku')['呼び出し方法'])
        self.assertIn('東北管外局：東北管内',view('all_tohoku')['交信対象'])
        self.assertIn('2400MHz帯5点',view('tokai_qso')['通常得点'])
        self.assertIn('デジタルモードを含みます',view('all_chiba')['通常得点'])
        self.assertIn('4点',view('all_osaka')['通常得点'])
        self.assertIn('FT4・FT8',view('oita')['通常得点'])
        self.assertIn('FT4・FT8',view('ww-digi')['交信対象'])
        self.assertIn('HFマルチバンド',view('nagasaki')['送信出力'])
        self.assertIn('県外局同士の交信も1点',view('fukuoka')['交信対象'])
        self.assertEqual(self.rules['toyama_emergency']['url'],
                         'https://www.jarl.com/toyama/25ham/49OSO.pdf')
        self.assertEqual(self.rules['kcwa_cw']['year'],2025)
        self.assertEqual(view('all_akita')['送信出力'],'制限なし')
        self.assertEqual(view('xpo')['送信出力'],'制限なし')
        self.assertNotIn('QRP',view('ai_chikyu')['送信出力'])
        self.assertIn('シングルオペ・マルチオペ共通',view('kagoshima')['送信出力'])

    def test_overlay_is_display_only(self):
        for ident,rule in self.rules.items():
            if ident not in self.items:continue
            with self.subTest(ident=ident):
                base=deepcopy(rule);base['event']['rule_view']={}
                got=apply(deepcopy(base))
                self.assertEqual(got['event']['rule_view'],self.items[ident]['rule_view'])
                base['event'].pop('rule_view');got['event'].pop('rule_view')
                if ident=='toyama_emergency':base.pop('url');got.pop('url')
                self.assertEqual(got,base)

if __name__=='__main__':unittest.main()
