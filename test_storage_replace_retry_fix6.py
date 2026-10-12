import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from storage import Snapshot, replace_bytes


class StorageReplaceRetryFix6Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'logbook' / '2026_JH1HST_.txt'
        self.path.parent.mkdir(parents=True)
        self.path.write_bytes(b'old')
        self.snap = Snapshot.read(self.path)

    def test_transient_permission_error_retries_then_succeeds(self):
        real_replace = __import__('os').replace
        calls = {'n': 0}

        def flaky(src, dst):
            calls['n'] += 1
            if calls['n'] <= 2:
                raise PermissionError(13, 'temporary lock')
            return real_replace(src, dst)

        with patch('storage.os.replace', side_effect=flaky), patch('storage.time.sleep') as sleep:
            replace_bytes(self.path, b'new', self.snap)

        self.assertEqual(self.path.read_bytes(), b'new')
        self.assertEqual(calls['n'], 3)
        self.assertEqual([c.args[0] for c in sleep.call_args_list], [0.05, 0.10])

    def test_permanent_permission_error_is_not_hidden(self):
        with patch('storage.os.replace', side_effect=PermissionError(13, 'denied')), patch('storage.time.sleep') as sleep:
            with self.assertRaises(PermissionError):
                replace_bytes(self.path, b'new', self.snap)
        self.assertEqual(self.path.read_bytes(), b'old')
        self.assertEqual(sleep.call_count, 4)
        self.assertFalse(any(self.path.parent.glob('.pslog-*.tmp')))

    def test_external_change_during_retry_still_wins(self):
        real_replace = __import__('os').replace
        calls = {'n': 0}

        def first_locked(src, dst):
            calls['n'] += 1
            if calls['n'] == 1:
                raise PermissionError(13, 'temporary lock')
            return real_replace(src, dst)

        def mutate(_seconds):
            self.path.write_bytes(b'external')

        from storage import ExternalChange
        with patch('storage.os.replace', side_effect=first_locked), patch('storage.time.sleep', side_effect=mutate):
            with self.assertRaises(ExternalChange):
                replace_bytes(self.path, b'new', self.snap)
        self.assertEqual(self.path.read_bytes(), b'external')


if __name__ == '__main__':
    unittest.main()
