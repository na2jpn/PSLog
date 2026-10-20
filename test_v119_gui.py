import os,tempfile,unittest
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
from dataclasses import replace
from PySide6.QtWidgets import QApplication,QCheckBox
from storage import Repository
from model import QSO
from award_applications import Applications
from jccjcg_award_check import aggregate as jaggregate
from dxcc_check import aggregate
from jccjcg_award_check_ui import JccJcgAwardCheckDialog
from dxcc_check_ui import DxccCheckDialog
class V119GuiTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.repo=Repository(Path(self.tmp.name))
  q=QSO('2026-10-17','10:00','7','RTTY','JJ1JPE','599','599','Japan','Soka Saitama Japan','CARD.R','1319')
  self.path=self.repo.path_for('JH1HST','',q.date);self.repo.open(self.path).append(q);self.repo.open(self.path).append(replace(q,time='10:01',band='14',remarks=''))
  self.before=self.path.read_bytes()
 def tearDown(self):self.assertEqual(self.path.read_bytes(),self.before)
 def test_jcc_counts_check_persists_band_independently(self):
  result=jaggregate(self.repo,'JH1HST');d=JccJcgAwardCheckDialog(self.repo);d._aggregate_completed(result)
  parent=next(d.tree.topLevelItem(i) for i in range(d.tree.topLevelItemCount()) if d.tree.topLevelItem(i).text(0).startswith('13.'))
  parent.setExpanded(True);self.app.processEvents();item=next(parent.child(i) for i in range(parent.childCount()) if parent.child(i).text(1)=='1319')
  self.assertIn('QSL済 1',parent.text(3));check=d.tree.itemWidget(item,3).findChild(QCheckBox);check.setChecked(True)
  self.assertIn('申請済 1',parent.text(3));self.assertTrue(Applications(self.repo.root).checked('JH1HST','JCC','1319','*'))
  col=4+result.bands.index('7');self.assertFalse(d.tree.itemWidget(item,col).findChild(QCheckBox).isChecked())
  d.close();d=JccJcgAwardCheckDialog(self.repo);d._aggregate_completed(result);parent=next(d.tree.topLevelItem(i) for i in range(d.tree.topLevelItemCount()) if d.tree.topLevelItem(i).text(0).startswith('13.'));self.assertIn('申請済 1',parent.text(3));d.close()
 def test_dxcc_band_summary_open_and_persistence(self):
  d=DxccCheckDialog(self.repo);d.own.setCurrentIndex(d.own.findData('JH1HST'));d.render(aggregate(self.repo,'JH1HST'))
  self.assertEqual(d.table.rowCount(),1);self.assertEqual(d.table.item(0,3).text(),'1');self.assertEqual(d.table.item(0,4).text(),'2');d.table.cellWidget(0,1).setChecked(True)
  self.assertIn('申請済エンティティ数：1',d.summary.text());d.band.setCurrentIndex(d.band.findData('14'));self.assertFalse(d.table.cellWidget(0,1).isChecked());self.assertEqual(d.table.item(0,3).text(),'0')
  d.table.cellWidget(0,1).setChecked(True);self.assertIn('申請済エンティティ数：1',d.summary.text());d.close()
  d=DxccCheckDialog(self.repo);d.own.setCurrentIndex(d.own.findData('JH1HST'));d.render(aggregate(self.repo,'JH1HST'));self.assertTrue(d.table.cellWidget(0,1).isChecked());d.band.setCurrentIndex(d.band.findData('7'));self.assertFalse(d.table.cellWidget(0,1).isChecked());d.close()
if __name__=='__main__':unittest.main()
