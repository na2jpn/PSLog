import json,os,tempfile,unittest,uuid
from pathlib import Path
from unittest.mock import patch
from backup_retention import clean_book,clean_history,clean_award,prune_safety,maintain
from storage import Repository,operation_lock
class RetentionTests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.repo=Repository(self.root)
 def tearDown(self):self.tmp.cleanup()
 def file(self,relative,n=0):
  p=self.root/relative;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(str(n));os.utime(p,ns=(n*1000000000,n*1000000000));return p
 def backup(self,folder,ident,n):return self.file(f'{folder}/{ident}.txt.20261022-000000-{n:06d}-12345678.bak',n)
 def test_existing_backups_per_log_and_manual_preserved(self):
  for n in range(15):self.backup('bak','2026_JX1XXX',n);self.backup('bak','2025_JX1XXX',n)
  custom=self.file('bak/my_notes.bak');clean_book(self.repo.book,10)
  self.assertEqual(len(list(self.repo.bak.glob('*.bak'))),21);self.assertTrue(custom.exists());self.assertFalse((self.repo.bak/'2026_JX1XXX.txt.20261022-000000-000000-12345678.bak').exists())
 def test_completed_journals_bounded_by_kind(self):
  for folder in ['batch_recovery','year_moves','year_moves_flr']:
   for n in range(12):self.file(f'bak/{folder}/{n:032x}.done.json',n)
  clean_book(self.repo.book,10)
  for folder in ['batch_recovery','year_moves','year_moves_flr']:self.assertEqual(len(list((self.repo.bak/folder).glob('*.done.json'))),10)
 def test_pending_prevents_history_deletion(self):
  for n in range(12):self.file(f'bak/batch_recovery/{n:032x}.done.json',n)
  p=self.file('bak/batch_recovery/unsafe.pending.json');clean_book(self.repo.book,10)
  self.assertTrue(p.exists());self.assertEqual(len(list(p.parent.glob('*.done.json'))),12)
 def test_safety_two_plus_explicitly_protected(self):
  old=self.file('bak/full-restore-safety/PSLog_before_full_restore_20261022-000000_00000000.zip')
  self.file(str(old.relative_to(self.root))+'.keep')
  for n in range(1,6):self.file(f'bak/full-restore-safety/PSLog_before_full_restore_20261022-000000_{n:08x}.zip',n)
  manual=self.file('bak/full-restore-safety/my_backup.zip');prune_safety(self.root,old.parent)
  self.assertTrue(old.exists());self.assertTrue(manual.exists());self.assertEqual(len(list(old.parent.glob('*.zip'))),4)
 def test_merge_backups_use_same_per_log_limit(self):
  for n in range(14):self.backup('bak/logbook_bak','2026_JX1XXX',n)
  clean_book(self.repo.book,10);self.assertEqual(len(list((self.repo.bak/'logbook_bak').glob('*.bak'))),10)
 def test_symlinked_folder_and_files_untouched(self):
  with tempfile.TemporaryDirectory() as external:
   outside=Path(external);f=outside/'00000000000000000000000000000000.done.json';f.write_text('evidence')
   self.repo.bak.mkdir(exist_ok=True)
   try:(self.repo.bak/'batch_recovery').symlink_to(outside,target_is_directory=True)
   except OSError:self.skipTest('Symlink privilege unavailable')
   clean_book(self.repo.book,1);self.assertTrue(f.exists())
 def test_setting_changes_existing_files_on_startup_maintenance(self):
  for n in range(14):self.backup('bak','2026_JX1XXX',n)
  (self.root/'config').mkdir();(self.root/'config/conf.cfg').write_text(json.dumps({'backup_keep':10}))
  self.assertFalse(maintain(self.root,10));self.assertEqual(len(list(self.repo.bak.glob('*.bak'))),10)
 def test_successful_operation_prunes_but_failed_operation_does_not(self):
  for n in range(35):self.file(f'bak/batch_recovery/{n:032x}.done.json',n)
  with self.assertRaises(RuntimeError):
   with operation_lock(self.repo.book):raise RuntimeError('save failed')
  self.assertEqual(len(list((self.repo.bak/'batch_recovery').glob('*'))),35)
  with operation_lock(self.repo.book):pass
  self.assertEqual(len(list((self.repo.bak/'batch_recovery').glob('*'))),30)
 def test_award_ledgers_separate_and_keep_current(self):
  folder=self.root/'config/awards/JCC';current=self.file('config/awards/JCC/0123456789abcdef.json')
  for n in range(14):self.file(f'config/awards/JCC/0123456789abcdef.{n:020d}.bak',n)
  clean_award(self.root,folder,10);self.assertEqual(len(list(folder.glob('*.bak'))),10);self.assertTrue(current.exists())
 def test_history_bundled_per_file_and_pending_protection(self):
  folder=self.root/'config/rules'
  for n in range(14):self.file(f'config/rules/history/bundled/{n:020d}/test_2026.txt',n)
  pending=self.file('config/rules/.pack-pending.json');clean_history(self.root,folder,10)
  self.assertEqual(len(list((folder/'history/bundled').glob('*/*.txt'))),14);pending.unlink();clean_history(self.root,folder,10)
  self.assertEqual(len(list((folder/'history/bundled').glob('*/*.txt'))),10)
 def test_retention_error_does_not_turn_save_into_failure(self):
  with patch('backup_retention.clean_book',side_effect=PermissionError('denied')):
   with operation_lock(self.repo.book):pass
 def test_full_zip_does_not_include_backup_tree(self):
  from full_backup import files
  self.file('bak/big.zip');self.file('logbook/2026_JX1XXX.txt');self.assertFalse(any('bak' in p.relative_to(self.root).parts for p in files(self.root)))
 def test_failed_pending_recovery_preserves_backups(self):
  for n in range(35):self.backup('bak','2026_JX1XXX',n)
  pending=self.file('bak/batch_recovery/unsafe.pending.json');self.assertTrue(maintain(self.root,10));self.assertTrue(pending.exists());self.assertEqual(len(list(self.repo.bak.glob('*.bak'))),35)
 def test_successful_safety_zip_creation_caps_at_two(self):
  from full_backup import create_restore_safety
  self.file('config/conf.cfg').write_text('{}')
  for n in range(5):create_restore_safety(self.repo)
  self.assertEqual(len(list((self.repo.bak/'full-restore-safety').glob('*.zip'))),2)
 def test_rule_pack_history_and_unknown_contents(self):
  folder=self.root/'config/rules'
  for n in range(14):self.file(f'config/rules/history/pack-{n:032x}/test_2026.txt',n)
  custom=self.file('config/rules/history/pack-00000000000000000000000000000000/notes.md');clean_history(self.root,folder,10)
  self.assertTrue(custom.exists());self.assertEqual(len(list((folder/'history').glob('pack-*/*.txt'))),10)
 def test_cabrillo_and_location_histories_are_bounded(self):
  (self.root/'config').mkdir(exist_ok=True);(self.root/'config/conf.cfg').write_text(json.dumps({'backup_keep':10}))
  for n in range(14):
   self.file(f'config/templates/cabrillo/history/bundled/{n:020d}/cq.txt',n)
   self.file(f'config/db/history/location_overrides_{n:020d}.json',n)
  self.assertFalse(maintain(self.root,10))
  self.assertEqual(len(list((self.root/'config/templates/cabrillo/history/bundled').glob('*/*.txt'))),10)
  self.assertEqual(len(list((self.root/'config/db/history').glob('*.json'))),10)
 def test_failed_full_restore_marks_safety_zip_protected(self):
  from full_backup import create
  from full_restore import restore
  from storage import StorageError
  cfg=self.root/'config/conf.cfg';cfg.parent.mkdir(exist_ok=True);cfg.write_text('{}')
  source,_=create(self.repo,self.root/'manual.zip');cfg.write_text('{"changed":true}')
  with patch('full_restore.replace_bytes',side_effect=OSError('write failed')):
   with self.assertRaises(StorageError):restore(self.repo,source)
  marked=list((self.repo.bak/'full-restore-safety').glob('*.zip.keep'));self.assertEqual(len(marked),1);self.assertTrue(marked[0].with_suffix('').exists())
if __name__=='__main__':unittest.main()
