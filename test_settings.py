import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile
from PySide6.QtWidgets import QApplication,QMessageBox
from storage import Repository,save_settings,load_settings,Snapshot,ExternalChange
from model import QSO
from full_backup import create
from preferences import validate
from settings_ui import SettingsDialog
from main import Window
class SettingsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def test_save_restart_confirm_off_and_unknown_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_settings(tmp,{'own':'JH1HST','my_qth':'Old Japan','future_key':{'value':1}})
            w=Window(tmp);w.set_text('my_qth','Current Japan')
            d=SettingsDialog(w.current_settings(),w.apply_preferences);d.checks['confirm_record'].setChecked(False);d.keep.setCurrentText('10');d.save()
            self.assertEqual(w.text('my_qth'),'Current Japan');self.assertEqual(w.repo.backup_keep,10)
            w.call.setText('JA1YYY');w.start_qso()
            with patch.object(QMessageBox,'question') as confirmation:w.record();confirmation.assert_not_called()
            w.close();saved=load_settings(tmp);self.assertFalse(saved['confirm_record']);self.assertEqual(saved['future_key'],{'value':1})
            w=Window(tmp);self.assertEqual(w.text('my_qth'),'Current Japan');self.assertEqual(len(w.rows),1);w.close()
    def test_settings_failure_does_not_apply(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_settings(tmp,{'own':'JH1HST'});w=Window(tmp);d=SettingsDialog(w.current_settings(),w.apply_preferences);d.checks['confirm_record'].setChecked(False)
            with patch('main.save_settings',side_effect=OSError('disk full')):d.save()
            self.assertTrue(w.settings['confirm_record']);self.assertIn('disk full',d.error.text());d.reject();w.close()
    def test_stale_config_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_settings(tmp,{'own':'JH1HST'});path=Path(tmp)/'config/conf.cfg';snapshot=Snapshot.read(path)
            save_settings(tmp,{'own':'JH1HST/1'});raw=path.read_bytes()
            with self.assertRaisesRegex(ExternalChange,'設定ファイルの内容が変更'):save_settings(tmp,{'own':'OTHER'},snapshot)
            self.assertEqual(path.read_bytes(),raw)
    def test_monthly_skip_once_and_disabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_settings(tmp,{'own':'JH1HST'});repo=Repository(tmp)
            repo.open(repo.path_for('JH1HST','','2026-01-01')).append(QSO('2026-01-01','00:05','7','CW','JA1YYY','599','599','Japan','Japan','',''))
            w=Window(tmp);w.show()
            with patch.object(QMessageBox,'exec',return_value=0) as prompt:
                w.monthly_backup_notice();w.monthly_backup_notice();self.assertEqual(prompt.call_count,1)
            self.assertTrue(load_settings(tmp)['monthly_notice']);w.close()
            w=Window(tmp);w.show()
            with patch.object(QMessageBox,'exec') as prompt:w.monthly_backup_notice();prompt.assert_not_called()
            w.settings['monthly_backup']=False;w.settings.pop('monthly_notice')
            with patch.object(QMessageBox,'exec') as prompt:w.monthly_backup_notice();prompt.assert_not_called()
            w.close()
    def test_full_zip_and_original_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);repo=Repository(root/'app');save_settings(repo.root,{'own':'JH1HST'})
            p=repo.path_for('JH1HST','','2026-01-01');repo.open(p).append(QSO('2026-01-01','00:05','7','CW','JA1YYY','599','599','Japan','Japan','',''));raw=p.read_bytes()
            output,count=create(repo,root)
            with ZipFile(output) as z:self.assertEqual(z.read('logbook/'+p.name),raw);self.assertIn('config/conf.cfg',z.namelist());self.assertEqual(len(z.namelist()),count+1);self.assertIn('PSLOG_BACKUP_INFO.json',z.namelist())
            self.assertEqual(p.read_bytes(),raw)
            with self.assertRaises(ValueError):create(repo,repo.book)
            with patch('full_backup.replace_bytes',side_effect=OSError('disk full')):
                with self.assertRaises(OSError):create(repo,root)
            self.assertEqual(len(list(root.glob('*.zip'))),1)
    def test_full_zip_explicit_filename(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);repo=Repository(root/'app');save_settings(repo.root,{'own':'JH1HST'})
            p=repo.path_for('JH1HST','','2026-01-01')
            repo.open(p).append(QSO('2026-01-01','00:05','7','CW','JA1YYY','599','599','Japan','Japan','',''))
            target=root/'PSLog_backup_20260916-023000.zip'
            output,count=create(repo,target)
            self.assertEqual(output,target.resolve())
            self.assertTrue(target.is_file())
            with ZipFile(target) as z:self.assertIn('config/conf.cfg',z.namelist())

    def test_retention_preference_and_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=Repository(tmp);p=repo.book/'2026_JH1HST_.txt'
            for i in range(15):repo.backup(p,str(i).encode())
            repo.backup_keep=10;repo.prune(p);self.assertEqual(len(repo.backups(p)),10)
            self.assertEqual(repo.backups(p)[-1].read_bytes(),b'14')
        with self.assertRaises(ValueError):validate({'backup_keep':0})
