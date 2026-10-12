import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import radio_control


class DummySerialPort:
    def __init__(self):
        self.in_waiting=0;self.closed=False;self.writes=[]
    def write(self,data):self.writes.append(bytes(data));return len(data)
    def read(self,_n=1):return b''
    def close(self):self.closed=True


class ExistingVirtualProvider:
    pair=radio_control.VirtualPair(3,'COM208','CNCB3','setupc.exe')
    def __init__(self,*_args,**_kwargs):pass
    def load_existing(self,_verify=True):return self.pair


class RadioFix5Tests(unittest.TestCase):
    def test_manager_reuses_existing_virtual_pair_without_creation(self):
        mgr=radio_control.RadioManager(Path('.'))
        physical=DummySerialPort();virtual=DummySerialPort();opened=[]
        def fake_open(_serial,port,baud,**_kwargs):
            opened.append(port)
            return virtual if str(port).endswith('CNCB3') else physical
        settings={'radio_civ_address':'94','radio_virtual_enabled':True,'radio_setupc_path':'setupc.exe'}
        fake_serial=SimpleNamespace()
        with patch.dict(__import__('sys').modules,{'serial':fake_serial}), \
             patch.object(mgr,'_resolve_civ',return_value=('COM8',38400,50050000.0)), \
             patch.object(radio_control,'_open_serial_safe',side_effect=fake_open), \
             patch.object(radio_control,'VirtualPortProvider',ExistingVirtualProvider):
            mgr._thread=threading.Thread(target=mgr._run_civ,args=(settings,),daemon=True);mgr._thread.start()
            deadline=time.monotonic()+1
            state=None
            while time.monotonic()<deadline:
                state=mgr.state()
                if state.virtual_port=='COM208':break
                time.sleep(.02)
            self.assertEqual(state.virtual_port,'COM208')
            self.assertIn(r'\\.\CNCB3',opened)
            mgr.stop()
        self.assertTrue(physical.closed);self.assertTrue(virtual.closed)

    def test_stop_does_not_remove_persistent_pair(self):
        mgr=radio_control.RadioManager(Path('.'))
        provider=SimpleNamespace(remove_persistent=lambda: (_ for _ in ()).throw(AssertionError('must not delete')))
        mgr._virtual_provider=provider;mgr._pair=radio_control.VirtualPair(1,'COM208','CNCB1','setupc.exe')
        mgr.stop()
        self.assertIsNone(mgr._pair)

    def test_persistent_pair_create_and_remove_use_admin_helpers(self):
        with tempfile.TemporaryDirectory() as tmp:
            provider=radio_control.VirtualPortProvider(tmp,'');provider.setupc='setupc.exe'
            with patch('radio_control.os.name','nt'), \
                 patch('radio_control.list_serial_ports',side_effect=[[],['COM208','COM209']]), \
                 patch('radio_control._run_elevated_setupc_create',return_value=(0,0,'OK|0')):
                pair=provider.create_persistent('COM8')
            self.assertEqual(pair.external_port,'COM208');self.assertEqual(pair.internal_name,'COM209')
            with patch('radio_control.find_setupc',side_effect=lambda configured='': configured or 'setupc.exe'), \
                 patch('radio_control._run_elevated_setupc_remove',return_value=0) as remove, \
                 patch.object(radio_control.VirtualPortProvider,'_pair_visible',return_value=False):
                ok,_message=provider.remove_persistent()
            self.assertTrue(ok);remove.assert_called_once_with('setupc.exe',0)
            self.assertFalse(provider.state_path.exists())

    def test_fix5_ui_and_frequency_style_are_present(self):
        settings=Path('settings_ui.py').read_text(encoding='utf-8')
        main=Path('main.py').read_text(encoding='utf-8')
        self.assertIn("QPushButton('仮想COMを作成')",settings)
        self.assertIn("QPushButton('仮想COMを削除')",settings)
        self.assertIn('作成した仮想COMは常設し',settings)
        self.assertIn('radio_freq_font.pointSize()+2',main)
        self.assertIn('radio_freq_font.setBold(True)',main)


if __name__=='__main__':unittest.main()
