import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from PySide6.QtWidgets import QApplication,QMessageBox
from contest_rules import RuleStore,default_rule
from contest_rule_ui import RuleEditor
from contest_scoring_ui import ScoringDialog
from rule_pack_ui import RulePackDialog
from rule_pack import build
import test_rule_pack
class UiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def test_pack_preview_apply_and_no_repeat(self):
        with tempfile.TemporaryDirectory() as d:
            store=RuleStore(d);path=Path(d)/'pack.zip';build(path,[(default_rule(),1,'1.01')],'test')
            dialog=RulePackDialog(store,path);self.assertEqual(dialog.table.item(0,3).text(),'追加')
            with patch.object(QMessageBox,'question',return_value=QMessageBox.Yes):dialog.apply()
            self.assertEqual(len(store.files()),1);self.assertFalse(dialog.apply_button.isEnabled());dialog.deleteLater()
    def test_v2_editor_keeps_sets_and_visual_changes(self):
        with tempfile.TemporaryDirectory() as d:
            r=test_rule_pack.ScoringTests().rule();dialog=RuleEditor(RuleStore(d),r);self.assertEqual(dialog.collect(),r);self.assertFalse(dialog.m1.isEnabled())
            sets=ScoringDialog(r['scoring']);sets.bonus.setValue(1000);sets.table.cellWidget(0,0).setText('zone');sets.apply();self.assertEqual(sets.value['bonus'],1000);self.assertEqual(sets.value['multipliers'][0]['id'],'zone');sets.deleteLater();dialog.deleteLater()
