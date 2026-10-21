import os,unittest,tempfile,copy,json
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
from dataclasses import replace
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
from PySide6.QtCore import QObject,Signal,QCoreApplication,QEvent
from PySide6.QtWidgets import QApplication,QMessageBox
from PySide6.QtGui import QTextCursor
from storage import Repository
from cluster_monitor import Spot
from band_site import BandSpots
from band_site_ui import BandSiteDialog,BandPanel,FtPanel
from cluster_monitor_ui import ClusterMonitorDialog
from spot_display import ft_groups,station_region,ft_mode
from rbn_settings import RbnSettings,DEFAULT_NODES
from spot_feed import SpotFeed
from spot_connection_ui import RbnSettingsDialog,ProbeWorker
class Fix2Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.repo=Repository(Path(self.tmp.name));self.widgets=[];self.now=datetime.now(timezone.utc);self.spot=Spot('国内','one',self.now.isoformat(),'JA1ZZZ','7074.5','FT8','13001A',reporter='W1ZZZ',comment='FT8 20 dB')
 def tearDown(self):
  for d in self.widgets:d.close();d.deleteLater()
  self.app.processEvents();QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);self.tmp.cleanup()
 def band(self):
  d=BandSiteDialog(self.repo);self.widgets.append(d);return d
 def test_ft_and_normal_are_separate_and_mix_in_eight_slots(self):
  d=self.band();d.toggle_band('7-FT',True);d.running=True;d.receive([self.spot,replace(self.spot,ident='cw',freq='7010',mode='CW')],False)
  self.assertIsInstance(d.panels['7'],BandPanel);self.assertIsInstance(d.panels['7-FT'],FtPanel);self.assertEqual([s.mode for s in d.panels['7'].spots],['CW']);self.assertEqual([s.mode for s in d.panels['7-FT'].spots],['FT8'])
  for name in ['10','10-FT','14','14-FT','18','18-FT']:d.toggle_band(name,True)
  self.assertEqual(len(d.panels),8)
  with patch.object(QMessageBox,'information'):d.toggle_band('21-FT',True)
  self.assertNotIn('21-FT',d.panels);d.show();self.app.processEvents();rects=[panel.geometry() for panel in d.panels.values()]
  for i,rect in enumerate(rects):
   for other in rects[i+1:]:self.assertFalse(rect.intersects(other))
 def test_group_by_khz_and_mode_latest_call_once(self):
  newer=replace(self.spot,ident='new',freq='7074.9',stamp=(self.now+timedelta(seconds=10)).isoformat());other=replace(self.spot,ident='other',call='W2ZZZ');ft4=replace(self.spot,ident='four',mode='FT4');nextfreq=replace(self.spot,ident='freq',freq='7075.1')
  groups=ft_groups([self.spot,newer,other,ft4,nextfreq]);self.assertEqual(len(groups[(7070,'FT8')]),2);self.assertEqual(next(s for s in groups[(7070,'FT8')] if s.call=='JA1ZZZ'),newer);self.assertIn((7070,'FT4'),groups);self.assertIn((7080,'FT8'),groups)
 def test_card_lists_every_station_scrolls_and_keeps_scroll(self):
  d=self.band();d.toggle_band('7-FT',True);d.running=True;rows=[replace(self.spot,ident=str(i),call=f'JA1Z{i}') for i in range(90)];d.receive(rows,False);d.show();self.app.processEvents();panel=d.panels['7-FT'];table=panel.cards[(7070,'FT8')][1];self.assertEqual(table.rowCount(),90);self.assertGreater(table.verticalScrollBar().maximum(),0);table.verticalScrollBar().setValue(10);d.refresh();self.assertEqual(table.verticalScrollBar().value(),10);self.assertIn('MHz',table.item(0,0).toolTip())
 def test_region_operating_calls_and_portable_locations(self):
  for call in ['JA1ZZZ','7K1ZZZ','8J1ZZZ','JD1ZZZ','JA1ZZZ/7','JA1ZZZ/P','JA/W1ZZZ']:self.assertEqual(station_region(call),'ja',call)
  for call in ['W1ZZZ','HL1ZZZ','BV1ZZZ','W6/JA1ZZZ','JA1ZZZ/KH0']:self.assertEqual(station_region(call),'dx',call)
  self.assertIsNone(station_region('JA1ZZZ/MM'));self.assertIsNone(station_region('???'))
 def test_scope_filters_both_panels_by_operating_call_and_persists(self):
  d=self.band();d.toggle_band('7-FT',True);d.running=True;rows=[self.spot,replace(self.spot,ident='dxft',call='W1ZZZ',reporter='JA1ZZZ'),replace(self.spot,ident='jacw',mode='CW',freq='7010'),replace(self.spot,ident='dxcw',call='HL1ZZZ',mode='CW',freq='7011')];d.receive(rows,False)
  d.scope.setCurrentIndex(d.scope.findData('ja'));self.assertTrue(all(s.call=='JA1ZZZ' for p in d.panels.values() for s in p.spots))
  d.scope.setCurrentIndex(d.scope.findData('dx'));self.assertEqual(d.panels['7'].spots[0].call,'HL1ZZZ');self.assertEqual(d.panels['7-FT'].spots[0].call,'W1ZZZ');d.reject();loaded=self.band();self.assertEqual(loaded.scope.currentData(),'dx');self.assertIn('7-FT',loaded.selected)
 def test_unknown_region_only_in_all(self):
  store=BandSpots();store.add([replace(self.spot,call='JA1ZZZ/MM')]);self.assertEqual(len(store.for_band('7',region='all')),1);self.assertFalse(store.for_band('7',region='ja'));self.assertFalse(store.for_band('7',region='dx'))
 def test_ft_flood_does_not_evict_normal_modes(self):
  store=BandSpots();cw=replace(self.spot,ident='cw',mode='CW');store.add([cw]);store.add([replace(self.spot,ident=str(i)) for i in range(4100)]);self.assertEqual(len(store.for_band('7',ft=False)),1);self.assertEqual(sum(bool(ft_mode(s.mode)) for s in store.items.values()),4000)
 def test_target_ft_off_by_default_and_no_replay_sound_on_enable(self):
  d=ClusterMonitorDialog(self.repo);self.widgets.append(d);d.calls.set_values(['JA1ZZZ']);d.update_filters();d.running=True;self.assertFalse(d.include_ft.isChecked())
  with patch.object(d,'play_alert') as sound:
   d.receive([self.spot],True);self.assertEqual(d.table.rowCount(),0);sound.assert_not_called()
   with patch.object(d.feed,'snapshot',return_value=[self.spot]):d.include_ft.setChecked(True)
   self.assertEqual(d.table.rowCount(),1);sound.assert_not_called();d.include_ft.setChecked(False);self.assertEqual(d.table.rowCount(),0)
  d.reject();e=ClusterMonitorDialog(self.repo);self.widgets.append(e);self.assertFalse(e.include_ft.isChecked())
 def test_silent_duplicate_update_refreshes_ft_card_without_alert(self):
  d=self.band();d.rbn.setChecked(True);d.toggle_band('7-FT',True);d.running=True;d.feed.clients[d]=(False,True);first=replace(self.spot,source='RBN',ident='');later=replace(first,stamp=(self.now+timedelta(minutes=1)).isoformat());delivered=[];d.feed.delivered.connect(lambda rows,notify:delivered.extend(rows))
  with patch('spot_feed.time.monotonic',return_value=10):d.feed._receive([first],True)
  with patch('spot_feed.time.monotonic',return_value=70):d.feed._receive([later],True)
  self.assertEqual(len(delivered),1);self.assertEqual(d.panels['7-FT'].cards[(7070,'FT8')][1].rowCount(),1);self.assertEqual(d.panels['7-FT'].spots[0].stamp,later.stamp);self.assertEqual(len(d.feed.snapshot(False,True)),1)
 def test_old_c_preset_migrates_but_custom_c_is_preserved(self):
  path=Path(self.repo.root)/'config/rbn.json';path.parent.mkdir(exist_ok=True);data=dict(own='JX1XXX',nodes=copy.deepcopy(DEFAULT_NODES));data['nodes'][2].update(host='dxc.dx.or.kr',port=23,profile='設定なし',enabled=False);path.write_text(json.dumps(data),encoding='utf-8');store=RbnSettings(self.repo);self.assertEqual(store.data['nodes'][2]['host'],'telnet.reversebeacon.net');self.assertFalse(store.data['nodes'][2]['enabled']);self.assertEqual(json.loads(path.read_text(encoding='utf-8'))['nodes'][2]['host'],'dxc.dx.or.kr')
  data['nodes'][2]['host']='custom.example';path.write_text(json.dumps(data),encoding='utf-8');self.assertEqual(RbnSettings(self.repo).data['nodes'][2]['host'],'custom.example')
 def test_success_and_error_appear_in_details_with_colors_and_literal_text(self):
  d=RbnSettingsDialog(self.repo);self.widgets.append(d);d.append_detail('<script>literal</script>');d.show_result('接続成功／RBN受信は未確認');self.assertIn('【結果】接続成功',d.details.toPlainText());self.assertIn('<script>',d.details.toPlainText());cursor=d.details.textCursor();cursor.movePosition(QTextCursor.MoveOperation.End);cursor.movePosition(QTextCursor.MoveOperation.PreviousCharacter,QTextCursor.MoveMode.KeepAnchor);self.assertEqual(cursor.charFormat().foreground().color().name(),'#18733b');d.show_result('接続失敗：TimeoutError');cursor=d.details.textCursor();cursor.movePosition(QTextCursor.MoveOperation.PreviousCharacter,QTextCursor.MoveMode.KeepAnchor);self.assertEqual(cursor.charFormat().foreground().color().name(),'#b3261e')
 def test_probe_separates_connected_empty_failed_and_rbn(self):
  spot=self.spot
  class Child(QObject):
   spots=Signal(object,bool);status=Signal(str)
   connected=True;failure='';rows=[]
   def __init__(self,*a,**k):super().__init__()
   def run(self):
    if self.rows:self.spots.emit(self.rows,True)
   def stop(self):pass
  for connected,rows,expected in [(True,[],'接続成功／RBN受信は未確認'),(False,[],'接続失敗'),(True,[spot],'RBN受信確認：1件')]:
   Child.connected=connected;Child.rows=rows;out=[]
   with patch('spot_connection_ui.RbnWorker',Child):worker=ProbeWorker(DEFAULT_NODES[0],'JX1XXX');worker.result.connect(out.append);worker.run()
   self.assertIn(expected,out[0])
 def test_cw_duplicates_do_not_consume_silent_ft_refresh_channel(self):
  feed=SpotFeed();feed.clients[object()]=(False,True);updates=[];feed.updated.connect(updates.extend);first=replace(self.spot,source='RBN',mode='CW');later=replace(first,stamp=(self.now+timedelta(minutes=1)).isoformat())
  with patch('spot_feed.time.monotonic',return_value=10):feed._receive([first],True)
  with patch('spot_feed.time.monotonic',return_value=70):feed._receive([later],True)
  self.assertFalse(updates);self.assertEqual(feed.snapshot(False,True)[0].stamp,later.stamp)
if __name__=='__main__':unittest.main()
