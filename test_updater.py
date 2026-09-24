import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from updater import _apply_staged, _verify_tree, _runtime_self_check
from update_package import REQUIRED_MANAGED_ROOTS
from update_launcher import ensure_updater_layout, ensure_distribution_layout


class UpdaterApplyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)

    def make_tree(self,root,tag):
        root.mkdir(parents=True,exist_ok=True)
        (root/'pslog.exe').write_bytes((tag+' exe').encode())
        (root/'exec').mkdir();(root/'exec/PSLogUpdater.exe').write_bytes((tag+' updater').encode())
        internal=root/'_internal';internal.mkdir();(internal/'runtime.dat').write_text(tag)
        meta=root/'meta';meta.mkdir();(meta/'BUILD_INFO.json').write_text(tag);(meta/'PSLOG_UPDATE_INFO.json').write_text(tag)
        (root/'docs').mkdir()

    def test_application_replaced_user_data_preserved(self):
        target=self.root/'target';stage=self.root/'stage'
        self.make_tree(target,'old');self.make_tree(stage,'new')
        for folder in ('config','logbook','logbook_flr','bak','output'):
            p=target/folder;p.mkdir();(p/'keep.txt').write_text(folder)
        (target/'my-note.txt').write_text('unknown root user file')
        _apply_staged(stage,target,REQUIRED_MANAGED_ROOTS)
        self.assertEqual((target/'_internal/runtime.dat').read_text(),'new')
        self.assertEqual((target/'pslog.exe').read_bytes(),b'new exe')
        self.assertEqual((target/'meta/BUILD_INFO.json').read_text(),'new')
        self.assertTrue((target/'docs').is_dir())
        for folder in ('config','logbook','logbook_flr','bak','output'):
            self.assertEqual((target/folder/'keep.txt').read_text(),folder)
        self.assertEqual((target/'my-note.txt').read_text(),'unknown root user file')


    def test_verify_tree_detects_changed_installed_file(self):
        root=self.root/'verify';root.mkdir()
        (root/'pslog.exe').write_bytes(b'good')
        import hashlib
        info=SimpleNamespace(files={'pslog.exe':hashlib.sha256(b'good').hexdigest()})
        _verify_tree(info,root)
        (root/'pslog.exe').write_bytes(b'bad')
        with self.assertRaisesRegex(RuntimeError,'整合性確認'):
            _verify_tree(info,root)

    def test_verify_callback_failure_rolls_back_old_application(self):
        target=self.root/'target2';stage=self.root/'stage2'
        self.make_tree(target,'old');self.make_tree(stage,'new')
        def fail(_root):
            raise RuntimeError('self check failed')
        with self.assertRaisesRegex(RuntimeError,'self check failed'):
            _apply_staged(stage,target,REQUIRED_MANAGED_ROOTS,fail)
        self.assertEqual((target/'_internal/runtime.dat').read_text(),'old')
        self.assertEqual((target/'pslog.exe').read_bytes(),b'old exe')

    def test_runtime_self_check_rejects_nonzero_exit(self):
        target=self.root/'runtime';target.mkdir();(target/'pslog.exe').write_bytes(b'MZ')
        with patch('updater.subprocess.run') as run:
            run.return_value=SimpleNamespace(returncode=91)
            with self.assertRaisesRegex(RuntimeError,'自己診断に失敗'):
                _runtime_self_check(target)

    def test_legacy_root_updater_moves_to_exec_and_replaces_old_copy(self):
        target=self.root/'layout';target.mkdir()
        (target/'exec').mkdir();(target/'exec/PSLogUpdater.exe').write_bytes(b'old')
        (target/'PSLogUpdater.exe').write_bytes(b'new')
        resolved=ensure_updater_layout(target)
        self.assertEqual(resolved,target/'exec/PSLogUpdater.exe')
        self.assertEqual(resolved.read_bytes(),b'new')
        self.assertFalse((target/'PSLogUpdater.exe').exists())

    def test_1042_bridge_root_files_migrate_to_clean_1043_layout(self):
        target=self.root/'bridge';target.mkdir()
        (target/'exec').mkdir();(target/'exec/PSLogUpdater.exe').write_bytes(b'updater')
        (target/'BUILD_INFO.json').write_text('build')
        (target/'PSLOG_UPDATE_INFO.json').write_text('update')
        for name in ('USER_GUIDE.txt','SAVE_LOCATION.md','WINDOWS_CHECKLIST.txt'):
            (target/name).write_text('retired')
        updater=ensure_distribution_layout(target)
        self.assertEqual(updater,target/'exec/PSLogUpdater.exe')
        self.assertEqual((target/'meta/BUILD_INFO.json').read_text(),'build')
        self.assertEqual((target/'meta/PSLOG_UPDATE_INFO.json').read_text(),'update')
        self.assertTrue((target/'docs').is_dir())
        self.assertEqual(list((target/'docs').iterdir()),[])
        for name in ('BUILD_INFO.json','PSLOG_UPDATE_INFO.json','USER_GUIDE.txt','SAVE_LOCATION.md','WINDOWS_CHECKLIST.txt'):
            self.assertFalse((target/name).exists(),name)


    def test_root_file_with_retired_name_is_not_deleted_without_legacy_metadata(self):
        target=self.root/'manual';target.mkdir()
        (target/'exec').mkdir();(target/'exec/PSLogUpdater.exe').write_bytes(b'updater')
        (target/'USER_GUIDE.txt').write_text('user-created later')
        ensure_distribution_layout(target)
        self.assertEqual((target/'USER_GUIDE.txt').read_text(),'user-created later')
        self.assertTrue((target/'docs').is_dir())



if __name__=='__main__':unittest.main()
