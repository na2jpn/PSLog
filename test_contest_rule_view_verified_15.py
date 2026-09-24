"""Non-GUI regression checks for the first 15 officially reviewed displays."""
from copy import deepcopy
from pathlib import Path
import json
import unittest

from contest_rules import loads
from rule_view_data import contest_sections,is_contest_rule

ROOT=Path(__file__).parent
RULES=ROOT/'config/rules'
IDS={
    'six_meter_and_down','all_asian_dx_cw','all_asian_dx_phone','all_ja',
    'jarl_world_wide_rtty','field_day','all_ja_cg','all_ja4','all_kyushu',
    'ja0_vhf','all_ja8','ja9_hf_cw','ja9_hf_phone','ja9_vu','all_ja5',
}

def rows(rule):
    return {label:value for _,_,section in contest_sections(rule) for label,value,_ in section}

class ReviewedRuleViewTests(unittest.TestCase):
    def test_all_registered_rules_load_and_render(self):
        paths=list(RULES.glob('*.txt'))
        self.assertEqual(len(paths),87)
        for path in paths:
            with self.subTest(path=path.name):
                rule=loads(path.read_text(encoding='utf-8-sig'))
                self.assertTrue(contest_sections(rule))

    def test_qso_party_is_only_in_its_dedicated_view(self):
        rules=[loads(path.read_text(encoding='utf-8-sig')) for path in RULES.glob('*.txt')]
        self.assertEqual(sum(is_contest_rule(rule) for rule in rules),86)
        self.assertFalse(is_contest_rule(next(rule for rule in rules if rule['id']=='qso_party')))

    def test_fifteen_display_records_are_independent_and_complete(self):
        found=set()
        required={'participants','power','call_method','counterparts','restrictions',
                  'exchange','repeat','points_display','multipliers_display','submission_deadline'}
        for path in RULES.glob('*.txt'):
            rule=loads(path.read_text(encoding='utf-8-sig'))
            if rule['id'] not in IDS:continue
            found.add(rule['id'])
            view=rule['event']['rule_view']
            self.assertFalse(required-set(view),rule['id'])
            displayed=rows(rule)
            self.assertEqual(displayed['通常得点'],view['points_display'])
            self.assertEqual(displayed['マルチ定義'],view['multipliers_display'])
            self.assertEqual(displayed['提出締切'],view['submission_deadline'])
            self.assertNotIn('周波数制限',displayed)
            self.assertEqual([label for label in displayed if label=='移動運用'],
                             ['移動運用'] if 'movement' in view else [])
        self.assertEqual(found,IDS)

    def test_specific_official_rules_and_shared_display_policy(self):
        def get(ident):
            path=next(path for path in RULES.glob('*.txt')
                      if json.loads(path.read_text(encoding='utf-8-sig'))['id']==ident)
            return rows(loads(path.read_text(encoding='utf-8-sig')))
        self.assertIn('2400MHz帯以上：2点',get('six_meter_and_down')['通常得点'])
        self.assertIn('CQ JA8 TEST',get('all_ja8')['呼び出し方法'])
        self.assertIn('X=3',get('all_ja8')['特殊なルール'])
        self.assertIn('年代別符号はマルチになりません',get('all_ja8')['マルチ定義'])
        self.assertIn('9エリアから運用する局',get('ja9_hf_cw')['交信対象'])
        self.assertIn('FT8',get('ja9_vu')['特殊なルール'])
        self.assertIn('慣例',get('all_ja5')['呼び出し方法'])
        self.assertEqual(get('ja9_hf_cw')['送信出力'],'制限なし')
        self.assertNotIn('移動運用',get('ja9_hf_cw'))
        self.assertIn('別の場所へ移って参加することはできません',get('ja0_vhf')['移動運用'])

    def test_generator_overlay_never_changes_submission_or_scoring(self):
        from devtools.rule_view_verified_15 import apply
        for path in RULES.glob('*.txt'):
            rule=loads(path.read_text(encoding='utf-8-sig'))
            if rule['id'] not in IDS:continue
            before=deepcopy(rule)
            before.pop('url')
            before['event'].pop('rule_view',None)
            regenerated=apply(deepcopy(rule))
            regenerated.pop('url')
            regenerated['event'].pop('rule_view',None)
            self.assertEqual(before,regenerated,rule['id'])

if __name__=='__main__':unittest.main()
