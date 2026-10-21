import os,unittest,tempfile,copy,json,socket,time,threading
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
from unittest.mock import patch,MagicMock
from dataclasses import replace
from datetime import datetime,timezone,timedelta
from PySide6.QtCore import QObject,Signal,Qt,QCoreApplication,QEvent
from PySide6.QtWidgets import QApplication,QMessageBox
from storage import Repository
from cluster_monitor import Spot
from rbn_settings import RbnSettings,DEFAULT_NODES,validate,get_settings
from rbn_cycle import CycleSchedule,RbnCycleWorker
from spot_feed import SpotFeed,get_feed
from cluster_workers import RbnWorker
from spot_connection_ui import RbnSettingsDialog,SpotConnection,ProbeWorker

class FakeCycle(QObject):
 spots=Signal(object,bool);status=Signal(str);finished=Signal();snapshot=Signal(str,object)
 def __init__(self,data,parent=None,**kwargs):super().__init__(parent);self.data=data;self.started=False;self.stopped=False
 def start(self):self.started=True
 def stop(self):self.stopped=True
 def wait(self,timeout):return True

class Fix1Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.repo=Repository(Path(self.tmp.name));self.widgets=[];self.data=dict(own='JX1XXX',nodes=copy.deepcopy(DEFAULT_NODES))
  for node in self.data['nodes']:node['enabled']=True
  self.spot=Spot('RBN','',datetime.now(timezone.utc).replace(second=0,microsecond=0).isoformat(),'JX2XXX','7010.0','CW',reporter='JX3XXX-#',comment='CW 20 dB 25 WPM CQ')
 def tearDown(self):
  for w in self.widgets:w.close();w.deleteLater()
  self.app.processEvents();QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);self.tmp.cleanup()
 def test_five_nodes_every_sixty_seconds_return_after_three_hundred(self):
  s=CycleSchedule(self.data['nodes']);slots=[]
  for now in range(0,660,60):slots.append(s.next(now)[0]['slot'])
  self.assertEqual(slots,list('ABCDEABCDEA'))
 def test_disabled_and_same_endpoint_retry_guard_persist(self):
  nodes=copy.deepcopy(self.data['nodes']);nodes[2]['enabled']=False;s=CycleSchedule(nodes);self.assertEqual([s.next(t)[0]['slot'] for t in (0,60,120,180)],list('ABDE'));self.assertIsNone(s.next(240)[0]);self.assertEqual(s.next(300)[0]['slot'],'A')
  retries={('arc.jg1vgx.net',7000):500};s=CycleSchedule(nodes,retries);self.assertEqual(s.next(1)[0]['slot'],'B')
 def test_settings_validation_and_external_change_guard(self):
  store=RbnSettings(self.repo);store.save(self.data);self.assertEqual(store.data['own'],'JX1XXX');self.assertEqual(len(json.loads(store.path.read_text(encoding='utf-8'))['nodes']),5)
  bad=copy.deepcopy(self.data);bad['nodes'][2]['port']=70000
  with self.assertRaises(ValueError):store.save(bad)
  bad=copy.deepcopy(self.data);bad['nodes'][1].update(host=bad['nodes'][0]['host'],port=7000)
  with self.assertRaises(ValueError):validate(bad)
  store.path.write_text('{}',encoding='utf-8')
  with self.assertRaises(Exception):store.save(self.data)
  self.assertEqual(store.path.read_text(encoding='utf-8'),'{}')
 def test_legacy_migration_and_shanghai_default(self):
  conf=Path(self.repo.root)/'config';conf.mkdir(exist_ok=True);(conf/'cluster_monitor.json').write_text(json.dumps(dict(own='JX1XXX',host='old.example',port=7373)),encoding='utf-8');store=RbnSettings(self.repo)
  self.assertEqual(store.data['nodes'][0]['host'],'old.example');self.assertEqual(store.data['own'],'JX1XXX');self.assertTrue(store.data['nodes'][2]['enabled']);self.assertEqual(store.data['nodes'][2]['host'],'telnet.reversebeacon.net')
 def test_buttons_open_same_settings_and_update_both_summaries(self):
  a=SpotConnection(self.repo);b=SpotConnection(self.repo);self.widgets.extend((a,b));self.assertIs(a.store,b.store)
  with patch('spot_connection_ui.RbnSettingsDialog') as dialog:a.button.click();b.button.click();self.assertEqual(dialog.call_count,2)
  a.store.save(self.data);self.assertIn('A→B→C→D→E',a.summary.text());self.assertEqual(a.summary.text(),b.summary.text())
 def test_dialog_save_cancel_and_validation(self):
  d=RbnSettingsDialog(self.repo);self.widgets.append(d);d.own.setCurrentText('JX1XXX');d.rows[2][0].setChecked(True);d.save();self.assertTrue(get_settings(self.repo).path.exists());self.assertTrue(get_settings(self.repo).data['nodes'][2]['enabled'])
  e=RbnSettingsDialog(self.repo);self.widgets.append(e);e.rows[0][2].setText('not valid host')
  with patch.object(QMessageBox,'warning') as warn:e.save();warn.assert_called_once()
  e.reject();self.assertEqual(get_settings(self.repo).data['nodes'][0]['host'],'arc.jg1vgx.net')
 def test_one_worker_shared_and_configuration_changes_restart_once(self):
  store=get_settings(self.repo);store.save(self.data);feed=get_feed(self.repo);a,b=object(),object()
  with patch('spot_feed.RbnCycleWorker',FakeCycle):
   feed.subscribe(a,False,True);worker=feed.active['rbn'];feed.subscribe(b,False,True);self.assertIs(feed.active['rbn'],worker);feed.unsubscribe(a);self.assertFalse(worker.stopped)
   changed=copy.deepcopy(self.data);changed['nodes'][0]['host']='new.example';store.save(changed);self.assertTrue(worker.stopped);self.assertIs(feed.active['rbn'],worker);worker.finished.emit();self.assertNotEqual(feed.active['rbn'],worker);self.assertEqual(feed.active['rbn'].data['nodes'][0]['host'],'new.example')
   last=feed.active['rbn'];feed.unsubscribe(b);self.assertTrue(last.stopped);last.finished.emit();self.assertFalse(feed.active)
 def test_cross_source_dedup_normalizes_frequency_and_retains_snapshot(self):
  feed=SpotFeed();feed.clients[object()]=(False,True);seen=[];feed.delivered.connect(lambda rows,notify:seen.extend(rows))
  with patch('spot_feed.time.monotonic',return_value=100):feed._receive([self.spot],True)
  second=replace(self.spot,reporter='JX4XXX-#',freq='7010.00',stamp=(datetime.fromisoformat(self.spot.stamp)+timedelta(minutes=1)).isoformat())
  with patch('spot_feed.time.monotonic',return_value=160):feed._receive([second],True)
  feed._snapshot('A',[self.spot]);feed._snapshot('B',[second]);self.assertEqual(len(seen),1);self.assertIn('A',feed.source_snapshots);self.assertIn('B',feed.source_snapshots)
  with patch('spot_feed.time.monotonic',return_value=410):feed._receive([second],True)
  self.assertEqual(len(seen),1) # previously seen snapshot must never alert later
  third=replace(second,stamp=(datetime.fromisoformat(second.stamp)+timedelta(minutes=5)).isoformat())
  with patch('spot_feed.time.monotonic',return_value=420):feed._receive([third],True)
  self.assertEqual(len(seen),2)
 def test_profile_commands_and_last_partial_batch_flush(self):
  class Sock:
   def __init__(self):self.sent=[];self.parts=[b'login:',b'DX de JX3XXX-#: 7010.0 JX2XXX CW 20 dB 25 WPM CQ 1000Z\r\n'];self.closed=False
   def settimeout(self,n):pass
   def sendall(self,b):self.sent.append(b)
   def recv(self,n):
    if self.parts:return self.parts.pop(0)
    time.sleep(.005);raise socket.timeout()
   def close(self):self.closed=True
   def shutdown(self,n):pass
  sock=Sock();state=MagicMock();state.matching.side_effect=lambda rows:rows;worker=RbnWorker(state,'host',7000,'JX1XXX',connector=lambda *a,**k:sock,commands=['set/skimmer'],duration=.04);out=[];worker.spots.connect(lambda rows,notify:out.extend(rows),Qt.ConnectionType.DirectConnection);worker.run()
  self.assertEqual(sock.sent,[b'JX1XXX\r\n',b'set/skimmer\r\n']);self.assertTrue(sock.closed);self.assertEqual(len(out),1)
 def test_cycle_stop_interrupts_wait_and_only_one_socket_at_a_time(self):
  events=[];outer=None
  class Child(QObject):
   spots=Signal(object,bool);status=Signal(str)
   def __init__(self,state,host,port,call,**kwargs):super().__init__();self.host=host;events.append(('create',host));self.logged_in=True
   def run(self):events.append(('run',self.host));self.spots.emit([self_spot],True);outer.stop()
   def stop(self):events.append(('stop',self.host))
  self_spot=self.spot;outer=RbnCycleWorker(self.data,worker_factory=Child,slot_seconds=.01);out=[];outer.spots.connect(lambda rows,notify:out.extend(rows),Qt.ConnectionType.DirectConnection);outer.run();self.assertEqual(sum(e[0]=='create' for e in events),1);self.assertEqual(len(out),1)
 def test_probe_blocked_while_rbn_is_in_use(self):
  store=get_settings(self.repo);store.save(self.data);feed=get_feed(self.repo);owner=object();feed.clients[owner]=(False,True);d=RbnSettingsDialog(self.repo);self.widgets.append(d)
  with patch.object(QMessageBox,'information') as info:d.test_node(0);info.assert_called_once()
  self.assertIsNone(d.probe);feed.clients.clear()
 def test_connect_deadline_and_late_result_close(self):
  from cluster_workers import bounded_connect
  release=threading.Event();sock=MagicMock()
  def connector(*a,**k):release.wait(1);return sock
  with self.assertRaises(TimeoutError):bounded_connect(('slow.example',7000),threading.Event(),timeout=.02,connector=connector)
  with self.assertRaisesRegex(TimeoutError,'前の名前解決'):bounded_connect(('slow.example',7000),threading.Event(),connector=connector)
  release.set();deadline=time.monotonic()+1
  while not sock.close.called and time.monotonic()<deadline:time.sleep(.005)
  sock.close.assert_called_once()
 def test_connect_stop_is_cooperative(self):
  from cluster_workers import bounded_connect
  stop=threading.Event();release=threading.Event()
  def connector(*a,**k):release.wait(1);return MagicMock()
  threading.Timer(.02,stop.set).start();started=time.monotonic()
  try:
   with self.assertRaises(TimeoutError):bounded_connect(('cancel.example',7000),stop,connector=connector)
   self.assertLess(time.monotonic()-started,.5)
  finally:release.set()
 def test_real_rotation_thread_visits_five_nodes_without_socket_overlap(self):
  seen=[];live={'count':0};outer=None
  class Sock:
   def __init__(self):self.parts=[b'login:',b'DX de JX3XXX-#: 7010.0 JX2XXX CW 20 dB 25 WPM CQ 1000Z\r\n'];self.closed=False
   def settimeout(self,n):pass
   def sendall(self,b):pass
   def recv(self,n):
    if self.parts:return self.parts.pop(0)
    time.sleep(.001);raise socket.timeout()
   def shutdown(self,n):pass
   def close(self):
    if not self.closed:live['count']-=1;self.closed=True
  def connector(address,timeout):
   if live['count']:raise AssertionError('overlapping sockets')
   live['count']+=1;seen.append(address);return Sock()
  def factory(*a,**k):return RbnWorker(*a,connector=connector,**k)
  outer=RbnCycleWorker(self.data,worker_factory=factory,slot_seconds=.025);out=[]
  def receive(rows,notify):
   out.extend(rows)
   if len(out)>=5:outer.stop()
  outer.spots.connect(receive,Qt.ConnectionType.DirectConnection);outer.start()
  if not outer.wait(3000):outer.stop();outer.wait(1000);self.fail('rotation did not stop')
  self.assertEqual(seen,[(n['host'],n['port']) for n in self.data['nodes']]);self.assertEqual(len(out),5);self.assertEqual(live['count'],0)
if __name__=='__main__':unittest.main()
