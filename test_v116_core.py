import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from model import QSO, InputError
from radio_control import VirtualPortProvider
from search import Hit
from storage import Repository


class V116CoreTests(unittest.TestCase):
    def test_nonstandard_contest_rst_serialization_is_opt_in(self):
        q=QSO('2026-10-12','12:34','7','FT8','JA1AAA','13L','001A','Japan','Tokyo','001A','')
        with self.assertRaises(InputError):
            q.to_ps()
        line=q.to_ps(allow_nonstandard_rst=True)
        self.assertIn(' | 13L | 001A | ',line)

    def test_contest_hit_edit_preserves_nonstandard_rst(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=Repository(tmp)
            path=repo.path_for('JH1HST','TEST202610','2026-10-12')
            path.parent.mkdir(parents=True,exist_ok=True)
            q=QSO('2026-10-12','12:34','7','FT8','JA1AAA','13L','001A','Japan','Tokyo','001A','')
            path.write_bytes(('\ufeff'+q.to_ps(allow_nonstandard_rst=True)+'\r\n').encode('utf-8'))
            session=repo.open(path)
            line,loaded=session.log.records[0]
            hit=Hit(session,session.snapshot,line,session.log.lines[line-1].raw,loaded,'JH1HST')
            edited=QSO(**vars(loaded));edited.his_qth='Saitama Japan'
            hit.apply(edited)
            reopened=repo.open(path)
            saved=reopened.log.records[0][1]
            self.assertEqual(saved.sent,'13L')
            self.assertEqual(saved.received,'001A')
            self.assertEqual(saved.his_qth,'Saitama Japan')

    def test_com0com_pair_uses_two_real_ports(self):
        with tempfile.TemporaryDirectory() as tmp:
            provider=VirtualPortProvider(tmp,'')
            provider.setupc='setupc.exe'
            with patch('radio_control.os.name','nt'), \
                 patch('radio_control.list_serial_ports',side_effect=[[],['COM208','COM209']]), \
                 patch('radio_control._run_elevated_setupc_create',return_value=(0,0,'OK|0')) as elevated:
                pair=provider.create_persistent('COM8')
            self.assertEqual(pair.external_port,'COM208')
            self.assertEqual(pair.internal_name,'COM209')
            elevated.assert_called_once_with('setupc.exe','COM208','COM209')
            self.assertTrue(provider.state_path.exists())



if __name__=='__main__':
    unittest.main()
