import unittest,json,threading,time,tempfile,os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
from unittest.mock import patch
import his_qth_batch as b
class Fix5Tests(unittest.TestCase):
 def test_php_request_conditions(self):
  from urllib.parse import urlparse,parse_qs
  class Response:
   def __enter__(self):return self
   def __exit__(self,*a):pass
   def read(self,n):return b'{"musen":[]}'
  def opener(req,timeout):
   params=parse_qs(urlparse(req.full_url).query)
   self.assertEqual(params['SK'],['2']);self.assertEqual(params['DA'],['0']);self.assertEqual(params['MA'],['JH1HST'])
   self.assertEqual(req.get_header('Referer'),'https://2jp.org');self.assertIn('Chrome/155.',req.get_header('User-agent'));self.assertEqual(timeout,15)
   return Response()
  self.assertEqual(b.request_location('JH1HST',opener),{'musen':[]})
 def test_list_locality_to_roman_and_jcc(self):
  from locations import qth_for_row
  with tempfile.TemporaryDirectory() as tmp:
   data={'musenInformation':{'totalCount':'1'},'musen':[{'listInfo':{'name':'JG1CFO','tdfkCd':'千葉県鴨川市'}}]}
   row=b.location_from_response(data,'JG1CFO',b.load_locations(Path(tmp)))
   self.assertEqual(row['source_code'],'1223');self.assertEqual(qth_for_row(row),'Kamogawa Chiba Japan')
   data['musen'][0]['listInfo']['name']='JG1CFOX'
   with self.assertRaises(b.StorageError):b.location_from_response(data,'JG1CFO',b.load_locations(Path(tmp)))
 def test_county_suffix_and_numeric_prefecture_rejected(self):
  with tempfile.TemporaryDirectory() as tmp:
   loc=b.load_locations(Path(tmp));data={'musen':[{'listInfo':{'name':'JH1HST','tdfkCd':'北海道阿寒郡鶴居村'}}]}
   self.assertEqual(b.location_from_response(data,'JH1HST',loc)['source_code'],'01001B')
   data['musen'][0]['listInfo']['tdfkCd']='01'
   with self.assertRaises(b.StorageError):b.location_from_response(data,'JH1HST',loc)
 def test_total_timeout_late_result_and_no_parallel_retry(self):
  release=threading.Event();ended=threading.Event();slot=threading.BoundedSemaphore(1)
  def blocked(*a,**k):
   try:release.wait(2);return b'{"musen":[]}'
   finally:ended.set()
  with patch.object(b,'LOOKUP_DEADLINE',.05),patch.object(b,'_LOOKUP_SLOT',slot),patch.object(b,'request_bytes',blocked):
   try:
    start=time.monotonic()
    with self.assertRaisesRegex(b.StopLookup,'制限時間超過') as cm:b.request_location('JH1HST')
    self.assertLess(time.monotonic()-start,.5);self.assertIn('URL:',str(cm.exception));self.assertIn('経過:',str(cm.exception))
    with self.assertRaisesRegex(b.StopLookup,'前の'):b.request_location('JH1HST')
   finally:release.set();self.assertTrue(ended.wait(1))
 def test_request_error_has_url_elapsed_type(self):
  def fail(*a,**k):raise OSError('DNS failure')
  with patch.object(b,'request_bytes',fail):
   with self.assertRaises(b.StopLookup) as cm:b.request_location('JH1HST')
  for text in ('URL:','経過:','OSError','DNS failure'):self.assertIn(text,str(cm.exception))
class Fix5GuiTests(unittest.TestCase):
 def test_real_worker_timeout_is_displayed_and_controls_return(self):
  from PySide6.QtWidgets import QApplication
  from PySide6.QtCore import QCoreApplication,QEvent
  from internet_tools_ui import MicLookupDialog
  from storage import Repository
  app=QApplication.instance() or QApplication([])
  release=threading.Event();ended=threading.Event()
  def blocked(*a,**k):
   try:release.wait(2);return b'{"musen":[]}'
   finally:ended.set()
  with tempfile.TemporaryDirectory() as tmp,patch.object(b,'LOOKUP_DEADLINE',.05),patch.object(b,'_LOOKUP_SLOT',threading.BoundedSemaphore(1)),patch.object(b,'request_bytes',blocked):
   d=MicLookupDialog(Repository(Path(tmp)))
   try:
    self.assertIn('JX1XXX',d.call.placeholderText());d.call.setText('JH1HST');d.run();deadline=time.monotonic()+2
    while d.worker is not None and time.monotonic()<deadline:app.processEvents();time.sleep(.005)
    self.assertIsNone(d.worker);self.assertTrue(d.lookup.isEnabled());self.assertIn('取得失敗',d.status.text());self.assertIn('制限時間超過',d.detail.toPlainText())
   finally:
    release.set();ended.wait(1);d.reject();d.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
if __name__=='__main__':unittest.main()

