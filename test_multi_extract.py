import unittest,tempfile
from copy import deepcopy
from PySide6.QtWidgets import QApplication
from contest_rules import default_rule,score,loads,dumps,RuleStore
from contest_rule_ui import RuleEditor
from multi_extract_ui import ExtractionDialog

class ExtractionTests(unittest.TestCase):
    def rule(self):
        r=default_rule();r['multi1'].update(kind='registered',rules=[dict(when={'field':'exchange','op':'starts','value':'H'},source='exchange',kind='digits',start=0,length=2),dict(when={'all':[]},source='exchange',kind='slice',start=0,length=2)])
        return r
    def entry(self,exchange,**kw):return dict(call='JA1AAA',band='7',mode='CW',exchange=exchange,**kw)
    def test_first_match_leading_zeros_and_unmatched(self):
        r=self.rule();e=self.entry('H001');before=deepcopy(e);s=score(r,[e]);self.assertEqual(s.rows[0]['multi'],'001');self.assertIn('マルチ抽出 1',s.rows[0]['reason']);self.assertEqual(e,before)
        self.assertEqual(score(r,[self.entry('08HW')]).rows[0]['multi'],'08')
        self.assertIsNone(score(r,[self.entry('H11A22')]).total)
        r['multi1']['rules'].pop();self.assertIsNone(score(r,[self.entry('08HW')]).total)
    def test_working_source_and_missing_information(self):
        r=self.rule();r['multi1']['rules']=[dict(when={'all':[]},source='continent',kind='whole',start=0,length=2)]
        self.assertEqual(score(r,[self.entry('',continent='EU')]).rows[0]['multi'],'EU')
        self.assertIsNone(score(r,[self.entry('')]).total)
        r['multi1']['rules'][0]['source']='eval'
        with self.assertRaises(ValueError):loads(dumps(r))
    def test_gui_json_and_saved_rule_roundtrip(self):
        app=QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as root:
            r=self.rule();editor=RuleEditor(RuleStore(root),r);self.addCleanup(editor.deleteLater)
            self.assertEqual(editor.m1.currentIndex(),4);self.assertEqual(editor.collect(),r)
            d=ExtractionDialog(r['multi1']['rules']);self.addCleanup(d.deleteLater)
            d.table.selectRow(1);d.move(-1);d.apply()
            self.assertEqual(d.rules[0]['kind'],'slice')
            self.assertEqual(editor.collect(),r) # Separate dialog changes do not mutate the original.
            editor.save();saved,_=RuleStore(root).read(editor.saved_path)
            self.assertEqual(saved,r);self.assertEqual(loads(dumps(saved)),r)
