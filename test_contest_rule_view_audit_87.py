"""Linux-safe regression checks for explicitly sourced contest displays."""
import json
from pathlib import Path
import unittest

from contest_rules import loads, dumps
from rule_view_data import contest_sections

ROOT = Path(__file__).parent
RULES = ROOT / 'config' / 'rules'
FIELDS = ('participants', 'power', 'movement', 'call_method', 'counterparts',
          'frequency', 'restrictions', 'exchange', 'repeat')


class ContestRuleViewAuditTests(unittest.TestCase):
    def test_all_87_rules_parse_and_render(self):
        paths = sorted(RULES.glob('*.txt'))
        self.assertEqual(len(paths), 87)
        for path in paths:
            with self.subTest(path=path.name):
                rule = loads(path.read_text(encoding='utf-8-sig'))
                self.assertEqual(len(contest_sections(rule)), 5)
                self.assertEqual(loads(dumps(rule))['id'], rule['id'])
                view = rule.get('event', {}).get('rule_view', {})
                self.assertFalse(set(view) - (set(FIELDS) | {'submission_notes','submission_deadline','points_display','multipliers_display'}))
                self.assertTrue(all(isinstance(v, str) and v.strip() for v in view.values()))

    def test_verified_examples(self):
        for name, expected in {
            'ai_chikyu_2026.txt': ('CQ AI TEST', '管外局同士'),
            'xpo_2026.txt': ('CQ XPO TEST', '直径500m'),
            'all_akita_2026.txt': ('CQ ATG TEST', 'レピーター'),
            'fukuoka_2026.txt': ('CQ FOX TEST', '50W以内'),
            'qso_party_2026.txt': ('CQ NYP', 'レピーター'),
            'shimane_2026.txt': ('CQ SN TEST', '10分間ルール'),
        }.items():
            with self.subTest(name=name):
                rule = loads((RULES / name).read_text(encoding='utf-8-sig'))
                displayed = '\n'.join(text for _, _, items in contest_sections(rule)
                                      for _, text, _ in items)
                self.assertTrue(all(piece in displayed for piece in expected))
        self.assertEqual(loads((RULES/'qso_party_2026.txt').read_text(encoding='utf-8-sig'))['url'],
                         'https://www.jarl.org/Japanese/1_Tanoshimo/1-1_Contest/qso_party_rule.html')

    def test_display_data_does_not_change_submission_data(self):
        # A separate view can be changed without mutating the executable rule.
        for path in RULES.glob('*.txt'):
            rule = loads(path.read_text(encoding='utf-8-sig'))
            before = json.loads(json.dumps(rule, ensure_ascii=False))
            rule['event']['rule_view'] = {'call_method': '表示専用のテスト'}
            contest_sections(rule)
            self.assertEqual({k: v for k, v in rule.items() if k != 'event'},
                             {k: v for k, v in before.items() if k != 'event'})
            self.assertEqual({k: v for k, v in rule['event'].items() if k != 'rule_view'},
                             {k: v for k, v in before['event'].items() if k != 'rule_view'})

    def test_contest_layout_keeps_submission_notes_in_submission(self):
        rule = loads((RULES/'all_ja8_2026.txt').read_text(encoding='utf-8-sig'))
        sections = {title: {label: text for label, text, _ in rows}
                    for title, _, rows in contest_sections(rule)}
        self.assertEqual(list(sections['その他']), ['参照年', 'ルールID'])
        self.assertNotIn('周波数制限', sections['交信ルール'])
        self.assertNotIn('10分間ルール・時間制限', sections['交信ルール'])
        self.assertIn('特殊なルール', sections['交信ルール'])
        self.assertIn('allja8@jarl.com', sections['提出']['提出時の注意'])
        self.assertEqual(sections['提出']['提出締切'], '2026年7月8日必着')
        self.assertNotIn('docs/contest-research', '\n'.join(sections['その他'].values()))

        all_ja = loads((RULES/'all_ja_2026.txt').read_text(encoding='utf-8-sig'))
        all_ja_rows = {title: {label: text for label, text, _ in rows}
                       for title, _, rows in contest_sections(all_ja)}
        self.assertIn('10分間', all_ja_rows['交信ルール']['特殊なルール'])
        self.assertNotIn('10分間ルール・時間制限', all_ja_rows['交信ルール'])


if __name__ == '__main__':
    unittest.main()
