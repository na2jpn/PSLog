import io,tempfile,unittest,zipfile
from pathlib import Path
from PySide6.QtWidgets import QApplication

from activity_ui import ActivityDialog
from countries import load
from model import QSO
from special_awards import anniversary_candidate,ten_thousand_candidate,selection_indices,metrics,workbook_bytes
from storage import Repository

class SpecialAwardStage1011Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.app=QApplication.instance() or QApplication([]);cls.countries=load(Path(__file__).parent)
 def q(self,call='JA1AAA',band='7',mode='CW',code='JCC 1314',remarks='BURO.R',qth='Kasukabe Saitama Japan',my='Soka Saitama Japan',day='2026-09-15'):
  return QSO(day,'12:34',band,mode,call,'599','599',qth,my,remarks,code)
 def row(self,call,unit,**extra):
  return dict(call=call,unit=unit,date='2026-09-15',time='12:34',band=extra.pop('band','7'),mode='CW',code=extra.pop('code',''),qth='Japan',**extra)
 def test_anniversary_units_and_prefixes(self):
  self.assertEqual(anniversary_candidate('100周年 J賞',self.q('JA1AAA'))['unit'],'JA1')
  self.assertEqual(anniversary_candidate('100周年 J賞',self.q('7K1AAA'))['unit'],'7K1')
  self.assertEqual(anniversary_candidate('100周年 A賞',self.q(code='JCC 131401'))['unit'],'131401')
  self.assertEqual(anniversary_candidate('100周年 R賞',self.q(code='JCG 14001'))['unit'],'14001')
  self.assertEqual(anniversary_candidate('100周年 L賞',self.q(code='JCC 4701'))['unit'],'47')
 def test_anniversary_station_types_are_explicit(self):
  blank=anniversary_candidate('100周年 100 AJD・銀賞',self.q(remarks=''))
  self.assertFalse(blank['unit']);self.assertIn('100TH.PUBLIC',blank['notes'])
  public=anniversary_candidate('100周年 100 AJD・銀賞',self.q('JA1AAA/2',remarks='100TH.PUBLIC'))
  self.assertEqual(public['unit'],'2')
  event=anniversary_candidate('100周年 イベント局賞',self.q('8J1RL',remarks='100TH.EVENT'))
  self.assertEqual(event['unit'],'8J1RL')
 def test_anniversary_same_call_other_band(self):
  rows=[self.row('JA1AAA','JA1AAA@7'),self.row('JA1AAA','JA1AAA@14',band='14'),self.row('JA1AAA/1','JA1AAA@7')]
  self.assertEqual(selection_indices('100周年 100賞',rows),[0,1])
  calls=[self.row('JA1AAA','JA1AAA'),self.row('JA1AAA/1','JA1AAA',band='14')]
  self.assertEqual(selection_indices('100周年 10000賞',calls),[0])
 def test_japan_candidate_and_disallowed_link(self):
  r=ten_thousand_candidate('全日本 2500局賞',self.q('JA1AAA/3',code='JCC 2701'),self.countries)
  self.assertEqual((r['unit'],r['pref'],r['area']),('JA1AAA','27','3'))
  r=ten_thousand_candidate('全日本 2500局賞',self.q(mode='SAT',remarks='BURO.R SAT'),self.countries)
  self.assertFalse(r['unit']);self.assertIn('中継局',r['notes'])
 def test_japan_builds_three_disjoint_prefecture_sets(self):
  rows=[]
  for setno in range(3):
   for pref in range(1,48):
    code=str(pref).zfill(2);rows.append(self.row(f'J{chr(65+setno)}1{pref:03d}' if pref<100 else f'J{chr(65+setno)}1AAA',f'S{setno}-{code}',pref=code,area='1',band='7',station_key=f'S{setno}-{code}'))
  # Synthetic calls need only be distinct for the selection helper.
  for i,r in enumerate(rows):r['call']=f'JA{(i%9)+1}{chr(65+i//676)}{chr(65+(i//26)%26)}{chr(65+i%26)}';r['unit']=r['call']
  m=metrics('全日本 2500局賞',rows)
  self.assertEqual(m['pref_sets'],3);self.assertEqual(m['required_sets'],3);self.assertFalse(m['complete'])
 def test_world_metadata_and_japan_group_limit(self):
  r=ten_thousand_candidate('全世界 2500局賞',self.q('HL4ZHE',code='',qth='Jeju Korea'),self.countries)
  self.assertEqual((r['entity'],r['itu'],r['continent']),('HL','44','AS'))
  rows=[self.row('JA1AAA','JA1AAA',japan_group='日本本土'),self.row('JA2BBB','JA2BBB',japan_group='日本本土'),self.row('JD1CCC','JD1CCC',japan_group='小笠原'),self.row('K1AAA','K1AAA',japan_group='')]
  self.assertEqual(selection_indices('全世界 2500局賞',rows),[0,2,3])
 def test_same_call_different_licensees_can_be_selected(self):
  rows=[self.row('JA1AAA','JA1AAA',licensee='日本太郎'),self.row('JA1AAA','JA1AAA',licensee='東京花子')]
  self.assertEqual(selection_indices('全日本 2500局賞',rows),[0,1])
 def test_world_metrics(self):
  rows=[]
  for i in range(100):
   call=f'K{(i%9)+1}{chr(65+i//26)}{chr(65+i%26)}A';rows.append(self.row(call,call,entity=f'E{i}',itu=str(i%40+1),continent=('AF','AN','AS','EU','NA','OC','SA')[i%7],japan_group=''))
  m=metrics('全世界 2500局賞',rows);self.assertEqual((m['entities'],m['itus'],m['continents']),(100,40,7));self.assertFalse(m['complete'])
 def test_workbooks_have_required_sheets(self):
  cases=[('100周年 J賞',[self.row('JA1AAA','JA1')],{'申請書','交信局リスト'}),('全日本 2500局賞',[self.row('JA1AAA','JA1AAA',pref='13',area='1')],{'申請概要','47都道府県','交信局リスト','エリア別累計'}),('全世界 2500局賞',[self.row('HL4ZHE','HL4ZHE',entity='HL',itu='44',continent='AS',country='Korea',japan_group='')],{'申請概要','交信局リスト','ARRLエンティティ','ITUゾーン','六大州・南極'})]
  for award,rows,names in cases:
   data=workbook_bytes(award,rows,dict(own='JH1HST',name='Test',signature='Test',reviewer1='JA1AAA A',reviewer2='JA1BBB B'))
   with zipfile.ZipFile(io.BytesIO(data)) as z:
    self.assertIsNone(z.testzip());book=z.read('xl/workbook.xml').decode()
    for name in names:self.assertIn(name,book)
 def test_ui_defaults_and_non_destructive_output(self):
  with tempfile.TemporaryDirectory() as td:
   repo=Repository(td);p=repo.path_for('JH1HST','','2026-09-15');repo.open(p).append(self.q(remarks='NO QSL'));raw=p.read_bytes()
   w=ActivityDialog(repo,'JH1HST',award=True);w.kind.setCurrentText('100周年 J賞');self.assertFalse(w.qsl.isChecked());self.assertFalse(w.qsl.isEnabled());w.extract();self.assertEqual(len(w.selected()),1);data,ext=w.output_data();self.assertEqual(ext,'.xlsx');self.assertTrue(zipfile.is_zipfile(io.BytesIO(data)));self.assertEqual(raw,p.read_bytes());w.close()
 def test_ui_ten_thousand_requires_received_qsl(self):
  with tempfile.TemporaryDirectory() as td:
   repo=Repository(td);p=repo.path_for('JH1HST','','2026-09-15');repo.open(p).append(self.q(remarks='BURO'))
   w=ActivityDialog(repo,'JH1HST',award=True);w.kind.setCurrentText('全日本 2500局賞');self.assertTrue(w.qsl.isChecked());self.assertFalse(w.rows);w.extract();self.assertEqual(w.rows,[]);w.close()

if __name__=='__main__':unittest.main()
