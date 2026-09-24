import unittest,tempfile
from pathlib import Path
from unittest.mock import patch
from blacklist import Blacklist,Entry
from storage import ExternalChange,StorageError
class BlacklistTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.store=Blacklist(self.tmp.name)
    def test_crud_normalization_and_scope(self):
        self.store.update(Entry('ｊａ１ｙｙｙ','memo',False))
        self.assertEqual(len(self.store.matching('JA1YYY')),1);self.assertFalse(self.store.matching('JA1YYY/1'))
        self.store.update(Entry('JA1YYY','new',True),'JA1YYY')
        self.assertEqual(len(Blacklist(self.tmp.name).matching('JA1YYY/P')),1)
        self.assertFalse(self.store.matching('JA1YYYZ'));self.assertFalse(self.store.matching('KH6/JA1YYY'))
        with self.assertRaises(ValueError):self.store.update(Entry('JA1YYY'))
        self.store.update(original='JA1YYY');self.assertFalse(Blacklist(self.tmp.name).entries)
    def test_external_change_and_failure_preserve_file(self):
        self.store.update(Entry('JA1YYY'));other=Blacklist(self.tmp.name);other.update(Entry('JA2YYY'));raw=self.store.path.read_bytes()
        with self.assertRaises(ExternalChange):self.store.update(original='JA1YYY')
        self.assertEqual(self.store.path.read_bytes(),raw)
        other.reload()
        with patch('blacklist.replace_bytes',side_effect=OSError('disk full')):
            with self.assertRaises(OSError):other.update(original='JA1YYY')
        self.assertEqual(other.path.read_bytes(),raw)
    def test_corrupt_config_does_not_become_empty(self):
        self.store.path.parent.mkdir();self.store.path.write_bytes(b'invalid')
        with self.assertRaises(StorageError):Blacklist(self.tmp.name)
        self.assertEqual(self.store.path.read_bytes(),b'invalid')
