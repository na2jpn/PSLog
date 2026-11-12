import tempfile,unittest
from pathlib import Path
from PySide6.QtWidgets import QApplication,QScrollArea
from storage import Repository,StorageError,ExternalChange
from model import QSO
from no_qsl import received,has_buro,set_buro,collect,toggle
from no_qsl_ui import NoQSLDialog
from contest_rules import loads,score
from contest_event_ui import EventDialog
ROOT=Path(__file__).parent
class V123Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.repo=Repository(self.tmp.name)
 def log(self,year=2023,rows=None):
  p=self.repo.path_for('JX1XXX','',f'{year}-01-01');s=self.repo.open(p)
  for i,value in enumerate(rows or ['']):s.append(QSO(f'{year}-'+('02' if i%2 else '01')+'-01',f'12:{i%60:02d}','7','CW',f'JX2X{i}','599','599','Japan','Soka',value,'1201'))
  return p
 def test_receipts_and_buro_are_independent_tokens(self):
  for v in ['BURO.R','hQSL.R','LoTW.R','custom.R']:self.assertTrue(received(v))
  for v in ['BURO','memoBURO.Rsuffix','BURO.R/ABC','memo <<RMKS2>> hQSL.R']:self.assertFalse(received(v))
  self.assertTrue(has_buro('memo BURO'));self.assertFalse(has_buro('BURO.R'));self.assertFalse(has_buro('XBURO'))
 def test_preserve_notes_secondary_sections_and_other_marks(self):
  old='メモ Direct BURO <<RMKS2>> 13P <<RMKS3>> keep';out=set_buro(old,False);self.assertIn('メモ Direct',out);self.assertIn('<<RMKS2>> 13P <<RMKS3>> keep',out);out=set_buro(out,True);self.assertTrue(has_buro(out));self.assertEqual(set_buro(out,True),out);self.assertEqual(set_buro('BURO.R メモ',False),'BURO.R メモ')
 def test_file_month_call_filters_and_received_exclusion(self):
  p=self.log(rows=['','BURO','BURO.R','hQSL.R','CUSTOM.R']);q=self.log(2024);self.assertEqual(len(collect(self.repo,[p,q])),3);self.assertEqual(len(collect(self.repo,[p],month=2)),1);self.assertEqual(len(collect(self.repo,[p],call='jx2x0')),1);self.assertEqual(len(collect(self.repo,[p],exclude_buro=True)),1);self.assertEqual(len(collect(self.repo,[p,p])),2)
 def test_buro_toggle_backup_and_exact_undo(self):
  p=self.log(rows=['メモ <<RMKS2>> 13P','other']);old=p.read_bytes();rows=collect(self.repo,[p]);toggle(self.repo,rows[0]);new=self.repo.open(p).log.lines;self.assertTrue(has_buro(new[0].qso.remarks));self.assertEqual(new[1].raw,rows[1].raw);self.assertIn('<<RMKS2>> 13P',new[0].qso.remarks);self.assertTrue(list(self.repo.bak.glob(p.name+'.*')));toggle(self.repo,collect(self.repo,[p])[0]);self.assertEqual(p.read_bytes(),old)
 def test_external_edits_not_overwritten(self):
  p=self.log();row=collect(self.repo,[p])[0];p.write_bytes(p.read_bytes()+b'\r\n');before=p.read_bytes()
  with self.assertRaises(ExternalChange):toggle(self.repo,row)
  self.assertEqual(p.read_bytes(),before)
 def test_wrong_year_in_existing_file_is_not_moved_by_buro_edit(self):
  p=self.log();other=p.with_name('2024'+p.name[4:]);p.rename(other);before=other.read_bytes();row=collect(self.repo,[other])[0]
  with self.assertRaisesRegex(StorageError,'交信年'):toggle(self.repo,row)
  self.assertEqual(other.read_bytes(),before);self.assertFalse(p.exists())
 def test_missing_selection_wrong_type_invalid_month_rejected(self):
  with self.assertRaises(StorageError):collect(self.repo,[])
  p=self.log()
  with self.assertRaises(StorageError):collect(self.repo,[p],month=13)
  with self.assertRaises(StorageError):collect(self.repo,[self.repo.free_book/p.name])
 def test_gui_toggle_fixed_header_and_exclude_buro(self):
  p=self.log(rows=['']*80);d=NoQSLDialog(self.repo);self.addCleanup(d.deleteLater);d.set_files([p]);d.resize(900,450);d.show();d.show_rows();self.app.processEvents();self.assertEqual(d.table.rowCount(),80);y=d.table.horizontalHeader().pos().y();d.table.verticalScrollBar().setValue(500);self.assertEqual(d.table.horizontalHeader().pos().y(),y);d.clicked(0,0);self.assertEqual(d.table.item(0,0).text(),'〇');d.clicked(0,0);self.assertEqual(d.table.item(0,0).text(),'ー');d.exclude_buro.setChecked(True);d.show_rows();d.clicked(0,0);self.assertEqual(d.table.rowCount(),79);d.close()
 def test_changed_filter_blocks_edit_until_display(self):
  p=self.log();before=p.read_bytes();d=NoQSLDialog(self.repo);self.addCleanup(d.deleteLater);d.set_files([p]);d.show_rows();d.call.setText('JX2');d.clicked(0,0);self.assertEqual(p.read_bytes(),before)
 def test_qrp_official_name_wrap_and_visible_select_button(self):
  r=loads((ROOT/'config/rules/jarl_qrp_club_2026.txt').read_text(encoding='utf-8'));self.assertEqual(r['name'],'JARL QRP CLUB 2026年 QRP コンテスト');self.assertEqual(r['name'],r['event']['submission']['contest'])
  for width in [820,640]:
   d=EventDialog(r['event'],{});d.resize(width,620);d.show();self.app.processEvents();scroll=d.tabs.widget(0);self.assertIsInstance(scroll,QScrollArea);self.assertEqual(scroll.horizontalScrollBar().maximum(),0,(width,scroll.widget().minimumSizeHint()));self.assertLessEqual(d.category_button.mapTo(scroll.viewport(),d.category_button.rect().topRight()).x(),scroll.viewport().width());d.close();d.deleteLater()
 def test_qrp_power_mode_duplicates_and_end_time(self):
  r=loads((ROOT/'config/rules/jarl_qrp_club_2026.txt').read_text(encoding='utf-8'));v=dict(category='G50',entry_categories=['G50'],station_type='individual',power=4,flags={k:True for k in r['event']['required_flags']});q=dict(date='2026-11-03',time='20:59',band='50',mode='CW',own='JX1XXX',call='JX2XXX',sent='13P',exchange='106P');s=score(r,[q,dict(q,mode='SSB'),dict(q,mode='AM')],v);self.assertEqual((s.points,s.multi1,s.total),(2,1,2));self.assertIsNone(score(r,[q],dict(v,power=6)).total);self.assertEqual(score(r,[dict(q,time='21:00')],v).points,0)
