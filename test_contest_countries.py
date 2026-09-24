import unittest
from types import SimpleNamespace
from pathlib import Path
from PySide6.QtWidgets import QApplication
from contest_country_ui import CountryDialog
from contest import entries
from contest_rules import score,default_rule
from model import QSO

class ContestCountryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def selection(self):
        rows=[]
        for i in range(102):
            q=QSO('2026-09-11','12:00','7','CW','JH1HST/JD1' if i==101 else 'DL5TI','599','599','','','')
            rows.append(('JA1AAA',q,Path('/sample.txt'),i+1))
        return SimpleNamespace(rows=rows)
    def test_explicit_selection_pagination_and_manual_preservation(self):
        selection=self.selection();d=CountryDialog(Path(__file__).parent,selection);self.addCleanup(d.deleteLater)
        work={(str(Path('/sample.txt')),1):{'country':'Manual','area':'TOKYO','prefix':'DL5'}}
        d.apply_to(work);self.assertNotIn('continent',work[(str(Path('/sample.txt')),1)])
        d.select_page();d.move(1);d.select_page();self.assertEqual(len(d.selected),101)
        d.apply_to(work);self.assertEqual(work[(str(Path('/sample.txt')),1)]['country'],'Manual');self.assertNotIn('continent',work[(str(Path('/sample.txt')),1)])
        self.assertEqual(work[(str(Path('/sample.txt')),1)]['area'],'TOKYO');self.assertEqual(work[(str(Path('/sample.txt')),1)]['prefix'],'DL5')
        self.assertEqual(work[(str(Path('/sample.txt')),101)]['continent'],'EU');self.assertNotIn((str(Path('/sample.txt')),102),work)
    def test_scoring_uses_explicit_continent_and_stops_when_missing(self):
        selection=self.selection();selection.rows=selection.rows[:1]
        r=default_rule();r['multi1']['kind']='off';r['conditions']=[{'when':{'field':'continent','op':'eq','value':'EU'},'points':3}]
        self.assertIsNone(score(r,entries(selection,{})).total)
        work={(str(Path('/sample.txt')),1):{'continent':'EU','country':'Germany'}}
        self.assertEqual(score(r,entries(selection,work)).total,3)
        work[(str(Path('/sample.txt')),1)]['continent']='TYPO';self.assertIsNone(score(r,entries(selection,work)).total)
