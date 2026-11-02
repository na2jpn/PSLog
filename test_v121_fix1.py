"""Search-result contest handoff: exact rows through review and submission."""
import tempfile,unittest
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QCoreApplication,QEvent
from model import QSO
from storage import Repository
from search import Criteria,search
from contest_ui import ContestDialog,MANUAL_CONTEST,key
class ContestSearchHandoffTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.repo=Repository(self.tmp.name);self.own='JX1XXX/1';self.path=self.repo.path_for(self.own,'','2026-11-01');session=self.repo.open(self.path)
  for n in range(8):session.append(QSO('2026-11-01',f'06:{n:02d}','7','CW',f'JX2X{n}','599','599','Japan','Soka',f'{n+1:03d}A',''))
  self.hits=search(self.repo,Criteria(own=self.own)).hits[:6];self.assertEqual(len(self.hits),6);self.original=self.path.read_bytes();self.dialogs=[]
 def tearDown(self):
  for d in self.dialogs:d.timer.stop();d.cancel_score();d.close();d.deleteLater()
  QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);self.tmp.cleanup()
 def dialog(self,hits=True):
  d=ContestDialog(self.repo,self.own,hits=self.hits if hits else None);self.dialogs.append(d);d.early_rules.setCurrentIndex(d.early_rules.findData(MANUAL_CONTEST));d.manual_name.setText('テスト大会');d.manual_year.setText('2026');d.format.setCurrentText('JARL R1.0');d.advance();self.assertEqual(d.stack.currentIndex(),1);return d
 def test_six_checked_hits_advance_without_any_source_log_checked(self):
  d=self.dialog();self.assertFalse(any(d.logs.item(i).checkState().value==2 for i in range(d.logs.count())));d.advance();self.assertEqual(d.stack.currentIndex(),2,d.status.text());self.assertEqual(len(d.selection.rows),6);self.assertEqual([d.draft[key(row)]['received'] for row in d.selection.rows],[f'{n+1:03d}A' for n in range(2,8)]);self.assertEqual(self.path.read_bytes(),self.original)
 def test_search_source_controls_hidden_and_note_visible(self):
  d=self.dialog();self.assertTrue(d.source_panel.isHidden());self.assertFalse(d.imported_note.isHidden());self.assertIn('6交信',d.imported_note.text());self.assertIn('次へ',d.imported_note.text())
 def test_submission_uses_real_portable_own_and_exact_six_rows(self):
  d=self.dialog();d.advance();d.sent.setText('13L');d.fill_sent();d.confirm_page();d.advance();self.assertEqual(d.stack.currentIndex(),3,d.status.text());d.timer.stop();d.calculate();d.advance();self.assertEqual(d.stack.currentIndex(),4,d.status.text());self.assertEqual(d.submission.fields['callsign'].text(),self.own);self.assertIn(self.own,d.submission.overview.text());self.assertNotIn('__search_checked__',d.submission.overview.text());self.assertEqual(len(d.selection.rows),6)
  p=d.submission
  for field,value in dict(contest='Test Contest',category='TEST',name='Test Operator',address='Soka',opplace='埼玉県草加市',power='10',signature='Test Operator',email='test@example.com',licenseclass='第2級アマチュア無線技士',powertype='定格出力').items():
   widget=p.fields[field]
   if hasattr(widget,'setCurrentText'):widget.setCurrentText(value)
   else:widget.setText(value)
  p.fields['oath'].setChecked(True);p.prepare();self.assertIsNotNone(p.prepared,p.status.text());payload=p.prepared.data.decode('cp932');self.assertIn(self.own,payload);self.assertEqual(payload.count('JX2X'),6);self.assertEqual(self.path.read_bytes(),self.original)
 def test_snapshot_change_blocks_progress(self):
  d=self.dialog();self.path.write_bytes(self.original+b'\r\n');d.advance();self.assertEqual(d.stack.currentIndex(),1);self.assertIsNone(d.selection);self.assertTrue(d.status.text())
 def test_normal_entry_still_shows_source_controls(self):
  d=self.dialog(False);self.assertFalse(d.source_panel.isHidden());self.assertTrue(d.imported_note.isHidden());d.advance();self.assertEqual(d.stack.currentIndex(),1);self.assertTrue(d.status.text())
 def test_cached_target_keeps_review_and_does_not_expand_to_all_file_rows(self):
  d=self.dialog();d.advance();row=d.selection.rows[0];d.draft[key(row)]['received']='999A';d.go_back();d.advance();self.assertEqual(len(d.selection.rows),6);self.assertEqual(d.draft[key(row)]['received'],'999A');self.assertEqual(self.path.read_bytes(),self.original)
 def test_registered_all_osaka_rule_advances_with_imported_six(self):
  d=self.dialog();source=Path(__file__).parent/'config/rules/all_osaka_2026.txt';target=self.repo.root/'config/rules/all_osaka_2026.txt';target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(source.read_bytes());d.rules.addItem('オール大阪2026',str(target));d.early_rules.addItem('オール大阪2026',str(target));d.early_rules.setCurrentIndex(d.early_rules.count()-1);d.advance();self.assertEqual(d.stack.currentIndex(),2,d.status.text());self.assertEqual(len(d.selection.rows),6);self.assertEqual(d.loaded_scope[0],self.own);self.assertEqual(d.table.rowCount(),6)
if __name__=='__main__':unittest.main()
