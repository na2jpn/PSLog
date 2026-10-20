import tempfile,unittest
from pathlib import Path
from dataclasses import replace
from model import QSO
from storage import Repository
from countries import load
from country_history import load_history
from dxcc_check import resolve,aggregate
from award_applications import Applications

class Fix2Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.db=load(self.root);self.history=load_history(self.root)
  self.q=QSO('2024-09-15','10:00','21','FT8','JA1AAA','-01','-01','','Soka Saitama Japan','','')
 def test_exact_only_entities_qth_and_calls(self):
  cases=[('3D2CCC','Conway Reef','3D2/c'),('3D2CCC','RG78 Conway Reef','3D2/c'),('3D2V','RH87 Rotuma Island','3D2/r'),('TX7W','Austral Islands','FO/a'),('JG8NQJ/JD1','QL64 Minamitorishima','JD/m'),('E51WL','North Cook Islands','E5/n')]
  for call,qth,ident in cases:
   with self.subTest(call=call,qth=qth):
    row,why=resolve(self.db,self.history,replace(self.q,call=call,his_qth=qth));self.assertIsNotNone(row,why);self.assertEqual(row['id'],ident)
  row,why=resolve(self.db,self.history,replace(self.q,call='3D2CCC'));self.assertEqual(row['id'],'3D2/c')
 def test_every_exact_entity_is_in_index(self):
  resolve(self.db,self.history,self.q)
  self.assertTrue({r['entity_prefix'] for r in self.db.exact.values()}<=set(self.db._dxcc_rows))
 def test_lotw_names_and_aliases(self):
  for qth,ident in [('South Africa','ZS'),('Republic of South Africa','ZS'),('St. Helena','ZD7'),('Saint Helena','ZD7'),('St. Lucia','J6'),('Saint Lucia','J6'),('Turkey','TA'),('Asiatic Türkiye','TA')]:
   with self.subTest(qth=qth):
    row,why=resolve(self.db,self.history,replace(self.q,his_qth=qth));self.assertIsNotNone(row,why);self.assertEqual(row['id'],ident)
 def test_uncertain_c7a_never_merged_even_with_country(self):
  for call in ['C7A','C7A/P']:
   for qth in ['Austria United Nations','Austria','United Nations HQ','']:
    row,why=resolve(self.db,self.history,replace(self.q,call=call,his_qth=qth));self.assertIsNone(row);self.assertIn('未確定',why)
 def test_ambiguous_jd1_and_cook_are_not_guessed(self):
  row,why=resolve(self.db,self.history,replace(self.q,call='JD1ABC'));self.assertIsNone(row)
  row,why=resolve(self.db,self.history,replace(self.q,call='E51WL',his_qth='Cook Islands'));self.assertIsNone(row)
  row,why=resolve(self.db,self.history,replace(self.q,call='ZZ1AAA',his_qth='Unknown Island'));self.assertIsNone(row)
 def test_aggregation_labels_history_checks_and_log_unchanged(self):
  repo=Repository(self.root);path=repo.path_for('JH1HST','',self.q.date)
  for n,(call,qth) in enumerate([('C21TS','Nauru'),('C21MM','Naoero'),('ZS6EB','South Africa'),('J69DS','Saint Lucia'),('E51WL','North Cook Islands'),('C7A','Austria United Nations')]):
   repo.open(path).append(replace(self.q,call=call,his_qth=qth,time=f'10:{n:02}',remarks='LoTW.R'))
  before=path.read_bytes();a=Applications(self.root);a.set('JH1HST','DXCC','ZS','*',True);a.set('JH1HST','DXCC','C2','*',True)
  result=aggregate(repo,'JH1HST');self.assertEqual(result.worked,4);self.assertEqual(len(result.unresolved),1)
  rows={e.ident:e for e in result.entities};self.assertEqual(rows['ZS'].name,'Republic of South Africa');self.assertEqual(rows['J6'].name,'Saint Lucia');self.assertEqual(len(rows['C2'].hits),2);self.assertEqual(rows['C2'].names,{'Nauru'})
  self.assertTrue(a.checked('JH1HST','DXCC',rows['ZS'].ident));self.assertTrue(a.checked('JH1HST','DXCC',rows['C2'].ident));self.assertEqual(before,path.read_bytes())
if __name__=='__main__':unittest.main()
