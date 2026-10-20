import io,json,socket,tempfile,threading,time,unittest
from pathlib import Path
from datetime import datetime,timezone
from urllib.error import HTTPError,URLError
from PySide6.QtCore import Qt
from cluster_monitor import Spot,MonitorState,PollGate,parse_local,parse_rbn,tokens,valid_token,region_matches,matches
from internet_common import request_bytes,InternetError
from his_qth_batch import request_location,StopLookup

XML='''<?xml version="1.0" encoding="Shift_JIS"?><List><Spot ID="x1"><Date>2026/10/20</Date><Time>09:18</Time><TimeZone>+9:00</TimeZone><Freq>7,010.0</Freq><Mode>CW</Mode><Message>移動運用</Message><SpotStation><CallSign>JA1AAA/1</CallSign><QthID>13001A</QthID><QthName1>埼玉県</QthName1></SpotStation><ReportStation><CallSign>JA2BBB</CallSign><QthID>1401</QthID></ReportStation></Spot></List>'''
class Fix3Tests(unittest.TestCase):
 def test_shift_jis_spot_uses_operating_station_not_reporter(self):
  row=parse_local(XML.encode('cp932'))[0];self.assertEqual(row.call,'JA1AAA/1');self.assertEqual(row.code,'13001A');self.assertEqual(row.freq,'7010.0');self.assertEqual(row.comment,'移動運用');self.assertEqual(row.stamp,'2026-10-20T00:18:00+00:00')
 def test_xml_invalid_or_oversize_stops(self):
  for raw in [b'<html/>',b'bad',b'x'*2_000_001,b'<!DOCTYPE List [<!ENTITY x "bad">]><List/>']:
   with self.assertRaises(Exception):parse_local(raw)
 def test_exact_code_and_county_suffix(self):
  for a,b in [('13001','13001'),('13001','13001A'),('13001A','13001A'),('1318','1318')]:self.assertTrue(region_matches(a,b))
  for a,b in [('13001A','13001B'),('13001A','13001'),('1318','131801'),('13001','130011'),('1318','1319')]:self.assertFalse(region_matches(a,b))
 def test_tokens_and_validation(self):
  self.assertEqual(tokens('ja1aaa，ＪＡ２ＢＢＢ, 13001a'),['JA1AAA','JA2BBB','13001A'])
  for text in ['1318','13001','13001A','100121']:self.assertTrue(valid_token(text,'code'))
  for text in ['130','13001AB','13001;bad']:self.assertFalse(valid_token(text,'code'))
 def test_filter_or_portable_and_rbn_not_region(self):
  s=parse_local(XML.encode('cp932'))[0];self.assertTrue(matches(s,['JA1AAA'],[]));self.assertTrue(matches(s,[],['13001']));self.assertFalse(matches(s,['JA1AAA/2'],[]))
  r=Spot('RBN','','2026-10-20T00:00:00+00:00','JA1AAA','7010','CW','13001A');self.assertFalse(matches(r,[],['13001']));self.assertTrue(matches(r,['JA1AAA'],[]))
 def test_dedup_keys_and_bounded_memory(self):
  st=MonitorState();s=parse_local(XML.encode('cp932'))[0];self.assertEqual(st.fresh([s,s]),[s]);self.assertFalse(st.fresh([s]))
  for n in range(20005):st.fresh([Spot('国内',str(n),'','JA1AAA','7','CW')])
  self.assertEqual(len(st.seen),20000)
 def test_rbn_midnight_parse_and_receiver_duplicates(self):
  now=datetime(2026,10,20,0,1,tzinfo=timezone.utc)
  a=parse_rbn('DX de JA2BBB-#: 7010.0 JA1AAA CW 20 dB 22 WPM CQ 2359Z',now);self.assertEqual(a.stamp,'2026-10-19T23:59:00+00:00');self.assertEqual(a.code,'')
  b=parse_rbn('DX de JA3CCC-#: 7010.0 JA1AAA CW 21 dB 22 WPM CQ 2359Z',now);self.assertEqual(a.key,b.key);self.assertIsNone(parse_rbn('login:'));self.assertIsNone(parse_rbn('DX de JA2BBB-#: 7010 JA1AAA CW 2960Z'))
 def test_gate_minimum_and_backoff(self):
  g=PollGate();self.assertTrue(g.claim(100));self.assertFalse(g.claim(101));self.assertFalse(g.claim(399));self.assertTrue(g.claim(400));g.failed(900);self.assertGreater(g.remaining(),899);g.succeeded();self.assertEqual(g.failures,0)
 def test_http_diagnostics_and_ua(self):
  class Response:
   def __enter__(self):return self
   def __exit__(self,*a):pass
   def read(self,n):return b'{}'
  def opener(req,timeout):self.assertIn('Chrome/',req.get_header('User-agent'));self.assertEqual(timeout,15);return Response()
  self.assertEqual(request_bytes('https://example.invalid/',opener=opener),b'{}')
  def blocked(*a,**k):raise HTTPError('https://example.invalid/',429,'Too Many Requests',{'Retry-After':'900'},io.BytesIO(b'quota'))
  with self.assertRaises(InternetError) as raised:request_bytes('https://example.invalid/',opener=blocked)
  self.assertEqual(raised.exception.retry_after,900);self.assertIn('quota',str(raised.exception));self.assertIn('HTTP 429',str(raised.exception))
  with self.assertRaises(StopLookup) as raised:request_location('JA1AAA',blocked)
  self.assertIn('URL:',str(raised.exception))
 def test_mic_nonjson_includes_response_diagnostic(self):
  class Response:
   def __enter__(self):return self
   def __exit__(self,*a):pass
   def read(self,n):return b'<html>maintenance</html>'
  with self.assertRaises(StopLookup) as raised:request_location('JA1AAA',lambda *a,**k:Response())
  self.assertIn('maintenance',str(raised.exception));self.assertIn('解析',str(raised.exception))
 def test_local_worker_stop_without_second_fetch(self):
  from cluster_workers import LocalWorker
  state=MonitorState();state.set_filters(['JA1AAA'],[]);calls=[];gate=PollGate()
  def fetch():calls.append(1);return parse_local(XML.encode('cp932'))
  worker=LocalWorker(state,gate=gate,fetch=fetch);out=[]
  def receive(rows,notify):out.append((rows,notify));worker.stop()
  worker.spots.connect(receive,Qt.ConnectionType.DirectConnection);worker.run();self.assertEqual(len(calls),1);self.assertFalse(out[0][1])
 def test_rbn_login_and_cooperative_close(self):
  from cluster_workers import RbnWorker
  class FakeSocket:
   def __init__(self):self.chunks=[b'login:',b'DX de JA2BBB-#: 7010.0 JA1AAA CW 20 dB 22 WPM CQ 1000Z\r\n'];self.sent=[];self.closed=False
   def settimeout(self,x):pass
   def sendall(self,b):self.sent.append(b)
   def recv(self,n):
    if self.chunks:return self.chunks.pop(0)
    time.sleep(.01);raise socket.timeout()
   def shutdown(self,x):pass
   def close(self):self.closed=True
  sock=FakeSocket();st=MonitorState();st.set_filters(['JA1AAA'],[]);w=RbnWorker(st,'relay.invalid',7000,'JH1HST',connector=lambda *a,**k:sock);out=[]
  def receive(rows,notify):out.extend(rows);w.stop()
  w.spots.connect(receive,Qt.ConnectionType.DirectConnection);t=threading.Thread(target=w.run);t.start();t.join(3)
  if t.is_alive():w.stop();t.join(1)
  self.assertFalse(t.is_alive());self.assertEqual(sock.sent,[b'JH1HST\r\n']);self.assertTrue(sock.closed);self.assertEqual(len(out),1)
if __name__=='__main__':unittest.main()
