import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from storage import StorageError
from update_package import (
    inspect_update,is_newer,REQUIRED_MANAGED_ROOTS,
    LEGACY_MANAGED_ROOTS_1042,LEGACY_MANAGED_ROOTS_1041,
    MANIFEST_PATH,LEGACY_MANIFEST_PATH,
)


class UpdatePackageTests(unittest.TestCase):
    def make_zip(self, root, version='1.043', extra=None, corrupt_hash=False,
                 managed_roots=REQUIRED_MANAGED_ROOTS, legacy=False):
        root=Path(root);path=root/'update.zip'
        if managed_roots==REQUIRED_MANAGED_ROOTS:
            payload={
                'pslog.exe':b'MZ new pslog',
                'exec/PSLogUpdater.exe':b'MZ new updater',
                '_internal/a.dat':b'internal',
                'meta/BUILD_INFO.json':b'{}',
            }
            dirs=('PSLog/docs/',)
            manifest_path=MANIFEST_PATH
        else:
            payload={
                'pslog.exe':b'MZ new pslog',
                '_internal/a.dat':b'internal',
                'USER_GUIDE.txt':b'guide',
                'SAVE_LOCATION.md':b'save',
                'WINDOWS_CHECKLIST.txt':b'check',
                'BUILD_INFO.json':b'{}',
            }
            if managed_roots==LEGACY_MANAGED_ROOTS_1041:
                payload['PSLogUpdater.exe']=b'MZ old-root updater'
            else:
                payload['exec/PSLogUpdater.exe']=b'MZ updater'
            dirs=()
            manifest_path=LEGACY_MANIFEST_PATH
        if extra:payload.update(extra)
        hashes={k:hashlib.sha256(v).hexdigest() for k,v in payload.items()}
        if corrupt_hash:hashes['pslog.exe']='0'*64
        manifest={
            'format':'PSLog update package','format_version':1,'product':'PSLog',
            'version':version,'packaged_utc':'2026-09-19T00:00:00+00:00',
            'managed_roots':list(managed_roots),
            'preserve':['config/','logbook/','logbook_flr/','bak/','output/'],'files':hashes,
        }
        with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
            for d in dirs:z.writestr(d,b'')
            for name,data in payload.items():z.writestr('PSLog/'+name,data)
            z.writestr(manifest_path,json.dumps(manifest).encode())
        return path

    def test_decimal_version_order(self):
        self.assertTrue(is_newer('1.041','1.04'))
        self.assertTrue(is_newer('1.042','1.041'))
        self.assertTrue(is_newer('1.043','1.042'))
        self.assertTrue(is_newer('1.044','1.043'))
        self.assertTrue(is_newer('1.05','1.049'))
        self.assertTrue(is_newer('1.051','1.05'))
        self.assertTrue(is_newer('1.052','1.051'))
        self.assertTrue(is_newer('1.055','1.052'))
        self.assertTrue(is_newer('1.10','1.078'))
        self.assertTrue(is_newer('1.101','1.10'))
        self.assertFalse(is_newer('1.078','1.10'))
        self.assertTrue(is_newer('1.13','1.12'))
        self.assertTrue(is_newer('1.131','1.13'))
        self.assertFalse(is_newer('1.12','1.13'))
        self.assertFalse(is_newer('1.043','1.043'))
        self.assertFalse(is_newer('1.04','1.043'))

    def test_valid_new_layout_and_forward_only(self):
        with tempfile.TemporaryDirectory() as d:
            p=self.make_zip(d,'1.044')
            info=inspect_update(p,'1.043',True)
            self.assertEqual(info.version,'1.044')
            self.assertEqual(info.manifest_logical,'meta/PSLOG_UPDATE_INFO.json')
            with self.assertRaisesRegex(StorageError,'同じ'):
                inspect_update(p,'1.044',True)
            with self.assertRaisesRegex(StorageError,'戻すことはできません'):
                inspect_update(p,'1.05',True)

    def test_legacy_1042_and_1041_layouts_remain_readable(self):
        with tempfile.TemporaryDirectory() as d:
            p=self.make_zip(d,managed_roots=LEGACY_MANAGED_ROOTS_1042)
            info=inspect_update(p)
            self.assertEqual(info.version,'1.043');self.assertEqual(info.manifest_logical,'PSLOG_UPDATE_INFO.json')
        with tempfile.TemporaryDirectory() as d:
            p=self.make_zip(d,managed_roots=LEGACY_MANAGED_ROOTS_1041)
            self.assertEqual(inspect_update(p).version,'1.043')

    def test_new_layout_requires_explicit_empty_docs_directory(self):
        with tempfile.TemporaryDirectory() as d:
            p=self.make_zip(d)
            with zipfile.ZipFile(p,'r') as zin:
                items=[(i,zin.read(i.filename) if not i.is_dir() else b'') for i in zin.infolist() if i.filename!='PSLog/docs/']
            with zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED) as zout:
                for i,data in items:
                    zout.writestr(i,data)
            with self.assertRaisesRegex(StorageError,'docs'):
                inspect_update(p)

    def test_tamper_and_user_data_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=self.make_zip(d,corrupt_hash=True)
            with self.assertRaisesRegex(StorageError,'一致しません'):
                inspect_update(p)
        with tempfile.TemporaryDirectory() as d:
            p=self.make_zip(d,extra={'config/conf.cfg':b'private'})
            with self.assertRaisesRegex(StorageError,'利用者データ'):
                inspect_update(p)
        with tempfile.TemporaryDirectory() as d:
            p=self.make_zip(d,extra={'logbook_flr/free.txt':b'private'})
            with self.assertRaisesRegex(StorageError,'利用者データ'):
                inspect_update(p)


if __name__=='__main__':unittest.main()
