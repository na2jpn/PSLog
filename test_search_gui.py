import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import unittest
import tempfile
from unittest.mock import patch
from PySide6.QtWidgets import QApplication,QMessageBox
from PySide6.QtCore import Qt,QTimer
from PySide6.QtTest import QTest
from storage import Repository,save_settings
from model import QSO
from search_ui import SearchDialog,EditDialog,DeleteDialog,DetailDialog,detail_text
from main import Window

class SearchGuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.repo=Repository(self.tmp.name)
        self.q=QSO('2026-01-01','00:05','7','CW','JA1YYY','599','599','Japan','Old QTH Japan','BURO','')
        self.path=self.repo.path_for('JH1HST','',self.q.date)
        self.repo.open(self.path).append(self.q)
        self.d=SearchDialog(self.repo,'JH1HST');self.addCleanup(self.d.close)
        self.assertEqual(self.d.filters['own'].currentText(),'JH1HST');self.assertTrue(self.d.portable.isChecked())
        self.d.run_search();self.d.table.selectRow(0)
    def test_edit_validation_and_refresh(self):
        e=EditDialog(self.d.selected());e.inputs['date'].setText('2026-02-30');e.save()
        self.assertFalse(e.saved);self.assertTrue(e.error.text())
        e.inputs['date'].setText('2026-01-01');e.inputs['mode'].setText('RTTY')
        self.assertEqual(e.inputs['sent'].text(),'599')
        e.inputs['remarks'].setText('BURO.R');e.save();self.assertTrue(e.saved)
        self.d.run_search();self.assertFalse(self.d.edit_button.isEnabled())
        self.assertEqual(self.d.model.hits[0].qso.remarks,'BURO.R')
        self.d.table.selectRow(0);self.d.filters['call'].setText('JA2')
        self.assertEqual(self.d.model.rowCount(),0);self.assertFalse(self.d.delete_button.isEnabled())
    def test_cancel_and_explicit_delete(self):
        raw=self.path.read_bytes();d=DeleteDialog(self.d.selected());d.show();self.app.processEvents()
        QTest.keyClick(d,Qt.Key.Key_Return);self.app.processEvents()
        self.assertFalse(d.saved);self.assertEqual(self.path.read_bytes(),raw)
        d=DeleteDialog(self.d.selected());d.delete_button.click()
        self.assertTrue(d.saved);self.assertEqual(len(self.repo.open(self.path).log.records),0)
        self.assertTrue(self.repo.backups(self.path))
    def test_dirty_cancel_and_external_edit(self):
        e=EditDialog(self.d.selected());e.inputs['remarks'].setText('hQSL.R')
        with patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.Yes):e.reject()
        self.assertFalse(e.saved)
        e=EditDialog(self.d.selected());e.inputs['remarks'].setText('hQSL.R')
        raw=self.path.read_bytes()+b'\r\n';self.path.write_bytes(raw);e.save()
        self.assertFalse(e.saved);self.assertTrue(e.error.text());self.assertEqual(self.path.read_bytes(),raw)

    def test_result_columns_and_max_display_limit(self):
        self.assertEqual(self.d.model.columns,['選択','DATE','TIME JST','相手コール','BAND','MODE','RMKS','HisQTH','MyQTH','元ログ'])
        self.assertEqual(self.d.max_results.text(),'1000')
        qs=[]
        for i in range(1005):
            qs.append(QSO('2026-01-01','00:05','7','CW',f'JA1{i:04d}','599','599',f'His QTH {i}',f'My QTH {i}',f'RMKS {i}',''))
        self.path.write_bytes(('\ufeff'+'\r\n'.join(q.to_ps() for q in qs)+'\r\n').encode('utf-8'))
        self.d.run_search()
        self.assertEqual(self.d.model.rowCount(),1000)
        self.assertIn('1,005件中 1,000件表示',self.d.status.text())
        first=self.d.model.hits[0].qso
        self.assertEqual(self.d.model.data(self.d.model.index(0,6)),first.remarks)
        self.assertEqual(self.d.model.data(self.d.model.index(0,7)),first.his_qth)
        self.assertEqual(self.d.model.data(self.d.model.index(0,8)),first.my_qth)
        self.assertEqual(self.d.model.data(self.d.model.index(0,0),Qt.ItemDataRole.CheckStateRole),Qt.CheckState.Checked)
        self.d.model.setData(self.d.model.index(0,0),Qt.CheckState.Unchecked,Qt.ItemDataRole.CheckStateRole)
        self.assertEqual(len(self.d.model.checked_hits()),999)
        self.assertIn('チェック済み 999件',self.d.status.text())
        self.d.model.set_all(False);self.assertFalse(self.d.export_button.isEnabled())
        self.d.model.set_all(True);self.assertTrue(self.d.export_button.isEnabled())
        self.d.max_results.setText('10');self.d.run_search()
        self.assertEqual(self.d.model.rowCount(),10)
        self.assertIn('最大表示件数 10',self.d.status.text())
        self.d.max_results.setText('0');self.d.run_search()
        self.assertEqual(self.d.model.rowCount(),0)
        self.assertIn('最大表示件数は1以上の数字',self.d.status.text())

    def test_checked_rows_only_are_handed_to_exports(self):
        self.repo.open(self.path).append(QSO('2026-01-01','00:06','7','CW','JA1ZZZ','599','599','Japan','Old QTH Japan','BURO',''))
        self.d.run_search();self.assertEqual(self.d.model.rowCount(),2)
        self.d.model.setData(self.d.model.index(0,0),Qt.CheckState.Unchecked,Qt.ItemDataRole.CheckStateRole)
        checked=self.d.model.checked_hits();self.assertEqual(len(checked),1)
        with patch('pota_ui.PotaDialog') as dialog:
            self.d.open_pota();self.assertEqual(len(dialog.call_args.kwargs['hits']),1)
        with patch('sota_ui.SotaDialog') as dialog:
            self.d.open_sota();self.assertEqual(len(dialog.call_args.kwargs['hits']),1)
        with patch('export_ui.ExportDialog') as dialog:
            self.d.open_export();self.assertEqual(len(dialog.call_args.kwargs['hits']),1)
        with patch.object(QMessageBox,'information'),patch('activity_ui.ActivityDialog') as dialog:
            self.d.open_party();self.assertEqual(len(dialog.call_args.kwargs['hits']),1)

    def test_search_action_labels_and_bulk_delete_preview(self):
        from search_ui import CheckedDeleteDialog
        self.assertEqual(self.d.edit_button.text(),'交信を編集…')
        self.assertEqual(self.d.delete_button.text(),'削除…')
        self.assertEqual(self.d.party_button.text(),'QSOパーティへ…')
        self.assertEqual(self.d.pota_button.text(),'POTAへ…')
        self.assertEqual(self.d.sota_button.text(),'SOTAへ…')
        self.assertEqual(self.d.export_button.text(),'エクスポートへ…')
        self.assertEqual(self.d.contest_button.text(),'コンテスト提出へ…')
        preview=CheckedDeleteDialog(self.repo,[self.d.model.hits[0]]*100,self.d)
        self.addCleanup(preview.close)
        self.assertEqual(preview.table.rowCount(),100)
        self.assertEqual(preview.delete_button.text(),'100件を削除')


    def test_search_filter_layout_and_logfile_browse(self):
        labels={w.text() for w in self.d.findChildren(type(self.d.status))}
        for text in ('対象自局','対象ログファイル','相手コール','BAND','MODE','RMKS','HIS QTH','JCC/JCG','MY QTH','開始日時 JST','終了日時 JST'):
            self.assertIn(text,labels)
        self.assertEqual(self.d.file_browse_button.text(),'参照…')
        with patch('search_ui.QFileDialog.getOpenFileName',return_value=(str(self.path),'')):
            self.d.browse_log_file()
        self.assertEqual(self.d.filters['filename'].text(),self.path.name)

    def test_edit_dialog_can_delete_the_exact_record(self):
        e=EditDialog(self.d.selected());self.addCleanup(e.close)
        self.assertTrue(e.delete_button.isEnabled())
        with patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.Yes):
            e.delete_record()
        self.assertTrue(e.saved);self.assertTrue(e.deleted);self.assertIsNone(e.saved_qso)
        self.assertEqual(len(self.repo.open(self.path).log.records),0)
        self.assertTrue(self.repo.backups(self.path))

    def test_qso_detail_is_separate_and_edit_notice_preserves_main_context(self):
        h=self.d.selected();detail=DetailDialog(self.repo,h,self.d);self.addCleanup(detail.close)
        text=detail.view.toPlainText()
        self.assertIn('元ログファイル:',text);self.assertIn('QSL受領判定:',text);self.assertIn('MODE:',text)
        labels=[w.text() for w in detail.findChildren(type(self.d.status))]
        self.assertTrue(any('メイン画面へ入力する場合は、このウィンドウを閉じてください。' in x for x in labels))
        edit=EditDialog(h,self.d);self.addCleanup(edit.close)
        labels=[w.text() for w in edit.findChildren(type(self.d.status))]
        self.assertTrue(any('編集を保存またはキャンセル' in x for x in labels))

    def test_main_menu_connection_keeps_current_qth(self):
        save_settings(self.tmp.name,{'own':'JH1HST','my_qth':'Current QTH Japan'})
        w=Window(self.tmp.name)
        from search_ui import SearchDialog as RealDialog
        def make_dialog(*args):
            d=RealDialog(*args);d.run_search();d.table.selectRow(0)
            def update():
                e=EditDialog(d.selected());e.inputs['remarks'].setText('CARD.R');e.save()
                d.logs_changed.emit();d.accept()
            QTimer.singleShot(0,update)
            return d
        with patch('search_ui.SearchDialog',side_effect=make_dialog):
            actions=w.action_refs
            action=next(a for a in actions if a.text()=='ログ検索・編集')
            self.assertTrue(action.isEnabled());action.trigger()
        self.assertEqual(w.rows[0][1].remarks,'CARD.R')
        self.assertEqual(w.text('my_qth'),'Current QTH Japan');w.close()
