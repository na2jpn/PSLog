import tempfile,unittest,json
from copy import deepcopy
from pathlib import Path
from dataclasses import replace
from unittest.mock import patch
from PySide6.QtWidgets import QApplication,QMessageBox
from contest_rules import default_rule,score,validate,loads,RuleStore
from contest import candidates,select_logs
from contest_rule_ui import RuleEditor,ConditionDialog,RulesDialog
from contest_ui import ContestDialog
from storage import Repository,ExternalChange
from model import QSO

class RuleTests(unittest.TestCase):
    def entry(self,**kw):return dict(dict(call='JA1AAA',band='7',mode='SSB',exchange='001A'),**kw)
    def cond(self,f,op,v):return {'field':f,'op':op,'value':v}
    def test_priority_and_duplicate(self):
        r=default_rule();r['conditions']=[{'when':{'all':[self.cond('mode','eq','SSB'),self.cond('digits_length','ge',3)]},'points':2},{'when':{'all':[]},'points':5}]
        s=score(r,[self.entry(),self.entry(),self.entry(call='JA2AAA',mode='CW')]);self.assertEqual([x['points'] for x in s.rows],[2,0,5]);self.assertEqual(s.total,7);self.assertEqual(s.rows[0]['reason'],'条件 1')
        r['duplicate']['by_mode']=True;s=score(r,[self.entry(),self.entry(mode='CW')]);self.assertEqual(s.points,7)
    def test_second_multiplier_zero_fixed_and_conditional(self):
        r=default_rule();r['multi2'].update(kind='bands',condition=self.cond('area','eq','SHIGA'))
        s=score(r,[self.entry(area='TOKYO')]);self.assertEqual(s.multi2,0);self.assertEqual(s.total,0);self.assertFalse(s.problems)
        s=score(r,[self.entry(area='SHIGA'),self.entry(band='14',area='SHIGA')]);self.assertEqual(s.multi2,2);self.assertEqual(s.total,8)
        r['multi2'].update(kind='fixed',value=0);self.assertEqual(score(r,[self.entry()]).total,0)
    def test_unresolved_not_zero(self):
        r=default_rule();self.assertIsNone(score(r,[self.entry(mode='FUTURE')]).total)
        r['conditions']=[{'when':self.cond('area','eq','SHIGA'),'points':2}];s=score(r,[self.entry()]);self.assertIsNone(s.total);self.assertIn('area',s.problems[0])
    def test_digit_groups_leading_zero_and_formula(self):
        r=default_rule();r['multi1']['kind']='digits';s=score(r,[self.entry(exchange='H001')]);self.assertEqual(s.rows[0]['multi'],'001')
        self.assertIsNone(score(r,[self.entry(exchange='11A22')]).total)
        r['multi1']['kind']='whole';data=[self.entry(),self.entry(call='JA2AAA',exchange='002B'),self.entry(band='14')]
        self.assertEqual(score(r,data).total,9);r['formula']='band_sum';self.assertEqual(score(r,data).total,5)
    def test_strict_json_rejects_unknown_keys_and_executable_text(self):
        r=default_rule();r['unknown']=1
        with self.assertRaises(ValueError):validate(r)
        r=default_rule();r['multi2']['kind']='eval'
        with self.assertRaises(ValueError):validate(r)
        with self.assertRaises(ValueError):loads('{"schema":1,"schema":1}')
        r=default_rule();r['points']['phone']=float('nan')
        with self.assertRaises(ValueError):validate(r)
        r=default_rule();r['points']['phone']=1.00000001
        with self.assertRaises(ValueError):validate(r)
    def test_store_collision_history_and_external_change(self):
        with tempfile.TemporaryDirectory() as d:
            store=RuleStore(d);r=default_rule();path,s=store.save(r)
            with self.assertRaises(ExternalChange):store.save(r)
            original=path.read_bytes();r['name']='changed';path,s=store.save(r,path,s);history=list((store.folder/'history').glob('*.txt'));self.assertEqual(history[0].read_bytes(),original)
            path.write_bytes(path.read_bytes()+b' ')
            with self.assertRaises(ExternalChange):store.save(r,path,s)
            r['id']='../bad'
            with self.assertRaises(ValueError):store.save(r)
    def test_candidates_keep_nonnumber_notes_out(self):
        text='FD BURO.R hQSL 001A H101 PM95 08HW JA1AAA/1 7.050 2026/09/10'
        self.assertEqual(candidates(text,'FD'),['001A','H101','PM95','08HW'])

class ContestUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.repo=Repository(self.tmp.name);self.q=QSO('2026-01-01','00:00','7','SSB','JA1AAA','59','59','Japan','Tokyo Japan','FD 001A BURO','');self.path=self.repo.path_for('JH1HST/1','',self.q.date);self.repo.open(self.path).append(self.q)
    def test_minute_filter_portable_and_invalid_date(self):
        s=select_logs(self.repo,[self.path],'JH1HST/1','202601010000','202601010000','FD');self.assertEqual(len(s.rows),1)
        with self.assertRaises(ValueError):select_logs(self.repo,[self.path],'JH1HST')
        with self.assertRaises(ValueError):select_logs(self.repo,[self.path],'JH1HST/1','202602300000')
    def test_wizard_back_keeps_draft_and_10_row_pages(self):
        for i in range(101):self.repo.open(self.path).append(replace(self.q,call='JA2AAA'))
        original=self.path.read_bytes();d=ContestDialog(self.repo,'JH1HST/1');d.advance();d.check_all(True);d.advance();self.assertEqual(d.stack.currentIndex(),2);self.assertEqual(d.table.rowCount(),10)
        d.table.item(0,5).setText('MANUAL');d.extract();self.assertEqual(d.table.item(0,5).text(),'MANUAL');self.assertEqual(d.table.item(1,5).text(),'001A');self.assertGreater(d.pending_review_count(),10);d.confirm_page();self.assertEqual(d.pending_review_count(),0);d.go_back();d.advance();self.assertEqual(d.table.item(0,5).text(),'MANUAL')
        for _ in range(10):d.move_page(1)
        self.assertEqual(d.table.rowCount(),2);self.assertEqual(original,self.path.read_bytes());d.deleteLater()
    def test_rmks_can_be_blind_copied_to_received_with_confirmation(self):
        d=ContestDialog(self.repo,'JH1HST/1');d.advance();d.check_all(True);d.advance()
        with patch.object(QMessageBox,'question',return_value=QMessageBox.Yes):d.fill_received_from_rmks()
        row=d.selection.rows[0];draft=d.draft[(str(row[2]),row[3])]
        self.assertEqual(draft['received'],'FD 001A BURO')
        self.assertEqual(draft['status'],'手入力（RMKS一括）')
        self.assertEqual(d.pending_review_count(),0)
        d.deleteLater()

    def test_manager_editor_roundtrip_and_invalid_json(self):
        store=RuleStore(self.tmp.name);e=RuleEditor(store);e.ident.setText('custom');e.m2.setCurrentIndex(1);e.factor.setValue(0);e.save();self.assertIsNotNone(e.saved_path);r,s=store.read(e.saved_path);self.assertEqual(r['multi2']['value'],0)
        e.raw.setPlainText('{bad');e.raw.document().setModified(True);e.save();self.assertIn('JSON',e.status.text());self.assertEqual(store.read(e.saved_path)[0],r);e.from_json();self.assertIn('不正',e.status.text());e.deleteLater()
        m=RulesDialog(self.tmp.name);self.assertEqual(m.list.count(),1);m.deleteLater()
    def test_condition_editor_and_scoring_connection(self):
        c=ConditionDialog({'all':[]});c.field.setCurrentIndex(5);c.op.setCurrentIndex(4);c.value.setText('4');c.add_leaf();c.apply();self.assertEqual(c.result_value,{'all':[{'field':'length','op':'ge','value':4}]});c.deleteLater()
        r=default_rule();r['multi2'].update(kind='fixed',value=0);RuleStore(self.tmp.name).save(r)
        d=ContestDialog(self.repo,'JH1HST/1');d.advance();d.check_all(True);d.advance();d.extract();d.advance();d.rules.setCurrentIndex(1);d.calculate();self.assertIsNone(d.result.total);self.assertIn('#b32020',d.result_label.text());d.confirm_page();d.calculate();self.assertEqual(d.result.total,0);self.assertIn('総得点 0',d.result_label.text());d.deleteLater()

    def test_target_change_cancel_and_reload_after_external_change(self):
        d=ContestDialog(self.repo,'JH1HST/1');d.advance();d.check_all(True);d.advance();d.table.item(0,5).setText('001A');d.go_back();d.rmks.setText('FD')
        with patch.object(QMessageBox,'question',return_value=QMessageBox.No):d.advance()
        self.assertEqual(d.stack.currentIndex(),1);self.assertTrue(d.draft)
        d.rmks.clear();self.path.write_bytes(self.path.read_bytes()+b'\n');d.advance();self.assertIn('変更',d.status.text())
        with patch.object(QMessageBox,'question',return_value=QMessageBox.Yes):d.reload_target()
        self.assertFalse(d.draft);d.advance();self.assertEqual(d.stack.currentIndex(),2);d.deleteLater()
