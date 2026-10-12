import subprocess
import sys
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import radio_control


class DummySerialPort:
    def __init__(self):
        self.in_waiting=0
        self.closed=False
        self.writes=[]
    def write(self,data):
        self.writes.append(bytes(data));return len(data)
    def read(self,_n=1):
        return b''
    def close(self):
        self.closed=True


class FailingVirtualProvider:
    def __init__(self,*_args,**_kwargs):
        pass
    def load_existing(self,_verify=True):
        raise radio_control.VirtualPortError('setupc test failure')


class RadioFix4Tests(unittest.TestCase):
    def test_virtual_failure_does_not_drop_physical_connection(self):
        mgr=radio_control.RadioManager(Path('.'))
        physical=DummySerialPort()
        settings={
            'radio_civ_address':'94',
            'radio_virtual_enabled':True,
            'radio_setupc_path':'dummy setupc.exe',
        }
        fake_serial=SimpleNamespace()
        with patch.dict(sys.modules,{'serial':fake_serial}), \
             patch.object(mgr,'_resolve_civ',return_value=('COM8',38400,50050000.0)), \
             patch.object(radio_control,'_open_serial_safe',return_value=physical), \
             patch.object(radio_control,'VirtualPortProvider',FailingVirtualProvider):
            mgr._thread=threading.Thread(target=mgr._run_civ,args=(settings,),daemon=True)
            mgr._thread.start()
            deadline=time.monotonic()+2
            state=None
            while time.monotonic()<deadline:
                state=mgr.state()
                if '仮想COM中継を開始できません' in state.virtual_status:
                    break
                time.sleep(.02)
            self.assertIsNotNone(state)
            self.assertTrue(state.connected)
            self.assertEqual(state.port,'COM8')
            self.assertEqual(state.frequency_hz,50050000.0)
            self.assertIn('setupc test failure',state.virtual_status)
            self.assertTrue(mgr.is_running())
            mgr.stop()

    def test_subprocess_timeout_is_converted_to_result(self):
        with patch('radio_control.subprocess.run',side_effect=subprocess.TimeoutExpired(['setupc.exe','list'],3)):
            result=radio_control._run(['setupc.exe','list'],timeout=3)
        self.assertEqual(result.returncode,124)
        self.assertIn('3秒でタイムアウト',result.stderr)

    def test_fix4_ui_surfaces_virtual_bridge_status(self):
        settings=Path('settings_ui.py').read_text(encoding='utf-8')
        main=Path('main.py').read_text(encoding='utf-8')
        self.assertIn("if state.virtual_status:suffix+=' / '+state.virtual_status",settings)
        self.assertIn("if state.virtual_status:tip.append(state.virtual_status)",main)


if __name__=='__main__':
    unittest.main()
