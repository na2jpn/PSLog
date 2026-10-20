import os,tempfile,unittest
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
from unittest.mock import patch,MagicMock
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from storage import Repository
from model import QSO
from dxcc_check_ui import DxccCheckDialog
from his_qth_batch_ui import HisQthBatchDialog
from dxcc_check import aggregate
class V118GuiTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.repo=Repository(Path(self.tmp.name));q=QSO('2026-10-17','10:00','7','RTTY','JJ1JPE','599','599','Japan','Soka Saitama Japan','','');self.path=self.repo.path_for('JH1HST/1','',q.date);self.repo.open(self.path).append(q)
 def test_initial_dxcc_unselected_does_not_open_logs(self):
  with patch.object(self.repo,'open',side_effect=AssertionError('unexpected initial read')):
   d=DxccCheckDialog(self.repo);self.assertEqual(d.own.currentIndex(),0);self.assertEqual(d.table.rowCount(),0);self.assertIsNone(d.result);d.reject();d.deleteLater()
 def test_default_qth_count_and_code_check(self):
  d=HisQthBatchDialog(self.repo,'JH1HST');self.assertEqual(int(d.limit.currentText()),20);self.assertTrue(d.include_code.isChecked());self.assertEqual(d.logs.count(),1);self.assertEqual(d.logs.item(0).checkState(),Qt.CheckState.Unchecked);d.reject();d.deleteLater()
 def test_dxcc_drilldown_hands_call_and_actual_portable_filename(self):
  d=DxccCheckDialog(self.repo);r=aggregate(self.repo,'JH1HST');d.render(r);self.assertIn('1',d.summary.text());hit=r.entities[0].hits[0]
  with patch('search_ui.SearchDialog') as dialog:
   obj=dialog.return_value;d.open_search(hit,d);self.assertEqual(dialog.call_args.kwargs['filename'],self.path.name);self.assertEqual(dialog.call_args.args[1],'JH1HST/1');obj.filters['call'].setText.assert_called_once_with('JJ1JPE');obj.run_search.assert_called_once();obj.exec.assert_called_once()
  d.reject();d.deleteLater()
if __name__=='__main__':unittest.main()
