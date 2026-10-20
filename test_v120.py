import os,unittest,tempfile,threading,time
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
from datetime import datetime,timezone,timedelta
from dataclasses import replace
from unittest.mock import patch
from PySide6.QtWidgets import QApplication,QMessageBox
from PySide6.QtCore import QCoreApplication,QEvent
from storage import Repository
from cluster_monitor import Spot,PollGate
from cluster_monitor_ui import ClusterMonitorDialog
from band_site import BandSpots,abbreviation
from band_site_ui import BandSiteDialog
class V120Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.repo=Repository(Path(self.tmp.name));self.dialogs=[];self.now=datetime.now(timezone.utc);self.spot=Spot('国内','one',self.now.isoformat(),'JX1XXX','7010.0','CW','13001A')
 def tearDown(self):
  for d in self.dialogs:d.reject();d.deleteLater()
  self.app.processEvents();QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);self.tmp.cleanup()
 def target(self):
  d=ClusterMonitorDialog(self.repo);self.dialogs.append(d);return d
 def band(self):
  d=BandSiteDialog(self.repo);self.dialogs.append(d);return d
 def test_set_only_applies_own_field_and_ignores_empty_whitespace(self):
  d=self.target();d.calls.edit.setText(' , jx1xxx, , J X 2 X X X,,');d.codes.edit.setText('13001A');d.set_condition(d.calls)
  self.assertEqual(d.calls.values,['JX1XXX','JX2XXX']);self.assertEqual(d.state.codes,());self.assertEqual(d.codes.values,[]);self.assertEqual(d.calls.edit.text(),' , jx1xxx, , J X 2 X X X,,')
  d.set_condition(d.codes);self.assertEqual(d.state.codes,('13001A',));d.calls.edit.setText('JX3XXX');d.reject();loaded=self.target();self.assertEqual(loaded.calls.values,['JX1XXX','JX2XXX']);self.assertEqual(loaded.calls.edit.text(),' , jx1xxx, , J X 2 X X X,,')
 def test_bad_set_keeps_applied_and_saved_values(self):
  d=self.target();d.calls.edit.setText('JX1XXX');d.set_condition(d.calls);before=d.path.read_bytes();d.calls.edit.setText('JX2XXX;JX3XXX')
  with patch.object(QMessageBox,'warning') as warning:d.set_condition(d.calls);warning.assert_called_once()
  self.assertEqual(d.calls.values,['JX1XXX']);self.assertEqual(d.path.read_bytes(),before)
 def test_save_failure_does_not_apply(self):
  d=self.target();d.calls.edit.setText('JX1XXX')
  with patch('cluster_monitor_ui.replace_bytes',side_effect=OSError('locked')),patch.object(QMessageBox,'warning'):d.set_condition(d.calls)
  self.assertEqual(d.calls.values,[]);self.assertEqual(d.state.calls,())
 def test_frequency_filter_expiration_and_duplicate_stations(self):
  store=BandSpots();store.add([self.spot,replace(self.spot,ident='second',source='RBN'),replace(self.spot,ident='old',call='JX2XXX',stamp=(self.now-timedelta(minutes=31)).isoformat()),replace(self.spot,ident='bad',freq='nan')],self.now)
  self.assertEqual(len(store.items),2);self.assertEqual(len(store.for_band('7')),1);self.assertEqual(len(store.for_band('14')),0);self.assertEqual(abbreviation(self.spot,'7'),'.010');store.expire(self.now+timedelta(minutes=31));self.assertFalse(store.items)
 def test_bands_limit_layout_persistence_and_no_network_on_open(self):
  with patch('cluster_workers.fetch_local',side_effect=AssertionError('network')):
   d=self.band();self.assertFalse(d.running);self.assertEqual(list(d.panels),['7'])
   for name in ['14','18','21','24','28','50','144']:d.toggle_band(name,True)
   self.assertEqual(len(d.panels),8)
   with patch.object(QMessageBox,'information'):d.toggle_band('430',True)
   self.assertNotIn('430',d.selected);d.show();self.app.processEvents();rects=[w.geometry() for w in d.panels.values()]
   for i,r in enumerate(rects):
    for other in rects[i+1:]:self.assertFalse(r.intersects(other))
   d.reject();loaded=self.band();self.assertEqual(loaded.selected,d.selected);self.assertFalse(loaded.running)
 def test_shared_feed_single_fetch_and_last_subscriber_stop(self):
  entered=threading.Event();release=threading.Event();calls=[]
  def fetch():calls.append(1);entered.set();release.wait(3);return [self.spot]
  with patch('cluster_workers.fetch_local',fetch),patch('cluster_workers.POLL_GATE',PollGate()):
   target=self.target();band=self.band();target.calls.edit.setText('JX1XXX');target.set_condition(target.calls);target.start();self.assertTrue(entered.wait(1));band.start();self.assertEqual(len(target.feed.active),1);self.assertEqual(len(target.feed.clients),2)
   target.reject();self.assertEqual(len(band.feed.clients),1);release.set();deadline=time.monotonic()+2
   while not band.store.items and time.monotonic()<deadline:self.app.processEvents();time.sleep(.01)
   self.assertEqual(len(calls),1);self.assertTrue(band.store.items);self.assertEqual(target.table.rowCount(),0);band.reject();deadline=time.monotonic()+3
   while band.feed.active and time.monotonic()<deadline:self.app.processEvents();time.sleep(.01)
   self.assertFalse(band.feed.active)
 def test_missing_common_login_does_not_start_rbn(self):
  d=self.band();d.connection.store.data['own']=''
  with self.assertRaises(ValueError):d.feed.subscribe(d,False,True)
  self.assertNotIn(d,d.feed.clients)
 def test_figure_clipping_and_tooltip_has_full_frequency(self):
  d=self.band();d.running=True;d.receive([replace(self.spot,ident=str(i),freq=str(7010+i*.01),call=f'JX{i}XXX') for i in range(80)],False);d.show();self.app.processEvents();panel=d.panels['7'];pix=panel.grab();self.assertFalse(pix.isNull());self.assertTrue(panel.hits);self.assertIn('MHz',panel.description(self.spot));self.assertEqual(len(panel.spots),80)
 def test_main_launches_modeless_windows_and_closes_them(self):
  from main import Window
  from storage import save_settings
  save_settings(self.repo.root,{'own':'JX1XXX'});w=Window(self.repo.root)
  try:
   w.open_cluster_monitor();target=w._target_alert_dialog;w.open_band_site();band=w._band_site_dialog;self.app.processEvents()
   self.assertFalse(target.isModal());self.assertFalse(band.isModal());self.assertTrue(target.isVisible());self.assertTrue(band.isVisible());w.open_cluster_monitor();self.assertIs(w._target_alert_dialog,target)
   w.close();self.assertTrue(target.closing);self.assertTrue(band.closing);self.assertIsNone(w._target_alert_dialog);self.assertIsNone(w._band_site_dialog)
  finally:
   w.close();w.deleteLater();self.app.processEvents()
if __name__=='__main__':unittest.main()
