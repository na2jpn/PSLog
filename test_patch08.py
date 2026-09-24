import hashlib
import json
import shutil
import tempfile
import zipfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from update_package import (
    UpdateInfo, REQUIRED_MANAGED_ROOTS, classify_update, installation_matches,
    UPDATE_UPGRADE, UPDATE_REINSTALL, UPDATE_SAME, UPDATE_DOWNGRADE,
)
from update_launcher import launch_update
from updater import perform


def sha(data):
    return hashlib.sha256(data).hexdigest()


class Patch08SameVersionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/'PSLog';self.root.mkdir()
        payload={
            'pslog.exe':b'MZ pslog same-version fixture',
            'exec/PSLogUpdater.exe':b'MZ updater same-version fixture',
            '_internal/runtime.dat':b'runtime fixture',
            'meta/BUILD_INFO.json':b'{"build":"fixture"}',
        }
        for logical,data in payload.items():
            p=self.root/Path(*logical.split('/'));p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        (self.root/'docs').mkdir()
        (self.root/'meta/PSLOG_UPDATE_INFO.json').write_text('{}',encoding='utf-8')
        self.info=UpdateInfo(
            Path(self.tmp.name)/'same.zip','1.048','2026-09-19T00:00:00+00:00',
            {name:sha(data) for name,data in payload.items()},
            REQUIRED_MANAGED_ROOTS,'meta/PSLOG_UPDATE_INFO.json'
        )

    def test_exact_same_version_is_not_reinstalled(self):
        self.assertTrue(installation_matches(self.info,self.root))
        self.assertEqual(classify_update(self.info,'1.048',self.root),UPDATE_SAME)

    def test_same_version_changed_file_becomes_repair_reinstall(self):
        (self.root/'_internal/runtime.dat').write_bytes(b'changed or damaged')
        self.assertFalse(installation_matches(self.info,self.root))
        self.assertEqual(classify_update(self.info,'1.048',self.root),UPDATE_REINSTALL)

    def test_same_version_missing_empty_managed_directory_is_reinstall(self):
        (self.root/'docs').rmdir()
        self.assertEqual(classify_update(self.info,'1.048',self.root),UPDATE_REINSTALL)

    def test_newer_and_older_still_keep_forward_only_rule(self):
        newer=UpdateInfo(self.info.path,'1.049',self.info.packaged_utc,self.info.files,self.info.managed_roots,self.info.manifest_logical)
        older=UpdateInfo(self.info.path,'1.046',self.info.packaged_utc,self.info.files,self.info.managed_roots,self.info.manifest_logical)
        self.assertEqual(classify_update(newer,'1.048',self.root),UPDATE_UPGRADE)
        self.assertEqual(classify_update(older,'1.048',self.root),UPDATE_DOWNGRADE)

    def test_launcher_records_reinstall_mode_for_external_updater(self):
        # launch_update copies the installed helper to a temporary folder and
        # records the chosen mode in the one-time session JSON.
        with patch('update_launcher.subprocess.Popen',return_value=SimpleNamespace(pid=43210)):
            session=launch_update(self.root,self.info.path,'1.048',mode='reinstall')
        try:
            data=json.loads(Path(session).read_text(encoding='utf-8'))
            self.assertEqual(data['mode'],'reinstall')
            self.assertEqual(data['current_version'],'1.048')
        finally:
            shutil.rmtree(Path(session).parent,ignore_errors=True)

    def test_launcher_rejects_unknown_mode(self):
        with self.assertRaisesRegex(Exception,'更新モード'):
            launch_update(self.root,self.info.path,'1.048',mode='downgrade')


class Patch08UpdaterTransactionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name)
        self.root=self.base/'PSLog';self.root.mkdir()
        self.payload={
            'pslog.exe':b'MZ repaired pslog',
            'exec/PSLogUpdater.exe':b'MZ repaired updater',
            '_internal/runtime.dat':b'new runtime',
            'meta/BUILD_INFO.json':b'{"build":"repair"}',
        }
        # Current installation deliberately differs in one managed file.
        current=dict(self.payload);current['_internal/runtime.dat']=b'old runtime'
        for logical,data in current.items():
            p=self.root/Path(*logical.split('/'));p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        (self.root/'docs').mkdir();(self.root/'meta/PSLOG_UPDATE_INFO.json').write_text('{}',encoding='utf-8')
        self.package=self.base/'repair.zip'
        hashes={k:sha(v) for k,v in self.payload.items()}
        manifest={
            'format':'PSLog update package','format_version':1,'product':'PSLog','version':'1.048',
            'packaged_utc':'2026-09-19T00:00:00+00:00','managed_roots':list(REQUIRED_MANAGED_ROOTS),
            'preserve':['config/','logbook/','logbook_flr/','bak/','output/'],'files':hashes,
        }
        with zipfile.ZipFile(self.package,'w',zipfile.ZIP_DEFLATED) as z:
            z.writestr('PSLog/docs/',b'')
            for name,data in self.payload.items():z.writestr('PSLog/'+name,data)
            z.writestr('PSLog/meta/PSLOG_UPDATE_INFO.json',json.dumps(manifest).encode('utf-8'))

    def session(self,mode):
        path=self.base/(mode+'.json');token='patch08token'
        path.write_text(json.dumps({
            'format':'PSLog update session','format_version':1,'token':token,
            'package':str(self.package),'target':str(self.root),'current_version':'1.048',
            'mode':mode,'pid':0,
        }),encoding='utf-8')
        return path,token

    def test_external_updater_accepts_same_version_reinstall_mode(self):
        session,token=self.session('reinstall')
        with patch('updater._runtime_self_check'):
            version,target,returned_token,mode=perform(session,token)
        self.assertEqual((version,target,returned_token,mode),('1.048',self.root.resolve(),token,'reinstall'))
        self.assertEqual((self.root/'_internal/runtime.dat').read_bytes(),b'new runtime')
        self.assertFalse(session.exists())

    def test_external_updater_rejects_same_version_when_session_says_upgrade(self):
        session,token=self.session('upgrade')
        with patch('updater.subprocess.Popen'), self.assertRaisesRegex(RuntimeError,'通常アップデート'):
            perform(session,token)
        self.assertEqual((self.root/'_internal/runtime.dat').read_bytes(),b'old runtime')


if __name__=='__main__':
    unittest.main()
