import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication,QGroupBox,QLabel,QCheckBox
from qsl_ui import QSLDialog,QSLDetailDialog
from storage import Repository,save_settings
from model import QSO
from main import Window

class QSLGuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def test_selection_invalidation_pagination_and_detail_choice(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=Repository(tmp);q=QSO('2026-01-01','00:05','7','CW','JA1YYY','599','599','Japan','MY historical QTH','BURO','')
            for own in ['JH1HST','JH1HST/1']:repo.open(repo.path_for(own,'',q.date)).append(q)
            source=Path(tmp)/'input.txt';source.write_text('\n'.join(['2026-1-1 0:05 JA1YYY']*205))
            d=QSLDialog(repo,'JH1HST/1');d.source.setText(str(source));self.assertFalse(d.preview_button.isEnabled())
            d.zone.setCurrentText('JST');d.method.setCurrentText('BURO.R');self.assertTrue(d.preview_button.isEnabled());d.preview()
            self.assertEqual(d.table.rowCount(),100);self.assertTrue(d.next.isEnabled());self.assertIsNone(d.plan.entries[0].pick)
            d.table.selectRow(0);self.assertIn('複数候補',d.detail.toPlainText())
            detail=QSLDetailDialog(repo,d.plan,d.folder.text())
            first=detail.selector_buttons[0];second=detail.selector_buttons[1]
            self.assertIsInstance(first,QCheckBox);self.assertIsInstance(second,QCheckBox)
            self.assertFalse(first.isChecked());self.assertFalse(second.isChecked())
            first.click();self.assertEqual(d.plan.entries[0].pick,0);self.assertTrue(first.isChecked());self.assertFalse(second.isChecked())
            second.click();self.assertIsNone(d.plan.entries[0].pick);self.assertTrue(first.isChecked());self.assertTrue(second.isChecked())
            detail.cancel();self.assertIsNone(d.plan.entries[0].pick);d.close()
    def test_detail_uses_checkboxes_for_unique_and_multiple(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=Repository(tmp);source=Path(tmp)/'input.txt'
            repo.open(repo.path_for('JH1HST','','2026-01-01')).append(QSO('2026-01-01','00:05','7','CW','JA1AAA','599','599','Japan','Soka Japan','',''))
            repo.open(repo.path_for('JH1HST/1','','2026-01-01')).append(QSO('2026-01-01','00:05','7','CW','JA1BBB','599','599','Japan','Soka Japan','',''))
            repo.open(repo.path_for('JH1HST','','2026-01-01')).append(QSO('2026-01-01','00:06','7','CW','JA1BBB','599','599','Japan','Soka Japan','',''))
            source.write_text('2026-01-01 00:05 JA1AAA\n2026-01-01 00:05 JA1BBB\n',encoding='utf-8')
            from qsl_batch import prepare
            plan=prepare(repo,source,'JH1HST','JST','hQSL.R')
            detail=QSLDetailDialog(repo,plan,str(Path(tmp)/'reports'))
            self.assertIsInstance(detail.selector_buttons[0],QCheckBox)
            checks=detail.selector_buttons[1:]
            self.assertEqual(len(checks),2);self.assertTrue(all(isinstance(b,QCheckBox) for b in checks))
            checks[0].click();self.assertTrue(checks[0].isChecked());self.assertFalse(checks[1].isChecked())
            checks[1].click();self.assertTrue(checks[0].isChecked());self.assertTrue(checks[1].isChecked())
            detail.clear_all();self.assertFalse(checks[0].isChecked());self.assertFalse(checks[1].isChecked())
            detail.cancel()
    def test_explanations_default_method_and_filter_labels_are_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=QSLDialog(Repository(tmp),'JH1HST')
            titles=[g.title() for g in d.findChildren(QGroupBox)]
            self.assertIn('受領一覧TXTの形式',titles);self.assertIn('QSL更新時の扱い',titles);self.assertIn('照合できなかった場合',titles)
            labels=[x.text() for x in d.findChildren(QLabel)]
            self.assertIn('表示フィルター',labels);self.assertIn('受領一覧TXTの日時基準',labels)
            self.assertTrue(any('処理するTXTを「受領一覧TXT」で選択してください。'==x for x in labels))
            self.assertEqual(d.method.currentText(),'選択してください');self.assertFalse(d.preview_button.isEnabled())
            self.assertEqual(d.table.horizontalHeaderItem(5).text(),'BURO判定')
            self.assertEqual(d.detail_button.text(),'処理の詳細へ進む');d.close()
    def test_menu_opens_and_uses_station(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_settings(tmp,{'own':'JH1HST'});w=Window(tmp)
            with patch('qsl_ui.QSLDialog') as dialog:
                action=next(a for a in w.action_refs if a.text()=='QSL受領一括処理');self.assertTrue(action.isEnabled());action.trigger()
                self.assertEqual(dialog.call_args.args[1],'JH1HST');self.assertTrue(dialog.return_value.exec.called)
            w.close()
