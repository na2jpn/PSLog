from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

from PySide6.QtWidgets import QApplication,QComboBox

from contest_rules import RuleStore,score,management_rule_label
from contest_submit_ui import SubmissionPane
from storage import Repository,VERSION
from test_ai_chikyu_2026 import r,row,ctx
from test_contest_batch10 import ExportFixture

ROOT=Path(__file__).resolve().parent

class Patch1070Tests(ExportFixture):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([])

    def test_version(self):
        self.assertEqual(VERSION,'1.14')

    def test_rule_manager_label_includes_start_month(self):
        # Source-tree tests do not seed bundled rules into an arbitrary temp
        # directory (bundled synchronization is intentionally frozen-build only).
        # Read the bundled rule from the actual source tree instead.
        store=RuleStore(ROOT)
        path=store.folder/'ai_chikyu_2026.txt'
        rule,_=store.read(path)
        self.assertEqual(management_rule_label(rule,store.display_label(rule,path)),'愛・地球博記念コンテスト（2026/9）')

    def test_standard_band_sort_checkbox_defaults_from_rule(self):
        spec=r();v=ctx();rows=[row()]
        p,before,sel,draft,info=self.fixture(spec,rows,v,opplace='Soka Japan')
        with tempfile.TemporaryDirectory() as tmp:
            fmt=QComboBox();fmt.addItem('JARL R1.0')
            wizard=SimpleNamespace(repo=Repository(tmp),format=fmt,selection=sel,draft=draft,loaded_scope=('JH1HST',),rule=spec,result=score(spec,rows,v),event_context=lambda:v,activity_name='コンテスト')
            pane=SubmissionPane(wizard);pane.set_context()
            self.assertTrue(pane.fields['sort_band_time'].isChecked())
            pane.deleteLater();fmt.deleteLater()
        normal=deepcopy(spec);normal['event']['submission']['order']='time'
        with tempfile.TemporaryDirectory() as tmp:
            fmt=QComboBox();fmt.addItem('JARL R1.0')
            wizard=SimpleNamespace(repo=Repository(tmp),format=fmt,selection=sel,draft=draft,loaded_scope=('JH1HST',),rule=normal,result=score(normal,rows,v),event_context=lambda:v,activity_name='コンテスト')
            pane=SubmissionPane(wizard);pane.set_context()
            self.assertFalse(pane.fields['sort_band_time'].isChecked())
            pane.fields['sort_band_time'].setChecked(True)
            self.assertTrue(pane.info()['sort_band_time'])
            pane.deleteLater();fmt.deleteLater()
        self.assertEqual(p.read_bytes(),before)

if __name__=='__main__':unittest.main()
