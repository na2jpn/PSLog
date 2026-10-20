import os,unittest,tempfile,time
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
from dataclasses import replace
from unittest.mock import patch,MagicMock
from model import QSO
from storage import Repository
import his_qth_batch as b
from test_v118 import response
class Fix6Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.repo=Repository(Path(self.tmp.name));self.q=QSO('2026-01-02','10:00','7','CW','JH1HST','599','599','Japan','Soka Saitama Japan','','')
 def add(self,date,stamp,call='JH1HST'):
  q=replace(self.q,date=date,time=stamp,call=call);p=self.repo.path_for('JH1HST','',date);self.repo.open(p).append(q);return p
 def test_datetime_sort_blank_ignores_old_cursor(self):
  p=self.add('2026-01-02','10:02');self.add('2026-01-02','10:00');old=self.add('2025-12-31','23:59')
  folder=self.repo.root/'var';folder.mkdir(exist_ok=True);(folder/'his_qth_progress.json').write_text('{"old":"cursor"}')
  for _ in range(2):
   rows,_=b.lookup_batch(self.repo,[p,old],'JH1HST',limit=1,lookup=lambda c:response(c),interval=0)
   self.assertEqual(rows[0].qso.date,'2025-12-31')
  self.assertEqual((folder/'his_qth_progress.json').read_text(),'{"old":"cursor"}')
 def test_inclusive_minute_boundary_before_limit(self):
  p=self.add('2026-01-02','10:02');self.add('2026-01-02','10:00');self.add('2026-01-02','10:01','JJ1JPE');self.add('2026-01-02','10:01','JH1FNU')
  rows,_=b.lookup_batch(self.repo,[p],'JH1HST',limit=2,start_at='202601021001',lookup=lambda c:response(c),interval=0)
  self.assertEqual([c.qso.time for c in rows],['10:01','10:01']);self.assertNotEqual(rows[0].qso.call,rows[1].qso.call)
 def test_invalid_datetime_never_calls_network(self):
  for value in ('202602301200','202601012400','202601011260','20260101','２０２６０１０１１２００','202601011200x'):
   with self.assertRaises(ValueError):b.validate_start(value)
  self.assertEqual(b.validate_start(''),'');self.assertEqual(b.validate_start('202402291200'),'202402291200')
class Fix6GuiTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  from PySide6.QtWidgets import QApplication
  cls.app=QApplication.instance() or QApplication([])
 def setUp(self):
  from his_qth_batch_ui import HisQthBatchDialog
  self.tmp=tempfile.TemporaryDirectory();self.repo=Repository(Path(self.tmp.name));self.d=HisQthBatchDialog(self.repo,'JH1HST')
 def tearDown(self):
  from PySide6.QtCore import QCoreApplication,QEvent
  self.d.rows=[];self.d.thread=None;self.d.reject();self.d.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);self.tmp.cleanup()
 def candidate(self):
  from model import QSO
  q=QSO('2026-01-02','10:01','7','CW','JH1HST','599','599','Japan','Soka Saitama Japan','','')
  c=MagicMock();c.qso=q;c.after=replace(q,his_qth='Soka Saitama Japan');return c
 def test_choices_default_and_label(self):
  self.assertEqual([self.d.limit.itemText(i) for i in range(self.d.limit.count())],['10','20','30','40','50','70','90']);self.assertEqual(self.d.limit.currentText(),'20');self.assertFalse(self.d.limit.isEditable());self.assertEqual(self.d.start_at.text(),'');self.assertEqual(self.d.save_button.text(),'チェックした結果をログに反映');self.d.busy(True);self.assertFalse(self.d.lookup_button.isEnabled());self.d.busy(False);self.assertTrue(self.d.lookup_button.isEnabled())
 def test_yes_same_minute_cooldown_blocks_even_direct_call(self):
  from PySide6.QtWidgets import QMessageBox
  self.d.rows=[self.candidate()];self.d.thread=MagicMock()
  with patch('his_qth_batch_ui.QMessageBox.question',return_value=QMessageBox.StandardButton.Yes):self.d.finished_work()
  self.assertEqual(self.d.start_at.text(),'202601021001');self.assertFalse(self.d.lookup_button.isEnabled());self.assertTrue(self.d.save_button.isEnabled());self.assertIn('30秒',self.d.lookup_button.text())
  with patch('his_qth_batch_ui.LookupThread') as worker:self.d.run();worker.assert_not_called()
  self.d.cooldown_until=time.monotonic()-1;self.d.update_cooldown();self.assertTrue(self.d.lookup_button.isEnabled());self.assertEqual(self.d.lookup_button.text(),'取得・確認')
 def test_no_keeps_start_and_empty_result_no_prompt(self):
  from PySide6.QtWidgets import QMessageBox
  self.d.start_at.setText('202501010000');self.d.rows=[self.candidate()];self.d.thread=MagicMock()
  with patch('his_qth_batch_ui.QMessageBox.question',return_value=QMessageBox.StandardButton.No):self.d.finished_work()
  self.assertEqual(self.d.start_at.text(),'202501010000');self.d.rows=[];self.d.thread=MagicMock()
  with patch('his_qth_batch_ui.QMessageBox.question') as question:self.d.finished_work();question.assert_not_called()
if __name__=='__main__':unittest.main()
