import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from PySide6.QtWidgets import QApplication
from pota_ui import PotaDialog
from storage import Repository,save_settings
from model import QSO
from main import Window

class PotaGuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def test_selection_filters_and_direct_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=Repository(tmp);q=QSO('2026-01-01','12:00','7','SSB','JA1YYY','59','59','Japan','Japan','POTA 日本語','')
            for own in ['JH1HST','JH1HST/1','JQ7FIU']:repo.open(repo.path_for(own,'',q.date)).append(q)
            d=PotaDialog(repo,'JH1HST');self.assertEqual(d.own.count(),2);self.assertEqual(d.logs.count(),1)
            d.write();self.assertIn('公園番号',d.status.text())
            d.parks.setText('JA-1222 JA-1234');d.check_all(True);d.rmks.setChecked(True);d.word.setText('pota');d.write()
            self.assertEqual(len(list((Path(tmp)/'output'/'pota').glob('*.adi'))),2);self.assertFalse(d.save_button.isEnabled())
            d.own.setCurrentText('JH1HST/1');self.assertEqual(d.station.text(),'JH1HST/1');self.assertEqual(d.logs.count(),1)
            d.search.setText('no matches');self.assertEqual(d.logs.count(),0);d.close()
    def test_special_menu_and_contest_layout(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_settings(tmp,{'own':'JH1HST'});w=Window(tmp)
            special=next(m for m in w.menu_refs if m.title()=='特殊なエクスポート')
            self.assertEqual([a.text() for a in special.actions()],['POTA提出用ADIFファイル','SOTA提出用CSVファイル'])
            with patch('pota_ui.PotaDialog') as dialog:
                special.actions()[0].trigger();self.assertTrue(dialog.return_value.exec.called)
            contest=next(m for m in w.menu_refs if m.title()=='コンテスト');self.assertEqual([a.text() for a in contest.actions()],['コンテスト提出ログ作成…','コンテストルール表示…','コンテストルール管理・編集…','Cabrillo出力テンプレート管理・編集…']);w.close()
