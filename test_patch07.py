import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from locations import exact_matches, normalize_lookup
from update_state import write_lock, lock_status, remove_lock, cleanup_stale_rollbacks, lock_path
from updater import _wait_for_launch_ack, _launch_updated_pslog


class Patch07LocationTests(unittest.TestCase):
    def setUp(self):
        self.data={'rows':[
            {'name':'東京都千代田区','verified_qth':'Chiyoda Tokyo Japan','reference_qth':'','kind':'JCC','code':'100101'},
            {'name':'埼玉県草加市','verified_qth':'Soka Saitama Japan','reference_qth':'','kind':'JCC','code':'1321'},
            {'name':'埼玉県戸田市','verified_qth':'Toda Saitama Japan','reference_qth':'','kind':'JCC','code':'1324'},
        ]}
    def test_exact_japanese_english_and_nfkc(self):
        self.assertEqual(exact_matches(self.data,'東京都千代田区')[0]['code'],'100101')
        self.assertEqual(exact_matches(self.data,'chiyoda tokyo japan')[0]['code'],'100101')
        self.assertEqual(normalize_lookup('Ｃｈｉｙｏｄａ， Ｔｏｋｙｏ  Japan'),'chiyoda tokyo japan')
        self.assertEqual(exact_matches(self.data,'千代田区'),[])
        self.assertEqual(exact_matches(self.data,'Soka Saitama Japan')[0]['code'],'1321')
        self.assertEqual(exact_matches(self.data,'Toda Saitama Japan')[0]['code'],'1324')


class Patch07UpdateStateTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/'PSLog';self.root.mkdir()
    def test_active_lock_and_remove(self):
        write_lock(self.root,'abc',os.getpid())
        status,data=lock_status(self.root)
        self.assertEqual(status,'active');self.assertEqual(data['token'],'abc')
        self.assertTrue(remove_lock(self.root,'abc'));self.assertEqual(lock_status(self.root)[0],'none')
    def test_stale_lock_is_removed(self):
        write_lock(self.root,'stale',99999999)
        self.assertEqual(lock_status(self.root)[0],'stale')
        self.assertFalse(lock_path(self.root).exists())
    def test_cleanup_rollbacks_skips_keep_marker(self):
        removable=self.root.parent/'.PSLogUpdateRollback-remove';removable.mkdir();(removable/'x').write_text('x')
        keep=self.root.parent/'.PSLogUpdateRollback-keep';keep.mkdir();(keep/'.PSLOG_KEEP_ROLLBACK').write_text('keep')
        removed=cleanup_stale_rollbacks(self.root)
        self.assertIn(removable,removed);self.assertFalse(removable.exists());self.assertTrue(keep.exists())

    def test_updater_waits_for_new_pslog_ack(self):
        with patch('updater.read_lock',side_effect=[{'token':'abc'},None]),patch('updater.time.sleep'):
            _wait_for_launch_ack(self.root,'abc',timeout=1)

    def test_updated_pslog_launch_carries_token(self):
        exe=self.root/'pslog.exe';exe.write_bytes(b'MZ')
        with patch('updater.subprocess.Popen') as popen:
            _launch_updated_pslog(self.root,'abc')
        args=popen.call_args.args[0]
        self.assertEqual(args,[str(exe),'--update-launch-token','abc'])


if __name__=='__main__':unittest.main()
