import io,json,tempfile,unittest
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED

from storage import Repository,save_settings
from model import QSO
from full_backup import create,MANIFEST
from full_restore import inspect_backup,restore


class FullRestoreTests(unittest.TestCase):
    def make_log(self,repo,call='JA1AAA',minute='00'):
        p=repo.path_for('JH1HST','','2026-09-16')
        repo.open(p).append(QSO('2026-09-16',f'12:{minute}','7','CW',call,'599','599','Japan','Japan','',''))
        return p

    def test_format1_manifest_and_restore_old_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);src=Repository(base/'src');dst=Repository(base/'dst')
            save_settings(src.root,{'own':'JH1HST','backup_keep':10})
            old=self.make_log(src,'JA1OLD','01')
            custom=src.root/'config'/'rules'/'my_private_2026.txt';custom.parent.mkdir(parents=True,exist_ok=True)
            # Keep custom config generic here; rule validation is tested by the real stores elsewhere.
            custom.unlink(missing_ok=True)
            backup,_=create(src,base/'old.zip')
            with ZipFile(backup) as z:
                self.assertIn(MANIFEST,z.namelist())
                info=json.loads(z.read(MANIFEST));self.assertEqual(info['format_version'],1)
                self.assertEqual(info['pslog_version'],'1.14')

            save_settings(dst.root,{'own':'JH1NEW','backup_keep':30})
            current=self.make_log(dst,'JA1NEW','02')
            extra=dst.book/'2025_JH1HST_.txt';extra.parent.mkdir(parents=True,exist_ok=True);extra.write_bytes(b'extra')
            plan=inspect_backup(dst,backup)
            self.assertFalse(plan.legacy)
            result=restore(dst,plan)
            self.assertTrue(result['safety_backup'].is_file())
            self.assertIn(b'JA1OLD',current.read_bytes())
            self.assertFalse(extra.exists())
            self.assertEqual(json.loads((dst.root/'config/conf.cfg').read_text('utf-8'))['own'],'JH1HST')

    def test_legacy_zip_restores_user_state_and_preserves_ambiguous_bundled_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);repo=Repository(base/'app')
            save_settings(repo.root,{'own':'CURRENT'})
            current=self.make_log(repo,'JA1NOW','03')
            # all_ja_2026.txt is bundled by the current source tree.  A manifest-less
            # old copy must not silently replace the current version.
            legacy_rule=b'{"old":"legacy bundled or user-edited copy"}\n'
            legacy_log=(b'\xef\xbb\xbf2026-09-16 | 12:04 JST | 7 | CW | JA1OLD | 599 | 599 | Japan | Japan |  |  \\\\\r\n')
            zpath=base/'legacy.zip'
            with ZipFile(zpath,'w',ZIP_DEFLATED) as z:
                z.writestr('config/conf.cfg',json.dumps({'own':'OLD'}).encode())
                z.writestr('config/rules/all_ja_2026.txt',legacy_rule)
                z.writestr('logbook/'+current.name,legacy_log)
            bundled=(Path(__file__).parent/'config/rules/all_ja_2026.txt').read_bytes()
            target=repo.root/'config/rules/all_ja_2026.txt';target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(bundled)
            plan=inspect_backup(repo,zpath)
            self.assertTrue(plan.legacy);self.assertIn('config/rules/all_ja_2026.txt',plan.legacy_conflicts)
            result=restore(repo,plan)
            self.assertEqual(target.read_bytes(),bundled)
            staged=result['legacy_conflict_folder']/'rules/all_ja_2026.txt'
            self.assertEqual(staged.read_bytes(),legacy_rule)
            self.assertEqual(json.loads((repo.root/'config/conf.cfg').read_text())['own'],'OLD')
            self.assertIn(b'JA1OLD',current.read_bytes())


    def test_format1_distinguishes_bundled_default_from_user_modified_rule(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);src=Repository(base/'src');dst=Repository(base/'dst')
            save_settings(src.root,{'own':'JH1HST'});self.make_log(src,'JA1SRC','05')
            bundle=Path(__file__).parent/'config/rules/all_ja_2026.txt'
            original=bundle.read_text('utf-8')
            rules=src.root/'config/rules';rules.mkdir(parents=True,exist_ok=True)
            # One untouched bundled file should be tagged bundled.
            untouched=Path(__file__).parent/'config/rules/all_saga_2026.txt'
            (rules/'all_saga_2026.txt').write_bytes(untouched.read_bytes())
            # A valid user edit of a bundled rule must be tagged user and restored.
            import json as _json
            obj=_json.loads(original);obj['name']=obj['name']+' USER EDIT'
            modified=(_json.dumps(obj,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
            (rules/'all_ja_2026.txt').write_bytes(modified)
            backup,_=create(src,base/'rules.zip')
            with ZipFile(backup) as z:
                info=json.loads(z.read(MANIFEST));role={e['path']:e['role'] for e in info['entries']}
            self.assertEqual(role['config/rules/all_saga_2026.txt'],'bundled')
            self.assertEqual(role['config/rules/all_ja_2026.txt'],'user')

            # Destination starts with current defaults.
            dr=dst.root/'config/rules';dr.mkdir(parents=True,exist_ok=True)
            (dr/'all_saga_2026.txt').write_bytes(untouched.read_bytes())
            (dr/'all_ja_2026.txt').write_bytes(bundle.read_bytes())
            save_settings(dst.root,{'own':'DST'})
            plan=inspect_backup(dst,backup);result=restore(dst,plan)
            self.assertEqual((dr/'all_ja_2026.txt').read_bytes(),modified)
            self.assertEqual((dr/'all_saga_2026.txt').read_bytes(),untouched.read_bytes())
            self.assertGreaterEqual(result['kept_current_defaults'],1)


    def test_restore_into_fresh_empty_data_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);src=Repository(base/'src');save_settings(src.root,{'own':'JH1HST'});self.make_log(src,'JA1FRESH','06')
            backup,_=create(src,base/'fresh.zip')
            dst=Repository(base/'empty')
            plan=inspect_backup(dst,backup);result=restore(dst,plan)
            self.assertIsNone(result['safety_backup'])
            restored=dst.book/'2026_JH1HST_.txt'
            self.assertIn(b'JA1FRESH',restored.read_bytes())

    def test_rejects_traversal_and_future_format(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);repo=Repository(base/'app')
            bad=base/'bad.zip'
            with ZipFile(bad,'w') as z:z.writestr('../escape.txt',b'x')
            with self.assertRaisesRegex(Exception,'不正なパス'):inspect_backup(repo,bad)

            future=base/'future.zip'
            info={'format':'PSLog full backup','format_version':99,'pslog_version':'9.99','created_at_jst':'x','entries':[]}
            with ZipFile(future,'w') as z:
                z.writestr(MANIFEST,json.dumps(info));z.writestr('config/conf.cfg',b'{}')
            with self.assertRaisesRegex(Exception,'未対応のバックアップ形式'):inspect_backup(repo,future)

    def test_manifest_hash_tamper_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);repo=Repository(base/'src');save_settings(repo.root,{'own':'JH1HST'});self.make_log(repo)
            original,_=create(repo,base/'good.zip')
            tampered=base/'tampered.zip'
            with ZipFile(original) as src,ZipFile(tampered,'w',ZIP_DEFLATED) as dst:
                for info in src.infolist():
                    data=src.read(info)
                    if info.filename.startswith('logbook/'):data=data+b'X'
                    dst.writestr(info.filename,data)
            with self.assertRaisesRegex(Exception,'一致しません'):inspect_backup(Repository(base/'dst'),tampered)


if __name__=='__main__':unittest.main()
