import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import radio_control


class RadioFix7Tests(unittest.TestCase):
    def test_virtual_pair_numbering_uses_external_and_internal_com(self):
        self.assertEqual(radio_control.preferred_virtual_pair('COM8',set()),(208,209))
        self.assertEqual(radio_control.preferred_virtual_pair('COM8',{208}),(308,309))
        self.assertEqual(radio_control.preferred_virtual_pair('COM8',{209}),(308,309))
        self.assertEqual(radio_control.preferred_virtual_pair('COM8',{208,209,308}),(408,409))

    def test_create_saves_both_real_com_ports(self):
        with tempfile.TemporaryDirectory() as tmp:
            provider=radio_control.VirtualPortProvider(tmp,'');provider.setupc='setupc.exe'
            with patch('radio_control.os.name','nt'), \
                 patch('radio_control.list_serial_ports',side_effect=[[],['COM208','COM209']]), \
                 patch('radio_control._run_elevated_setupc_create',return_value=(0,7,'OK|7')) as run:
                pair=provider.create_persistent('COM8')
            self.assertEqual((pair.pair_id,pair.external_port,pair.internal_name),(7,'COM208','COM209'))
            run.assert_called_once_with('setupc.exe','COM208','COM209')
            text=provider.state_path.read_text('utf-8')
            self.assertIn('"external_port": "COM208"',text)
            self.assertIn('"internal_name": "COM209"',text)

    def test_run_handles_windows_elevation_required_as_result(self):
        err=OSError('elevation required');err.winerror=740
        with patch('radio_control.subprocess.run',side_effect=err):
            result=radio_control._run(['setupc.exe','list'])
        self.assertEqual(result.returncode,740)
        self.assertIn('elevation required',result.stderr)

    def test_ui_separates_virtual_com_tab_and_has_connect_button(self):
        source=Path('settings_ui.py').read_text(encoding='utf-8')
        self.assertIn("tabs.addTab(virtual_page,'仮想COM中継')",source)
        self.assertIn("self.virtual_radio_connect=QPushButton('接続')",source)
        self.assertLess(source.index("self.radio_test=QPushButton('接続テスト')"),source.index("tabs.addTab(virtual_page,'仮想COM中継')"))
        self.assertIn('COM208 ⇔ COM209',source)
        self.assertNotIn('radio_scroll=QScrollArea()',source)
        self.assertNotIn('virtual_scroll=QScrollArea()',source)

    def test_create_helper_is_ports_class_on_both_ends(self):
        source=Path('radio_control.py').read_text(encoding='utf-8')
        self.assertIn("install 'PortName=COM#' 'PortName=COM#'",source)
        self.assertIn('RealPortName=$external',source)
        self.assertIn('RealPortName=$internal',source)


if __name__=='__main__':
    unittest.main()
