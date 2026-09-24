import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from tools.package_windows import package,REQUIRED,PDFS,BUNDLED_DIRS
from update_package import inspect_update,LEGACY_MANAGED_ROOTS_1042,LEGACY_MANAGED_ROOTS_1041


class PackageTests(unittest.TestCase):
    def fixture(self,root):
        source=Path(__file__).parent;build=root/'build';assets=build/'_internal/config/db';assets.mkdir(parents=True)
        (build/'pslog.exe').write_bytes(b'MZ synthetic test fixture')
        (build/'exec').mkdir();(build/'exec/PSLogUpdater.exe').write_bytes(b'MZ updater fixture')
        (build/'docs').mkdir();(build/'meta').mkdir()
        for name in REQUIRED:(assets/name).write_bytes((source/'config/db'/name).read_bytes())
        pdfdir=build/'_internal/config/templates/pdf';pdfdir.mkdir(parents=True)
        for name in PDFS:(pdfdir/name).write_bytes((source/'config/templates/pdf'/name).read_bytes())
        for folder in BUNDLED_DIRS:
            for src in (source/folder).rglob('*'):
                if src.is_file():
                    dst=build/'_internal'/src.relative_to(source);dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(src.read_bytes())
        return source,build

    def test_normal_package_has_clean_root_meta_and_empty_docs(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source,build=self.fixture(root);out=root/'delivery.zip';package(build,source,out)
            with zipfile.ZipFile(out) as z:
                names=z.namelist()
                root_files={n[len('PSLog/'):] for n in names if n.startswith('PSLog/') and not n.endswith('/') and '/' not in n[len('PSLog/'): ]}
                self.assertEqual(root_files,{'pslog.exe'})
                self.assertIn('PSLog/docs/',names)
                self.assertFalse(any(n.startswith('PSLog/docs/') and n!='PSLog/docs/' for n in names))
                self.assertIn('PSLog/meta/BUILD_INFO.json',names)
                self.assertIn('PSLog/meta/PSLOG_UPDATE_INFO.json',names)
                for retired in ('USER_GUIDE.txt','SAVE_LOCATION.md','WINDOWS_CHECKLIST.txt','BUILD_INFO.json','PSLOG_UPDATE_INFO.json','PSLogUpdater.exe'):
                    self.assertNotIn('PSLog/'+retired,names)
                self.assertIn('PSLog/exec/PSLogUpdater.exe',names)
                info=json.loads(z.read('PSLog/meta/BUILD_INFO.json'))
                self.assertEqual(info['windows_manual_test'],'未確認');self.assertEqual(info['version'],'1.14')
                update=json.loads(z.read('PSLog/meta/PSLOG_UPDATE_INFO.json'))
                self.assertEqual(update['version'],'1.14');self.assertEqual(update['product'],'PSLog')
                self.assertIn('exec/PSLogUpdater.exe',update['files']);self.assertIn('meta/BUILD_INFO.json',update['files'])
            self.assertEqual(inspect_update(out).version,'1.14')
            with self.assertRaises(FileExistsError):package(build,source,out)
            (build/'config').mkdir(exist_ok=True);(build/'config/conf.cfg').write_text('private')
            with self.assertRaises(ValueError):package(build,source,root/'bad.zip')
            self.assertFalse((root/'bad.zip').exists())

    def test_package_script_runs_directly_from_tools_path(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source,build=self.fixture(root);out=root/'direct-cli.zip'
            script=source/'tools/package_windows.py'
            result=subprocess.run([sys.executable,str(script),str(build),str(source),str(out)],cwd=root,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertTrue(out.is_file());self.assertEqual(inspect_update(out).version,'1.14')

    def test_1042_bridge_uses_exact_old_root_layout(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source,build=self.fixture(root);out=root/'bridge1042.zip';package(build,source,out,bridge_from='1.042')
            with zipfile.ZipFile(out) as z:
                names=z.namelist();update=json.loads(z.read('PSLog/PSLOG_UPDATE_INFO.json'))
                self.assertEqual(tuple(update['managed_roots']),LEGACY_MANAGED_ROOTS_1042)
                self.assertIn('PSLog/exec/PSLogUpdater.exe',names);self.assertNotIn('PSLog/PSLogUpdater.exe',names)
                self.assertIn('PSLog/BUILD_INFO.json',names);self.assertNotIn('PSLog/meta/BUILD_INFO.json',names)
                self.assertIn('PSLog/USER_GUIDE.txt',names)
            self.assertEqual(inspect_update(out).version,'1.14')

    def test_1041_bridge_has_only_legacy_root_updater(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source,build=self.fixture(root);out=root/'bridge1041.zip';package(build,source,out,bridge_from='1.041')
            with zipfile.ZipFile(out) as z:
                names=z.namelist();update=json.loads(z.read('PSLog/PSLOG_UPDATE_INFO.json'))
                self.assertEqual(tuple(update['managed_roots']),LEGACY_MANAGED_ROOTS_1041)
                self.assertIn('PSLog/PSLogUpdater.exe',names);self.assertNotIn('PSLog/exec/PSLogUpdater.exe',names)
            self.assertEqual(inspect_update(out).version,'1.14')

    def test_package_script_bridge_cli(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source,build=self.fixture(root);script=source/'tools/package_windows.py'
            for old in ('1.041','1.042'):
                out=root/f'bridge-{old}.zip'
                result=subprocess.run([sys.executable,str(script),str(build),str(source),str(out),'--bridge-from',old],cwd=root,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
                self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(inspect_update(out).version,'1.14')

    def test_build_script_emits_one_normal_windows_zip(self):
        text=(Path(__file__).parent/'build-windows.ps1').read_text(encoding='utf-8-sig')
        self.assertIn('PSLog_${version}_Windows_',text)
        self.assertNotIn('PSLog_1.10_Windows_',text)
        self.assertIn('from storage import VERSION; print(VERSION)',text)
        self.assertNotIn('UpdateFrom_',text)
        self.assertEqual(text.count('tools/package_windows.py dist/pslog . $releaseFile'),1)

    def test_stale_meta_and_unknown_root_file_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source,build=self.fixture(root)
            (build/'meta/stale.json').write_text('{}')
            with self.assertRaisesRegex(ValueError,'meta'):package(build,source,root/'bad.zip')
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source,build=self.fixture(root)
            (build/'stray.txt').write_text('stray')
            with self.assertRaisesRegex(ValueError,'ルート'):package(build,source,root/'bad.zip')

    def test_missing_assets_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'pslog.exe').write_bytes(b'MZ fixture')
            with self.assertRaises(ValueError):package(root,Path(__file__).parent,root/'bad.zip')

    def test_unknown_config_and_modified_reference_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source,build=self.fixture(root)
            for relative in ('config/blacklist.txt','config/rules/personal.txt','_internal/config/db/private.csv'):
                extra=build/relative;extra.parent.mkdir(parents=True,exist_ok=True);extra.write_text('private')
                with self.assertRaisesRegex(ValueError,'設定データ|利用者データ'):package(build,source,root/'bad.zip')
                self.assertFalse((root/'bad.zip').exists());extra.unlink()
            assets=build/'_internal/config/db';(assets/'locations.json').write_text('modified')
            with self.assertRaisesRegex(ValueError,'一致しません'):package(build,source,root/'bad.zip')
            self.assertFalse((root/'bad.zip').exists())

    def test_output_inside_build_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            with self.assertRaisesRegex(ValueError,'外に指定'):package(root,Path(__file__).parent,root/'release.zip')


if __name__=='__main__':unittest.main()
