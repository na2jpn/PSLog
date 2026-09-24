import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import tempfile
import unittest
from PySide6.QtWidgets import QApplication
from storage import Repository,save_settings
from model import QSO
from search_ui import SearchDialog,EditDialog
from main import Window,FILE_MENU_ITEMS


class Patch09GuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def test_edit_qsl_buttons_and_rst_same_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=Repository(tmp)
            q=QSO('2026-09-21','16:48','7','CW','JH4WXV','599','599','Hikari Yamaguchi Japan','Soka Saitama Japan','33 BURO','')
            repo.open(repo.path_for('JH1HST','',q.date)).append(q)
            search=SearchDialog(repo,'JH1HST');search.run_search();search.table.selectRow(0)
            d=EditDialog(search.selected())
            self.assertIs(d.inputs['sent'].parent(),d.inputs['received'].parent())
            self.assertEqual(list(d.qsl_buttons),['LoTW.R','hQSL.R','eQSL.R','BURO.R','QRZ.R','CARD.R','Other.R'])
            d.qsl_buttons['hQSL.R'].click();self.assertEqual(d.inputs['remarks'].text(),'33 BURO hQSL.R')
            d.qsl_buttons['BURO.R'].click();self.assertEqual(d.inputs['remarks'].text(),'33 BURO.R hQSL.R')
            d.qsl_buttons['BURO.R'].click();self.assertEqual(d.inputs['remarks'].text(),'33 BURO.R hQSL.R')
            d.saved=True;d.close();search.close()

    def test_file_menu_order_and_separators(self):
        self.assertEqual(list(FILE_MENU_ITEMS),[
            '本体の場所を開く','ログを再読込',None,
            'ログファイルの場所を開く','出力ファイルの場所を開く','レポートの場所を開く',None,
            'PSLog再起動','PSLog終了'])


if __name__=='__main__':unittest.main()
