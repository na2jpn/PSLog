import unittest
from pathlib import Path
from types import SimpleNamespace
from PySide6.QtWidgets import QApplication
from model import QSO
from contest_area_ui import AreaDialog,area_hint
from locations import load
from contest import entries
from contest_rules import score,default_rule

class ContestAreaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([])
        cls.root=Path(__file__).parent;cls.db=load(cls.root)
    def selection(self,count=1):
        return SimpleNamespace(rows=[('JA1AAA',QSO('2026-09-12','12:00','7','CW','JA1YYY','599','599','','','note','JCC 010101'),Path('/sample.txt'),i+1) for i in range(count)])
    def test_exact_master_match_and_leading_zero(self):
        for code in ('JCC 010101','010101','jcg 01002B','JCG 01002'):
            self.assertEqual(area_hint(self.db,code)['area'],'01')
        for code in ('','JCG 010101','JCC 999999','10','010101 extra','PM95'):
            self.assertIsNone(area_hint(self.db,code))
    def test_selection_pagination_and_existing_values(self):
        selection=self.selection(102);original=repr(selection.rows)
        d=AreaDialog(self.root,selection);self.addCleanup(d.deleteLater)
        work={(str(Path('/sample.txt')),1):{'area':'manual','received':'11M'}}
        d.apply_to(work);self.assertEqual(len(work),1)
        d.select_page();d.move(1);self.assertEqual(d.table.rowCount(),2);d.select_page();d.apply_to(work)
        self.assertEqual(len(work),102);self.assertEqual(work[(str(Path('/sample.txt')),1)]['area'],'manual')
        self.assertEqual(work[(str(Path('/sample.txt')),1)]['received'],'11M')
        self.assertEqual(work[(str(Path('/sample.txt')),102)]['area'],'01');self.assertEqual(repr(selection.rows),original)
    def test_area_condition_scoring_and_missing_area(self):
        selection=self.selection();rule=default_rule();rule['multi1']['kind']='off'
        rule['conditions']=[{'when':{'field':'area','op':'eq','value':'01'},'points':2}]
        self.assertIsNone(score(rule,entries(selection,{})).total)
        d=AreaDialog(self.root,selection);self.addCleanup(d.deleteLater);d.select_page();work={};d.apply_to(work)
        self.assertEqual(score(rule,entries(selection,work)).total,2)
