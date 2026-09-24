import io,tempfile,unittest,zipfile
from pathlib import Path
from PySide6.QtWidgets import QApplication

from aja import canonical_band,region_kind,candidate,distinct,stats,xlsx_bytes,import_workbook,load_master
from activity_ui import ActivityDialog
from award_registry import Ledger
from model import QSO
from storage import Repository

class AjaStage9Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
 def q(self,call='JA1AAA',band='7',date='2026-09-15',code='JCC 1314',remarks='BURO.R',mode='CW'):
  return QSO(date,'12:34',band,mode,call,'599','599','Japan','Soka Saitama Japan',remarks,code)
 def test_band_normalization_and_satellite(self):
  self.assertEqual(canonical_band('135kHz'),'0.135');self.assertEqual(canonical_band('475kHz'),'0.475')
  self.assertEqual(canonical_band('3.8'),'3.5');self.assertEqual(canonical_band('10.4G'),'10000')
  self.assertEqual(canonical_band('144','FO-29','CW'),'SAT')
 def test_designated_city_and_tokyo_dates(self):
  self.assertEqual(region_kind('1344','2003-03-31')[0],'city');self.assertFalse(region_kind('1344','2003-04-01')[0])
  self.assertFalse(region_kind('134401','2003-03-31')[0]);self.assertEqual(region_kind('134401','2003-04-01')[0],'ward')
  self.assertEqual(region_kind('100101','2010-03-31')[0],'ward');self.assertEqual(region_kind('100101','2010-04-01')[0],'city')
 def test_candidate_units_and_station_keys(self):
  r=candidate(self.q('JA1AAA/1','7',code='JCC 1314'));self.assertEqual(r['unit'],'1314@7');self.assertEqual(r['station_key'],'JA1AAA@7');self.assertEqual(r['region_type'],'city')
  r=candidate(self.q(code='JCG 14001'));self.assertEqual(r['unit'],'14001@7');self.assertEqual(r['region_type'],'gun')
  self.assertFalse(candidate(self.q(date='2026-01-01',code='JCC 1344'))['unit'])
 def test_two_independent_duplicate_rules(self):
  rows=[dict(unit='1314@7',call='JA1AAA',aja_band='7',station_key='JA1AAA@7',region_type='city'),dict(unit='1312@7',call='JA1AAA',aja_band='7',station_key='JA1AAA@7',region_type='city'),dict(unit='1314@7',call='JA1BBB',aja_band='7',station_key='JA1BBB@7',region_type='city'),dict(unit='1314@14',call='JA1AAA',aja_band='14',station_key='JA1AAA@14',region_type='city')]
  selected,warnings=distinct(rows);self.assertEqual(len(selected),2);self.assertEqual(stats(rows)['bands'],2);self.assertEqual(len(warnings),2)
 def test_corrected_workbook_and_roundtrip(self):
  rows=[dict(unit='1314@7',region='1314',region_type='city',aja_band='7',band='7',mode='CW',call='JA1AAA',date='2026-09-15',station_key='JA1AAA@7',qth='Kasukabe'),dict(unit='14001@14',region='14001',region_type='gun',aja_band='14',band='14',mode='SSB',call='JA1BBB',date='2026-09-14',station_key='JA1BBB@14',qth='Japan')]
  data=xlsx_bytes(Path(__file__).parent,rows,dict(own='JH1HST',name='Test',signature='Test'))
  with zipfile.ZipFile(io.BytesIO(data)) as z:
   self.assertIsNone(z.testzip());sheet=z.read('xl/worksheets/sheet1.xml').decode();totals=z.read('xl/worksheets/sheet2.xml').decode()
   for value in ('135kHz','475kHz','10GHz','135GHz','248GHz','Satellite','JA1AAA','JA1BBB'):self.assertIn(value,sheet)
   self.assertIn('JH1HST',totals);self.assertIn('<v>2</v>',totals)
  with tempfile.TemporaryDirectory() as td:
   path=Path(td)/'aja.xlsx';path.write_bytes(data);result=import_workbook(path);self.assertEqual(result['selected'],2);self.assertEqual({r['unit'] for r in result['records']},{'1314@7','14001@14'})
 def test_supplied_blank_legacy_xls_is_readable(self):
  path=Path(__file__).parent/'docs/activity-research/sources/AJA-list_202401.xls';self.assertEqual(import_workbook(path)['records'],[])
 def test_master_retains_historical_rows(self):
  data=load_master(Path(__file__).parent);self.assertEqual(len(data['rows']),1713);self.assertIn('1344',{r['code'] for r in data['rows']});self.assertIn('134401',{r['code'] for r in data['rows']})
 def test_ui_selects_unit_and_station_once_and_exports(self):
  with tempfile.TemporaryDirectory() as td:
   repo=Repository(td);p=repo.path_for('JH1HST','','2026-09-15');session=repo.open(p)
   for q in [self.q('JA1AAA','7',code='JCC 1314'),self.q('JA1AAA/1','7',code='JCC 1312'),self.q('JA1BBB','7',code='JCC 1314'),self.q('JA1AAA','14',code='JCC 1314')]:session.append(q)
   raw=p.read_bytes();w=ActivityDialog(repo,'JH1HST',award=True);w.kind.setCurrentText('AJA');self.assertFalse(w.endorse_band.isEnabled());w.extract();self.assertEqual(len(w.selected()),2);self.assertIn('2バンド',w.summary_label.text());data,ext=w.output_data();self.assertEqual(ext,'.xlsx');self.assertTrue(zipfile.is_zipfile(io.BytesIO(data)));self.assertEqual(raw,p.read_bytes());w.close()
 def test_prior_station_same_band_is_excluded(self):
  with tempfile.TemporaryDirectory() as td:
   repo=Repository(td);p=repo.path_for('JH1HST','','2026-09-15');repo.open(p).append(self.q('JA1AAA/1','7',code='JCC 1312'))
   ledger=Ledger(td,'AJA','特記なし / ','JH1HST');ledger.import_records([dict(unit='1314@7',call='JA1AAA',date='2025-01-01',band='7',aja_band='7',station_key='JA1AAA@7',region_type='city')],'認定済み')
   w=ActivityDialog(repo,'JH1HST',award=True);w.kind.setCurrentText('AJA');w.extract();self.assertEqual(w.rows,[]);w.close()

if __name__=='__main__':unittest.main()
