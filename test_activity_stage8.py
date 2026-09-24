import unittest,tempfile,io,zipfile,json
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from storage import Repository,Snapshot,ExternalChange
from model import QSO
from party import exchange,member,jarl_text,xlsx_bytes,hamtte_sheets,stats
from award_registry import candidate,Ledger,list_tsv
from activity_filters import band_group,mode_group
from activity_ui import ActivityDialog
class ActivityTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
 def q(self,call='JA1AAA',remarks='433.16 93HC BURO',code='JCC 1314',day='2026-09-12',time='20:00',band='430'):
  return QSO(day,time,band,'FM',call,'59','58','Kasukabe Saitama Japan','Soka Saitama Japan',remarks,code)
 def test_exchange_examples_and_no_original_changes(self):
  for s in ['HMT','ＨＭＴ','HAMUTTE','HAMTTE','はむって','ハムッテ','ﾊﾑｯﾃ','-12HMT']:self.assertTrue(member(s),s)
  self.assertFalse(member('HAM RADIO'))
  self.assertEqual(exchange('nyp','BURO NAKA 433.12 hQSL.R'),'NAKA')
  self.assertEqual(exchange('welcome','433.16 93HC BURO','58'),'93HC')
  self.assertEqual(exchange('welcome','433.16 06W','59'),'06W')
  self.assertEqual(exchange('hamtte_spring','5913 BURO','59'),'13')
  self.assertEqual(exchange('hamtte_spring','59913','599'),'13')
  self.assertEqual(exchange('hamtte_spring','-12HMT','-12'),'HMT')
  self.assertEqual(exchange('welcome','25C 26N','59'),'')
 def test_period_midnight_no_exclusion(self):
  rows=[dict(call='JA1AAA',date=d,band='430',sent='HMT',received='HMT',member=True) for d in ('2025-08-13','2025-08-14')]
  self.assertEqual(stats('hamtte_summer',rows)['units'],2)
  self.assertEqual(stats('hamtte_summer',rows+rows)['rows'],4)
  self.assertEqual(stats('hamtte_summer',rows+rows)['units'],2)
 def test_band_mode_groups(self):
  self.assertEqual(band_group('10.4G'),'1200以上');self.assertEqual(band_group('135kHz'),'3.5以下');self.assertEqual(band_group('3.8'),'3.5以下')
  self.assertEqual(mode_group('FT99'),'FT*');self.assertEqual(mode_group('NEW'),'その他')
 def test_mobile_award_units_and_received_only(self):
  q=self.q('JA1AAA/2','BURO.R','JCC 2001');row=('JH1HST',q,Path('a'),1)
  self.assertEqual(candidate('AJD',row)['unit'],'2');self.assertEqual(candidate('JCC',row)['unit'],'2001')
  q.code='JCC 100113';self.assertEqual(candidate('JCC',row)['unit'],'100113');self.assertEqual(candidate('WAKU',row)['unit'],'')
  q.code='JCC 270106';self.assertEqual(candidate('JCC',row)['unit'],'2701');self.assertEqual(candidate('WAKU',row)['unit'],'270106')
  q.remarks='BURO';self.assertFalse(candidate('JCC',row)['confirmed'])
  q.remarks='eQSL.R';self.assertTrue(candidate('JCC',row)['confirmed'])
 def test_ledger_addition_scope_and_concurrent_protection(self):
  with tempfile.TemporaryDirectory() as td:
   a=Ledger(td,'JCC','CW','JH1HST');a.import_units('1314,1312');b=Ledger(td,'JCC','CW','JH1HST');self.assertEqual(b.used(),{'1314','1312'})
   self.assertEqual(Ledger(td,'JCC','SSB','JH1HST').used(),set())
   b.application([dict(unit='1313')],'候補','123','JCC300');self.assertNotIn('1313',b.used())
   b.application([dict(unit='1313')],'認定済み','123','JCC300');self.assertIn('1313',b.used())
   with self.assertRaises(ExternalChange):a.save()
   self.assertTrue(list(b.path.parent.glob('*.bak')))
 def test_remaining_area_complement_and_no_fake_qso(self):
  with tempfile.TemporaryDirectory() as td:
   l=Ledger(td,'AJD');l.import_units('8 9',True);self.assertEqual(l.used(),set('01234567'));self.assertFalse((Path(td)/'logbook').exists())
 def test_real_ui_selection_and_export(self):
  with tempfile.TemporaryDirectory() as td:
   repo=Repository(td);p=repo.path_for('JH1HST','','2026-09-12');sess=repo.open(p);sess.append(self.q());raw=p.read_bytes()
   w=ActivityDialog(repo,'JH1HST');w.kind.setCurrentIndex(5);w.sent.setText('12HW');w.extract();self.assertEqual(len(w.rows),1,w.status.text())
   self.assertEqual(w.selected()[0]['received'],'93HC')
   for k,v in dict(name='試験',address='埼玉',signature='試験',email='test@example.com').items():w.info[k].setText(v)
   w.oath.setChecked(True);data,ext=w.output_data();self.assertEqual(ext,'.txt');self.assertIn('58 93HC',data.decode('cp932'));self.assertIn('59 12HW',data.decode('cp932'));self.assertEqual(raw,p.read_bytes())
   w.check_all(False)
   with self.assertRaises(ValueError):w.output_data()
   w.close()

 def test_qso_party_accepts_exact_search_hits(self):
  from search import Criteria,search
  with tempfile.TemporaryDirectory() as td:
   repo=Repository(td);p=repo.path_for('JH1HST','','2026-09-12');sess=repo.open(p)
   sess.append(self.q(call='JA1AAA'));sess.append(self.q(call='JA1BBB',remarks='OTHER'))
   hits=search(repo,Criteria('JH1HST',call='JA1AAA')).hits
   w=ActivityDialog(repo,'JH1HST',hits=hits)
   self.assertEqual(w.tabs.currentIndex(),1)
   self.assertEqual(len(w.rows),1);self.assertEqual(w.rows[0]['call'],'JA1AAA')
   self.assertIn('ログ検索でチェックした交信',w.status.text())
   w.extract();self.assertEqual(len(w.rows),1)
   w.close()

 def test_award_ui_tsv_and_ledger(self):
  with tempfile.TemporaryDirectory() as td:
   repo=Repository(td);p=repo.path_for('JH1HST','','2026-09-12');repo.open(p).append(self.q(remarks='BURO.R'));raw=p.read_bytes()
   w=ActivityDialog(repo,'JH1HST',award=True);w.kind.setCurrentText('JCC');w.extract();self.assertEqual(len(w.selected()),1,w.status.text());data,ext=w.output_data();self.assertTrue(data.decode('utf-8-sig').startswith('1314\tJA1AAA\t'))
   w.ledger().application(w.selected(),'認定済み','42','JCC200');w.extract();self.assertEqual(len(w.selected()),0);self.assertEqual(raw,p.read_bytes());w.close()
 def test_single_band_award_intrinsic_filter_and_tab_transition(self):
  with tempfile.TemporaryDirectory() as td:
   repo=Repository(td);p=repo.path_for('JH1HST','','2026-09-12');sess=repo.open(p)
   sess.append(self.q(call='JA1AAA',remarks='BURO.R',band='18'))
   sess.append(self.q(call='JA1BBB',remarks='BURO.R',band='7'))
   w=ActivityDialog(repo,'JH1HST',award=True);w.kind.setCurrentText('18MHz賞')
   for c in w.filters.bands.values():c.setChecked(True)
   w.extract()
   self.assertEqual(w.tabs.currentIndex(),1,w.status.text())
   self.assertEqual(len(w.rows),1,w.status.text())
   self.assertEqual(w.rows[0]['band'],'18')
   self.assertTrue(w.rows[0]['unit'])
   w.close()

 def test_award_ambiguous_base_call_is_review_row_not_fatal(self):
  with tempfile.TemporaryDirectory() as td:
   repo=Repository(td);p=repo.path_for('JH1HST','','2026-09-12');sess=repo.open(p)
   sess.append(self.q(call='JA1AAA',remarks='BURO.R',band='18'))
   sess.append(self.q(call='JA1BBB/JH1CCC',remarks='BURO.R',band='18'))
   w=ActivityDialog(repo,'JH1HST',award=True);w.kind.setCurrentText('18MHz賞');w.extract()
   self.assertEqual(w.tabs.currentIndex(),1,w.status.text())
   self.assertEqual(len(w.rows),2,w.status.text())
   bad=[r for r in w.rows if r.get('_candidate_error')]
   self.assertEqual(len(bad),1)
   self.assertIn('基本コール',bad[0]['notes'])
   self.assertEqual(len(w.selected()),1)
   w.close()

 def test_hamtte_workbook_has_member_and_summary(self):
  r=dict(date='2025-08-13',time='23:59',band='430',mode='FT8',call='JA1AAA',rst_sent='-10',rst_received='-12',sent='HMT',received='HMT',member=True)
  data=xlsx_bytes(hamtte_sheets([r],dict(title='HAMtte2025夏',own='JH1HST')))
  with zipfile.ZipFile(io.BytesIO(data)) as z:
   self.assertIsNone(z.testzip());self.assertIn('JA1AAA',z.read('xl/worksheets/sheet2.xml').decode());self.assertIn('✓',z.read('xl/worksheets/sheet2.xml').decode())
  from xml.etree import ElementTree as ET
  with zipfile.ZipFile(io.BytesIO(data)) as z:
   tree=ET.fromstring(z.read('xl/worksheets/sheet2.xml'));self.assertIn('JA1AAA',''.join(tree.itertext()))

 def test_jag_category_retained_and_ten_ghz_units(self):
  r=dict(date='2026-07-11',time='06:00',band='10',mode='CW',call='JA1AAA',rst_sent='599',rst_received='599',sent='',received='M',member=False)
  info=dict(own='JH1HST',name='Test',address='Japan',signature='Test',oath=True,categoryname='一般・電信')
  self.assertIn('一般・電信',jarl_text('jag_warc',[r],info))
  for band in ('10.1G','10.4G'):
   self.assertEqual(candidate('10000MHz賞',('JH1HST',self.q(band=band),Path('a'),1))['unit'],'JA1AAA')
 def test_contest_checkbox_reaches_scoring_and_restores_review(self):
  from contest_ui import ContestDialog
  with tempfile.TemporaryDirectory() as td:
   repo=Repository(td);p=repo.path_for('JH1HST','','2026-09-12')
   for call in ('JA1AAA','JA1BBB'):repo.open(p).append(self.q(call))
   raw=p.read_bytes();w=ContestDialog(repo,'JH1HST');w.check_all(True);w.load_target();w.draw();w.stack.setCurrentIndex(2)
   w.table.item(0,11).setCheckState(Qt.Unchecked);w.advance();self.assertEqual(len(w.selection.rows),1);self.assertEqual(w.selection.rows[0][1].call,'JA1BBB')
   w.go_back();self.assertEqual(w.table.rowCount(),2);self.assertEqual(w.table.item(0,11).checkState(),Qt.Unchecked);self.assertEqual(raw,p.read_bytes());w.close()
 def test_stage_only_and_remaining_preview(self):
  with tempfile.TemporaryDirectory() as td:
   w=ActivityDialog(Repository(td),'JH1HST',award=True);w.kind.setCurrentText('JCC');w.level.setText('JCC200');w.app_status.setCurrentText('認定済み');w.record_application()
   self.assertEqual(w.ledger().data['applications'][0]['level'],'JCC200');self.assertIn('照合はできません',w.status.text());w.close()
   l=Ledger(td,'AJD');units,status=l.preview_units('8 9',True,'未申請');self.assertEqual(units,set('01234567'));self.assertEqual(status,'提出済み');self.assertFalse(l.path.exists())
