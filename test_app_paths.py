import os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from PySide6.QtWidgets import QApplication
from app_paths import data_directory,open_folder
from storage import Repository
from model import QSO

class AppPathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def test_source_and_frozen_locations_ignore_working_directory(self):
        source=data_directory()
        with tempfile.TemporaryDirectory() as folder:
            old=Path.cwd()
            try:
                os.chdir(folder);self.assertEqual(data_directory(),source)
                exe=Path(folder)/'日本語 folder'/'pslog.exe'
                with patch('sys.frozen',True,create=True),patch('sys.executable',str(exe)):
                    self.assertEqual(data_directory(),exe.parent)
                self.assertEqual(data_directory(folder),Path(folder).resolve())
            finally:os.chdir(old)
    def test_folder_failures_report_path_and_do_not_escape(self):
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/'日本語 folder'
            with patch('PySide6.QtGui.QDesktopServices.openUrl',return_value=False),patch('PySide6.QtWidgets.QMessageBox.warning') as warning:
                self.assertFalse(open_folder(None,target));self.assertIn(str(target),warning.call_args.args[2])
            with patch('pathlib.Path.mkdir',side_effect=PermissionError('denied')),patch('PySide6.QtWidgets.QMessageBox.warning') as warning:
                self.assertFalse(open_folder(None,target));self.assertIn('denied',warning.call_args.args[2])
    def test_unicode_space_long_directory_preserves_original(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            for i in range(7):root=root/('日本語の保存先 space '+str(i)*25)
            repo=Repository(root);q=QSO('2026-09-12','12:00','7','CW','JA1AAA','599','599','Japan','Soka Saitama Japan','note')
            path=repo.path_for('JH1HST/1','',q.date);repo.open(path).append(q)
            self.assertGreater(len(str(path)),260);self.assertEqual(repo.open(path).log.records[0][1],q)
