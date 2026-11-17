import ast
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from product_info import COPYRIGHT, ORGANIZATION
from storage import VERSION
from tools import windows_signing as signing
from tools.windows_version_info import write_version_info
import test_windows_package as fixtures

ROOT = Path(__file__).resolve().parent
THUMBPRINT = '12ab' * 10


class SigningTests(unittest.TestCase):
    def files(self, root):
        paths = [root/'pslog.exe', root/'exec/PSLogUpdater.exe']
        for path in paths:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'MZ test fixture')
        return paths

    def test_both_executables_signed_and_verified_with_timestamp(self):
        with tempfile.TemporaryDirectory() as folder:
            paths = self.files(Path(folder))
            with patch.object(signing, 'find_signtool', return_value='signtool.exe'), patch.object(signing.subprocess, 'run') as run:
                result = signing.sign_executables(paths, '  '+THUMBPRINT+'\n', machine_store=True)
            self.assertEqual(result, [p.resolve() for p in paths])
            self.assertEqual(run.call_count, 4)
            for index, path in enumerate(paths):
                args = run.call_args_list[index*2].args[0]
                self.assertEqual(args[:8], ['signtool.exe','sign','/sha1',THUMBPRINT,'/fd','SHA256','/tr',signing.DEFAULT_TIMESTAMP_URL])
                self.assertIn('/sm', args)
                self.assertEqual(args[args.index('/td')+1], 'SHA256')
                self.assertEqual(args[args.index('/d')+1], 'PSLog')
                self.assertEqual(args[-1], str(path.resolve()))
                self.assertEqual(run.call_args_list[index*2].kwargs, {'check':True})
                self.assertEqual(run.call_args_list[index*2+1].args[0], ['signtool.exe','verify','/pa','/all','/tw','/v',str(path.resolve())])

    def test_invalid_parameters_do_not_launch_signtool(self):
        with tempfile.TemporaryDirectory() as folder:
            paths = self.files(Path(folder))
            with patch.object(signing.subprocess, 'run') as run:
                for thumb in ('', 'auto', 'a'*39, 'z'*40):
                    with self.subTest(thumb=thumb), self.assertRaises(ValueError):
                        signing.sign_executables(paths, thumb)
                for url in ('', 'file:///test', 'https://example.invalid/ bad'):
                    with self.subTest(url=url), self.assertRaises(ValueError):
                        signing.sign_executables(paths, THUMBPRINT, timestamp_url=url)
                with self.assertRaises(FileNotFoundError):
                    signing.sign_executables([paths[0], Path(folder)/'missing.exe'], THUMBPRINT)
                run.assert_not_called()

    def test_sign_or_verify_warning_stops_remaining_work(self):
        with tempfile.TemporaryDirectory() as folder:
            paths = self.files(Path(folder))
            for fail_index in (0,1):
                def execute(args, **kwargs):
                    execute.count += 1
                    if execute.count == fail_index+1:
                        raise subprocess.CalledProcessError(2,args)
                execute.count = 0
                with patch.object(signing,'find_signtool',return_value='signtool.exe'), patch.object(signing.subprocess,'run',side_effect=execute):
                    with self.assertRaises(subprocess.CalledProcessError):
                        signing.sign_executables(paths,THUMBPRINT)
                self.assertEqual(execute.count,fail_index+1)

    def test_find_signtool_uses_newest_numeric_sdk_or_explicit_path(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            for version in ('10.0.9.0','10.0.10.0','preview'):
                path=root/'Windows Kits/10/bin'/version/'x64/signtool.exe'
                path.parent.mkdir(parents=True);path.write_bytes(b'fixture')
            with patch.object(signing.shutil,'which',return_value=None), patch.dict(signing.os.environ,{'ProgramFiles(x86)':folder}):
                self.assertIn('10.0.10.0',signing.find_signtool())
            tool=root/'custom.exe';tool.write_bytes(b'fixture')
            self.assertEqual(signing.find_signtool(tool),str(tool.resolve()))
            with self.assertRaises(FileNotFoundError):signing.find_signtool(root/'absent.exe')

    def test_windows_version_resources_share_author_and_version(self):
        with tempfile.TemporaryDirectory() as folder:
            for updater, filename in ((False,'pslog.exe'),(True,'PSLogUpdater.exe')):
                path=Path(folder)/filename
                write_version_info(path,updater=updater)
                tree=ast.parse(path.read_text(encoding='utf-8'))
                fields={ast.literal_eval(node.args[0]):ast.literal_eval(node.args[1]) for node in ast.walk(tree) if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='StringStruct'}
                self.assertEqual(fields['LegalCopyright'],COPYRIGHT)
                self.assertEqual(fields['CompanyName'],ORGANIZATION)
                self.assertEqual(fields['ProductVersion'],VERSION)
                self.assertEqual(fields['OriginalFilename'],filename)

    def test_signed_bytes_hashed_without_modification_by_packager(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source,build=fixtures.PackageTests().fixture(root)
            files=[build/'pslog.exe',build/'exec/PSLogUpdater.exe']
            def execute(args,**kwargs):
                if args[1]=='sign':
                    path=Path(args[-1]);path.write_bytes(path.read_bytes()+b' signed fixture')
            with patch.object(signing,'find_signtool',return_value='signtool.exe'), patch.object(signing.subprocess,'run',side_effect=execute):
                signing.sign_executables(files,THUMBPRINT)
            out=root/'signed.zip';fixtures.package(build,source,out)
            with zipfile.ZipFile(out) as z:
                manifest=json.loads(z.read('PSLog/meta/versionup.json'))
                for path in files:
                    rel=path.relative_to(build).as_posix();data=path.read_bytes()
                    self.assertEqual(z.read('PSLog/'+rel),data)
                    self.assertEqual(manifest['files'][rel],hashlib.sha256(data).hexdigest())


if __name__=='__main__':unittest.main()
