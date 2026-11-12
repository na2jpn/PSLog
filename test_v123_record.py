import tempfile,unittest
from unittest.mock import patch
from PySide6.QtWidgets import QApplication
from storage import save_settings
from model import now_jst
from main import Window
class HistoricalTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);save_settings(self.tmp.name,{'own':'JX1XXX','confirm_record':False});self.w=Window(self.tmp.name);self.addCleanup(self.w.close)
 def test_past_date_is_preserved_at_call_set_and_saved_to_year(self):
  w=self.w;w.fields['date'].setText('2023/05/10');w.fields['date'].textEdited.emit('2023/05/10');w.fields['time'].setText('12:34');self.assertIn('2023_JX1XXX_',w.path.text());w.call.setText('JX2XXX');w.start_qso();self.assertEqual(w.text('date'),'2023/05/10');self.assertEqual(w.text('time'),'12:34');w.set_text('band','7');w.set_text('mode','CW');w.set_text('sent','599');w.set_text('received','599')
  with patch.object(w,'_confirm_record_time',return_value='keep'):w.record()
  p=w.repo.path_for('JX1XXX','','2023-05-10');self.assertTrue(p.exists());q=w.repo.open(p).log.lines[0].qso;self.assertEqual((q.date,q.time),('2023-05-10','12:34'));self.assertIn(p.name,w.path.text())
 def test_changed_year_and_incomplete_date_safe_no_file_created(self):
  for date in ['2','2024/02/29','2025-05-01','bad','2023/01/01']:
   self.w.fields['date'].setText(date);self.w.fields['date'].textEdited.emit(date);self.w.update_path()
  self.assertIn('2023_',self.w.path.text());self.assertFalse(any(self.w.repo.book.glob('2023_*.txt')))
 def test_today_clears_historical_mode(self):
  w=self.w;w.fields['date'].setText('2023-01-01');w.fields['date'].textEdited.emit('2023-01-01');today=now_jst().strftime('%Y-%m-%d');w.fields['date'].setText(today);w.fields['date'].textEdited.emit(today);w.call.setText('JX2XXX');w.start_qso();self.assertEqual(w.text('date'),today);self.assertFalse(w._historical_date)
 def test_workspace_reload_clears_historical_state_with_date(self):
  self.w._date_manually_edited('2023-01-01');self.assertTrue(self.w._historical_date);self.w._load_workspace(self.w.active_workspace_index);self.assertFalse(self.w._historical_date);self.w.call.setText('JX2XXX');self.w.start_qso();self.assertEqual(self.w.text('date'),now_jst().strftime('%Y-%m-%d'))
 def test_no_qsl_tool_is_directly_below_batch(self):
  actions=self.w.menuBar().actions();menu=next(a.menu() for a in actions if a.text()=='ツール');self.assertEqual([a.text() for a in menu.actions()][:2],['QSL受領一括処理','No QSLリスト'])
