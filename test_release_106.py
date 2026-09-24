import json
import unittest
from pathlib import Path

from storage import VERSION
from contest_station import check_submission


class Release106Tests(unittest.TestCase):
    def test_version(self):
        self.assertEqual(VERSION, '1.14')

    def test_submission_footer_actions_are_owned_by_wizard_footer(self):
        submit = Path('contest_submit_ui.py').read_text(encoding='utf-8')
        wizard = Path('contest_ui.py').read_text(encoding='utf-8')
        self.assertIn("self.prepare_button=button('入力内容を確認',self.prepare)", submit)
        self.assertIn("self.save_button=button('ファイルを保存',self.write)", submit)
        self.assertIn('self.submit_prepare_button=self.submission.prepare_button', wizard)
        self.assertIn('row.addWidget(self.submit_prepare_button);row.addWidget(self.submit_save_button);row.addWidget(self.next)', wizard)
        self.assertIn('self.submit_prepare_button.setVisible(final_stage);self.submit_save_button.setVisible(final_stage)', wizard)

    def test_only_explicit_all_station_opplace_contests_remain_mandatory(self):
        expected = {
            'all_chiba_2026.txt',
            'all_hyogo_2026.txt',
            'kcj_2026.txt',
            'kcj-topband_2026.txt',
        }
        actual = set()
        for path in Path('config/rules').glob('*.txt'):
            try:
                rule = json.loads(path.read_text(encoding='utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            required = rule.get('event', {}).get('submission', {}).get('required_fields', [])
            if 'opplace' in required:
                actual.add(path.name)
        self.assertEqual(actual, expected)

    def test_portable_still_requires_opplace_but_fixed_does_not(self):
        rule = {'event': {}}
        # Fixed/stationary operation may omit OPPLACE unless the contest explicitly
        # requires it through submission.required_fields.
        check_submission(rule, {}, {'portable': False, 'guest': False, 'opplace': ''}, 'JH1HST')
        with self.assertRaisesRegex(ValueError, '移動運用の提出には運用地'):
            check_submission(rule, {}, {'portable': True, 'guest': False, 'opplace': ''}, 'JH1HST')
        with self.assertRaisesRegex(ValueError, '移動運用の提出には運用地'):
            check_submission(rule, {}, {'portable': False, 'guest': False, 'opplace': ''}, 'JH1HST/1')
        check_submission(rule, {}, {'portable': True, 'guest': False, 'opplace': 'Soka Saitama Japan'}, 'JH1HST/1')

    def test_relaxed_contests_keep_other_required_fields(self):
        expected_email = {
            'all_ja0_160m_2025.txt',
            'all_ja0_35_2026.txt',
            'all_ja0_7_2026.txt',
            'shizuoka_2026.txt',
        }
        for name in expected_email:
            rule = json.loads((Path('config/rules') / name).read_text(encoding='utf-8'))
            required = rule['event']['submission'].get('required_fields', [])
            self.assertIn('email', required, name)
            self.assertNotIn('opplace', required, name)


if __name__ == '__main__':
    unittest.main()
