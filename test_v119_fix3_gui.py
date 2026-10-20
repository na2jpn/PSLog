import os,tempfile,unittest,json,time,threading
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
from dataclasses import replace
from unittest.mock import patch
from PySide6.QtWidgets import QApplication,QPushButton
from storage import Repository,save_settings
from cluster_monitor_ui import ClusterMonitorDialog,ConditionInput
from internet_tools_ui import MicLookupDialog
from cluster_monitor import Spot
from model import QSO
class Fix3GuiTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
 def setUp(self):
  self.previous_widgets=set(self.app.topLevelWidgets())
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.repo=Repository(Path(self.tmp.name));self.spot=Spot('国内','id1','2026-10-20T00:00:00+00:00','JA1AAA/1','7010.0','CW','13001A','埼玉県','JA2BBB','test')
 def tearDown(self):
  from PySide6.QtCore import QCoreApplication,QEvent
  for widget in self.app.topLevelWidgets():
   if widget not in self.previous_widgets:widget.close();widget.deleteLater()
  QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);self.app.processEvents()
 def test_comma_input_validation(self):
  w=ConditionInput('call');w.edit.setText(', jx1xxx,, jx2xxx,');self.assertEqual(w.parsed(),['JX1XXX','JX2XXX']);self.assertEqual(w.values,[])
  w.edit.setText('bad:')
  with self.assertRaises(ValueError):w.parsed()
  w.close()
 def test_initial_no_network_and_invalid_start(self):
  with patch('internet_common.urlopen',side_effect=AssertionError('initial network')):
   d=ClusterMonitorDialog(self.repo);self.assertFalse(d.running);self.assertFalse(d.workers);d.start();self.assertIn('入力',d.status.text());d.reject()
   m=MicLookupDialog(self.repo);m.call.setText('JA1AAA/1');m.run();self.assertIsNone(m.worker);m.reject()
 def test_notification_once_mute_initial_and_closed(self):
  d=ClusterMonitorDialog(self.repo);d.calls.set_values(['JA1AAA']);d.update_filters();d.running=True
  with patch('alert_audio.AlertPlayer.play') as beep:
   d.receive([self.spot],False);self.assertEqual(d.table.rowCount(),1);beep.assert_not_called()
   d.receive([self.spot],True);beep.assert_not_called()
   d.receive([replace(self.spot,ident='id2')],True);self.assertEqual(beep.call_count,1)
   d.sound.setChecked(False);d.receive([replace(self.spot,ident='id3')],True);self.assertEqual(beep.call_count,1)
   d.stop();d.receive([replace(self.spot,ident='id4')],True);self.assertEqual(d.table.rowCount(),3)
  d.reject()
 def test_conditions_persist_no_automatic_monitor(self):
  d=ClusterMonitorDialog(self.repo);d.calls.set_values(['JA1AAA']);d.codes.set_values(['13001']);d.sound.setChecked(False);d.reject()
  d=ClusterMonitorDialog(self.repo);self.assertEqual(d.calls.values,['JA1AAA']);self.assertEqual(d.codes.values,['13001']);self.assertFalse(d.sound.isChecked());self.assertFalse(d.running);self.assertFalse(d.workers);d.reject()
 def test_mic_result_raw_and_determined_location(self):
  from test_v118 import response
  m=MicLookupDialog(self.repo);m.call.setText('JJ1JPE');m.render(response('JJ1JPE','埼玉県草加市'));self.assertIn('判定成功',m.status.text());self.assertIn('Soka',m.detail.toPlainText());self.assertIn('1321',m.detail.toPlainText());m.render({'musen':[]});self.assertIn('該当局なし',m.status.text());m.failed('HTTP 403\nreason');self.assertIn('HTTP 403',m.detail.toPlainText());m.reject()
 def test_stop_close_drops_late_results(self):
  from cluster_monitor import PollGate
  entered=threading.Event();release=threading.Event()
  def fetch():entered.set();release.wait(2);return [self.spot]
  with patch('cluster_workers.fetch_local',fetch),patch('cluster_workers.POLL_GATE',PollGate()),patch('alert_audio.AlertPlayer.play') as beep:
   d=ClusterMonitorDialog(self.repo);d.calls.set_values(['JA1AAA']);d.update_filters();d.start()
   self.assertTrue(entered.wait(1));d.reject();release.set();deadline=time.monotonic()+3
   while d.workers and time.monotonic()<deadline:self.app.processEvents();time.sleep(.01)
   self.assertFalse(d.workers);d.receive([self.spot],True);self.assertEqual(d.table.rowCount(),0);self.assertTrue(d.closing);beep.assert_not_called()
 def test_tools_menu_order_and_actions(self):
  from main import Window
  save_settings(self.repo.root,{'own':'JH1HST'});w=Window(self.repo.root)
  titles=[a.text() for a in w.menuBar().actions()];self.assertIn('ログ',titles);self.assertNotIn('編集',titles);self.assertEqual(titles.index('ツール')+1,titles.index('バックアップ'))
  tools=next(m for m in w.menu_refs if m.title()=='ツール');self.assertEqual([a.text() for a in tools.actions()],['QSL受領一括処理','総務省DB参照','ターゲットアラート','バンドサイト'])
  log=next(m for m in w.menu_refs if m.title()=='ログ');self.assertNotIn('QSL受領一括処理',[a.text() for a in log.actions()]);self.assertTrue(any(a.menu() and a.text()=='ログ一括処理' for a in log.actions()))
  with patch('internet_tools_ui.MicLookupDialog') as dialog:tools.actions()[1].trigger();dialog.return_value.exec.assert_called_once()
  with patch('cluster_monitor_ui.ClusterMonitorDialog') as dialog:tools.actions()[2].trigger();dialog.return_value.show.assert_called_once()
  with patch('band_site_ui.BandSiteDialog') as dialog:tools.actions()[3].trigger();dialog.return_value.show.assert_called_once()
  w._target_alert_dialog=None;w._band_site_dialog=None
  w.close()
if __name__=='__main__':unittest.main()
