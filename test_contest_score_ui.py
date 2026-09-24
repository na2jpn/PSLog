import unittest
from types import SimpleNamespace
from pathlib import Path
from PySide6.QtWidgets import QApplication
from contest_score_ui import ScoreView
from contest_rules import score,default_rule
from model import QSO

class ScoreViewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def make(self,n):
        rows=[];entries=[]
        for i in range(n):
            call=f'JA1A{i}'
            q=QSO('2026-09-11','12:00','7','CW',call,'599','599','Japan','Soka Saitama Japan','001A')
            rows.append(('JH1HST',q,Path('/sample/log.txt'),i+1))
            entries.append(dict(call=call,band='7',mode='CW',exchange='001A'))
        return SimpleNamespace(rows=rows),entries
    def test_every_row_reachable_and_filter_keeps_source_number(self):
        selection,entries=self.make(205);entries[204]['mode']='FUTURE'
        result=score(default_rule(),entries);view=ScoreView();self.addCleanup(view.deleteLater)
        view.set_result(selection,result,{})
        self.assertEqual(view.table.rowCount(),100)
        view.next.click();self.assertEqual(view.table.item(0,0).text(),'101')
        view.next.click();self.assertEqual(view.table.rowCount(),5)
        self.assertEqual(view.table.item(4,0).text(),'205');self.assertIn('未分類',view.table.item(4,6).text())
        self.assertFalse(view.next.isEnabled())
        view.only_pending.setChecked(True);self.assertEqual(view.table.rowCount(),1)
        self.assertEqual(view.table.item(0,0).text(),'205')
        self.assertIn('原本行: 205',view.table.item(0,0).toolTip())
    def test_multiplier_judgement_column_marks_new_and_existing(self):
        selection,entries=self.make(3);entries[0]['exchange']='11';entries[1]['exchange']='11';entries[2]['exchange']='12'
        result=score(default_rule(),entries);view=ScoreView();self.addCleanup(view.deleteLater);view.set_result(selection,result,{})
        self.assertEqual(view.table.horizontalHeaderItem(5).text(),'マルチ判定')
        self.assertEqual([view.table.item(i,5).text() for i in range(3)],['新規','既出','新規'])
    def test_pending_candidate_and_refresh_remove_stale_rows(self):
        selection,entries=self.make(102);result=score(default_rule(),entries)
        view=ScoreView();self.addCleanup(view.deleteLater)
        view.set_result(selection,result,{(str(Path('/sample/log.txt')),102):{'status':'候補・要確認'}})
        view.only_pending.setChecked(True);self.assertEqual(view.table.item(0,0).text(),'102')
        self.assertEqual(view.table.item(0,3).text(),'未確定')
        view.set_result(selection,result,{});self.assertEqual(view.table.rowCount(),0)
        view.only_pending.setChecked(False);view.next.click();view.clear()
        self.assertEqual(view.table.rowCount(),0);self.assertFalse(view.previous.isEnabled());self.assertFalse(view.next.isEnabled())
