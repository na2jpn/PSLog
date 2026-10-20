import os,unittest,tempfile
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
from dataclasses import replace
from unittest.mock import patch
from model import QSO
from storage import Repository,StorageError
import his_qth_batch as b

def record(address,begin='',end='',call='JA4BDY'):
 return {'listInfo':{'name':call,'tdfkCd':address,'licenseDate':begin},'detailInfo':{'validTerms':end}}
def response(*records):return {'musenInformation':{'totalCount':str(len(records))},'musen':list(records)}
class Fix7Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.repo=Repository(Path(self.tmp.name));self.q=QSO('2025-01-03','12:49','7','CW','JA4BDY','599','599','Japan','Soka Saitama Japan','','');self.path=self.repo.path_for('JH1HST','',self.q.date);self.repo.open(self.path).append(self.q)
 def run_batch(self,data,limit=20):return b.lookup_batch(self.repo,[self.path],'JH1HST',limit,lookup=lambda call:data,interval=0)[0]
 def test_same_address_collapses_and_auto_checks(self):
  rows=self.run_batch(response(record('東京都府中市','2020-01-01'),record('東京都府中市','2025-01-01')))
  self.assertEqual(len(rows),1);self.assertTrue(rows[0].selected);self.assertFalse(rows[0].ambiguous);self.assertEqual(rows[0].license_start,'2025-01-01');self.assertIsNotNone(rows[0].after)
 def test_two_localities_newest_first_unchecked_and_commit_selection(self):
  data=response(record('東京都府中市','令和2年1月1日','令和7年1月1日まで'),record('埼玉県草加市','令和6年1月1日','令和11年1月1日まで'))
  rows=self.run_batch(data,limit=1);self.assertEqual(len(rows),2);self.assertEqual(rows[0].address,'埼玉県草加市');self.assertIn('最新候補',rows[0].note);self.assertTrue(all(c.ambiguous and not c.selected for c in rows));self.assertEqual(rows[0].key,rows[1].key)
  with self.assertRaises(StorageError):b.commit(self.repo,rows)
  rows[0].selected=rows[1].selected=True
  with self.assertRaisesRegex(StorageError,'1つだけ'):b.commit(self.repo,rows)
  rows[1].selected=False;before=self.path.read_bytes();self.assertEqual(b.commit(self.repo,rows),(1,1));self.assertNotEqual(self.path.read_bytes(),before);self.assertEqual(self.repo.open(self.path).log.records[0][1].code,'1321')
 def test_dates_unknown_and_expiration_order(self):
  loc=b.load_locations(self.repo.root)
  opts=b.location_options(response(record('東京都府中市'),record('埼玉県草加市')),'JA4BDY',loc);self.assertFalse(any(o['latest'] for o in opts))
  opts=b.location_options(response(record('東京都府中市',end='2026/01/01'),record('埼玉県草加市',end='2028/01/01')),'JA4BDY',loc);self.assertEqual(opts[0]['address'],'埼玉県草加市');self.assertTrue(opts[0]['latest'])
  self.assertEqual(b.license_day('令和元年5月1日'),'2019-05-01');self.assertEqual(b.license_day('2025-01-01 ～ 2030-01-01',last=True),'2030-01-01');self.assertEqual(b.license_day('2026-02-30'),'')
 def test_different_qsos_independent_and_bad_candidate_visible(self):
  self.repo.open(self.path).append(replace(self.q,time='12:50'))
  rows=self.run_batch(response(record('東京都府中市'),record('不明な所在地')));self.assertEqual(len(rows),4);self.assertEqual(len({c.key for c in rows}),2);self.assertEqual(sum(c.after is None for c in rows),2);self.assertFalse(any(c.selected for c in rows))
class Fix7GuiTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  from PySide6.QtWidgets import QApplication
  cls.app=QApplication.instance() or QApplication([])
 def setUp(self):
  from his_qth_batch_ui import HisQthBatchDialog
  self.core=Fix7Tests();self.core.setUp();self.d=HisQthBatchDialog(self.core.repo,'JH1HST');self.d.show();self.app.processEvents()
 def tearDown(self):
  from PySide6.QtCore import QCoreApplication,QEvent
  self.d.rows=[];self.d.reject();self.d.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);self.core.doCleanups()
 def test_exclusive_checks_clear_and_choose_other(self):
  from PySide6.QtCore import Qt
  rows=self.core.run_batch(response(record('東京都府中市','2020-01-01'),record('埼玉県草加市','2025-01-01')));self.d.render(rows,'')
  first,second=self.d.table.item(0,0),self.d.table.item(1,0);self.assertFalse(self.d.save_button.isEnabled())
  first.setCheckState(Qt.CheckState.Checked);self.assertTrue(rows[0].selected);self.assertFalse(second.flags() & Qt.ItemFlag.ItemIsEnabled);self.assertEqual(self.d.selected_rows(),[rows[0]])
  second.setCheckState(Qt.CheckState.Checked);self.assertFalse(rows[1].selected)
  first.setCheckState(Qt.CheckState.Unchecked);self.assertTrue(second.flags() & Qt.ItemFlag.ItemIsEnabled);second.setCheckState(Qt.CheckState.Checked);self.assertEqual(self.d.selected_rows(),[rows[1]])
  self.d.include_code.setChecked(False);self.assertEqual(self.d.selected_rows(),[rows[1]]);self.assertEqual(rows[1].after.code,'')
  with patch('his_qth_batch_ui.QMessageBox.question',return_value=__import__('PySide6.QtWidgets',fromlist=['QMessageBox']).QMessageBox.StandardButton.Yes),patch.object(b,'commit',return_value=(1,1)) as commit:self.d.save();self.assertEqual(commit.call_args.args[1],[rows[1]])
 def test_success_clears_results_and_failure_keeps_results(self):
  from PySide6.QtWidgets import QMessageBox
  rows=self.core.run_batch(response(record('東京都府中市')));self.d.render(rows,'')
  with patch('his_qth_batch_ui.QMessageBox.question',return_value=QMessageBox.StandardButton.Yes),patch.object(b,'commit',side_effect=StorageError('locked')):self.d.save()
  self.assertEqual(self.d.table.rowCount(),1);self.assertTrue(self.d.rows);self.assertTrue(self.d.save_button.isEnabled())
  with patch('his_qth_batch_ui.QMessageBox.question',return_value=QMessageBox.StandardButton.Yes),patch.object(b,'commit',return_value=(1,1)):self.d.save()
  self.assertEqual(self.d.table.rowCount(),0);self.assertFalse(self.d.rows);self.assertFalse(self.d.save_button.isEnabled())
 def test_initial_widths_and_manual_width_survive_render(self):
  from PySide6.QtWidgets import QHeaderView
  self.assertEqual(self.d.table.columnCount(),10)
  for c in range(10):self.assertGreaterEqual(self.d.table.columnWidth(c),45);self.assertEqual(self.d.table.horizontalHeader().sectionResizeMode(c),QHeaderView.ResizeMode.Interactive)
  self.d.table.setColumnWidth(4,300);rows=self.core.run_batch(response(record('東京都府中市')));self.d.render(rows,'');self.assertEqual(self.d.table.columnWidth(4),300);self.assertTrue(rows[0].selected);self.assertTrue(self.d.save_button.isEnabled());self.assertEqual(self.d.table.item(0,6).text(),'未取得')
if __name__=='__main__':unittest.main()
