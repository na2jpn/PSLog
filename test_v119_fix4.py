import os,unittest,tempfile,wave
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
from unittest.mock import MagicMock,patch
from PySide6.QtWidgets import QApplication,QWidget
from preferences import validate
from alert_audio import AlertPlayer
from settings_ui import SettingsDialog
from storage import Repository,save_settings,load_settings
class Fix4Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
 def test_settings_validation(self):
  self.assertEqual(validate({})['alert_volume'],50)
  for value in (-1,101,True,'50'):
   with self.assertRaises(ValueError):validate({'alert_volume':value})
  with self.assertRaises(ValueError):validate({'alert_sound':'missing'})
 def test_audio_volume_queue_and_stop(self):
  p=AlertPlayer();p.effect=MagicMock();p.play(0);p.effect.play.assert_not_called()
  p.play(25,'terere');p.effect.setVolume.assert_called_with(.25);self.assertTrue(p.effect.setSource.call_args.args[0].toLocalFile().endswith('terere.wav'))
  p.play(70);self.assertEqual(len(p.pending),1);self.assertEqual(p.effect.play.call_count,1)
  p.effect.isPlaying.return_value=True;p._changed();p.effect.isPlaying.return_value=False;p._changed();p._next();self.assertEqual(p.effect.play.call_count,2)
  p.stop();self.assertFalse(p.pending);self.assertFalse(p.active);p.effect.stop.assert_called_once()
 def test_settings_preview_save_reload(self):
  with tempfile.TemporaryDirectory() as tmp:
   repo=Repository(Path(tmp));d=SettingsDialog({},lambda values:save_settings(repo.root,values),repo=repo)
   d.alert_volume.setValue(32);d.alert_sound.setCurrentIndex(1)
   with patch.object(d.alert_player,'play') as play:
    d._preview_alert();play.assert_called_once_with(32,'terere');self.assertFalse(load_settings(repo.root))
   d.save();self.assertEqual(load_settings(repo.root)['alert_volume'],32);self.assertEqual(load_settings(repo.root)['alert_sound'],'terere');d.deleteLater();self.app.processEvents()
 def test_monitor_uses_saved_preferences_and_mute(self):
  from cluster_monitor_ui import ClusterMonitorDialog
  with tempfile.TemporaryDirectory() as tmp:
   repo=Repository(Path(tmp));save_settings(repo.root,{'alert_volume':19,'alert_sound':'terere'});d=ClusterMonitorDialog(repo)
   with patch.object(d.alert,'play') as play,patch.object(d.alert,'stop') as stop:
    d.play_alert();play.assert_called_once_with(19,'terere');d.sound.setChecked(False);stop.assert_called_once();d.play_alert();self.assertEqual(play.call_count,1)
   d.reject();d.deleteLater();self.app.processEvents()
 def test_gui_cleanup_preserves_previous_widgets(self):
  from test_v119_fix3_gui import Fix3GuiTests
  sentinel=QWidget();sentinel.show();case=Fix3GuiTests();case.setUpClass();case.setUp()
  with patch.object(sentinel,'close') as close:case.tearDown();close.assert_not_called()
  case.doCleanups();sentinel.close();sentinel.deleteLater();self.app.processEvents()
 def test_bundled_waves(self):
  for name in ('standard','terere'):
   with wave.open(str(Path(__file__).parent/'assets/sounds'/(name+'.wav'))) as w:self.assertEqual(w.getsampwidth(),2);self.assertGreater(w.getnframes(),0)
if __name__=='__main__':unittest.main()
