import json
from pathlib import Path
import unittest

from contest_export import check_jarl_official_required
from contest_overview import overview_rows
from storage import VERSION

ROOT = Path(__file__).resolve().parent


class Patch011071Tests(unittest.TestCase):
    def _required_info(self, format_name):
        info = {
            'contest': 'TEST',
            'category': 'CA',
            'callsign': 'JH1HST',
            'address': 'Soka Saitama Japan',
            'name': 'Test Operator',
            'power': '5',
            'email': 'test@example.com',
            'date': '2026-09-24',
            'signature': 'Test Operator',
            'oath': True,
            'fd': False,
        }
        if format_name == 'JARL R1.0':
            info.update(licenseclass='第2級アマチュア無線技士', powertype='定格出力')
        return info

    def test_version(self):
        self.assertEqual(VERSION, '1.14')

    def test_jarl_interactive_required_fields_include_email(self):
        for format_name in ('JARL R1.0', 'JARL R2.1'):
            with self.subTest(format=format_name):
                info = self._required_info(format_name)
                check_jarl_official_required(format_name, info)
                info['email'] = '   '
                with self.assertRaisesRegex(ValueError, 'メールアドレス'):
                    check_jarl_official_required(format_name, info)

    def test_ai_chikyu_submission_default_is_jst(self):
        rule = json.loads((ROOT / 'config/rules/ai_chikyu_2026.txt').read_text(encoding='utf-8-sig'))
        self.assertEqual(rule['event']['submission']['zone'], 'JST')
        source = (ROOT / 'contest_submit_ui.py').read_text(encoding='utf-8')
        self.assertIn("self.fields['zone'].setCurrentText(submit['zone'])", source)

    def test_ai_chikyu_overview_uses_broad_phone_power_rule_only(self):
        rule = json.loads((ROOT / 'config/rules/ai_chikyu_2026.txt').read_text(encoding='utf-8-sig'))
        rows = {label: text for label, text, _ in overview_rows(rule)}
        self.assertEqual(rows['送信出力'], '電話部門は20W以下（HF帯は10W以下）。')
        self.assertNotIn('5 W', rows['送信出力'])
        self.assertNotIn('明示された上限・出力値', rows['送信出力'])

    def test_submission_ui_marks_email_required_and_compacts_requested_gaps(self):
        submit = (ROOT / 'contest_submit_ui.py').read_text(encoding='utf-8')
        wizard = (ROOT / 'contest_ui.py').read_text(encoding='utf-8')
        self.assertIn("('email','メールアドレス *')", submit)
        self.assertIn('source_form.setSizePolicy(QSizePolicy.Policy.Preferred,QSizePolicy.Policy.Fixed)', wizard)
        self.assertIn("send_arrow.setSizePolicy(QSizePolicy.Policy.Preferred,QSizePolicy.Policy.Fixed)", wizard)


if __name__ == '__main__':
    unittest.main()
