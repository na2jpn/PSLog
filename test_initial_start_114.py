import unittest
from pathlib import Path

from storage import VERSION


class InitialStart114Tests(unittest.TestCase):
    def setUp(self):
        self.text=(Path(__file__).with_name('main.py')).read_text(encoding='utf-8')

    def test_version(self):
        self.assertEqual(VERSION,'1.14')

    def test_first_start_can_switch_to_free_radio(self):
        self.assertIn("prompt=QLabel('アマチュア無線のコールサイン')",self.text)
        self.assertIn("QPushButton('アマチュア無線ではなくフリラのコールサイン')",self.text)
        self.assertIn("prompt.setText('フリラのコールサイン')",self.text)
        self.assertIn("free_box=QGroupBox('フリラログの設定')",self.text)
        self.assertIn("model.setPlaceholderText('任意・自由入力・過去ログから候補')",self.text)
        self.assertIn("session=free_session(slot,free_call,free_type,machine,'')",self.text)

    def test_blank_model_remains_valid_when_loading_free_tab(self):
        self.assertIn("if self.f_own.text().strip():self._activate_free_station(False)",self.text)
        self.assertNotIn("if self.f_own.text().strip() and self.f_model.currentText().strip():self._activate_free_station(False)",self.text)

    def test_free_call_is_not_inherited_into_amateur_tab(self):
        self.assertIn("call='' if s.get('type')=='free' else s.get('call','')",self.text)

    def test_free_only_settings_do_not_overwrite_amateur_own(self):
        self.assertIn("if primary is None:",self.text)
        self.assertIn("own=self.settings.get('own','');suffix=self.settings.get('suffix','')",self.text)


if __name__=='__main__':
    unittest.main()
