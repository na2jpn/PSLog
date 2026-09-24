import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from PySide6.QtWidgets import QApplication
from main import Window
from storage import save_settings,load_settings
from contest_rules import RuleStore,default_rule,dumps,loads
from contest_rule_ui import RulesDialog,RuleEditor
from contest_ui import ContestDialog
from storage import Repository

class V101Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def test_latest_values_saved_at_record_and_restored(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_settings(tmp,{'own':'JH1HST','confirm_record':False})
            w=Window(tmp);w.set_text('band','50');w.set_text('mode','CW');w.set_text('my_qth','Soka Saitama Japan')
            w.call.setText('JA1AAA');w.start_qso();w.record()
            saved=load_settings(tmp)
            self.assertEqual([saved[k] for k in ('band','mode','my_qth')],['50','CW','Soka Saitama Japan'])
            w.timer.stop();w.deleteLater() # do not rely on closeEvent for this assertion
            other=Window(tmp)
            self.assertEqual(other.text('band'),'50');self.assertEqual(other.text('mode'),'CW')
            other.call.setText('JA1BBB');other.start_qso();self.assertEqual(other.text('sent'),'599')
            other.keep_band.setChecked(False);other.keep_mode.setChecked(False);other.start_qso()
            self.assertEqual(other.text('band'),'');self.assertEqual(other.text('mode'),'')
            other.close()
    def test_log_success_is_not_reported_as_failure_when_preferences_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_settings(tmp,{'own':'JH1HST','confirm_record':False})
            w=Window(tmp);w.call.setText('JA1AAA');w.start_qso()
            with patch('main.save_settings',side_effect=OSError('test settings error')):w.record()
            self.assertIn('交信は保存済み',w.status.text());self.assertEqual(len(w.rows),1);w.close()
    def test_years_kana_order_old_rules_and_editor_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=RuleStore(tmp)
            for ident,name,reading,year in [('shiga','滋賀コンテスト','シガコンテスト',2025),('shiga','滋賀コンテスト','しがコンテスト',2026),('allja','ALL JA','ALL JA',2026),('tokyo','東京コンテスト','とうきょうコンテスト',2026)]:
                r=default_rule();r.update(id=ident,name=name,sort_name=reading,year=year);store.save(r)
            ordered=[store.read(p)[0] for p in store.files()]
            self.assertEqual([(r['id'],r['year']) for r in ordered],[('allja',2026),('shiga',2026),('shiga',2025),('tokyo',2026)])
            old=default_rule();self.assertEqual(loads(dumps(old)),old)
            editor=RuleEditor(store,old);self.assertEqual(editor.collect(),old)
            editor.sort_name.setText('てすと');self.assertEqual(editor.collect()['sort_name'],'てすと');editor.deleteLater()
            d=RulesDialog(tmp);self.assertEqual(d.list.item(1).text(),'（ユーザー定義）滋賀コンテスト（2026） [shiga]');d.reject()
            wizard=ContestDialog(Repository(tmp),'JH1HST');self.assertEqual(wizard.rules.itemText(2),'（ユーザー定義）滋賀コンテスト（2026）');wizard.reject()
