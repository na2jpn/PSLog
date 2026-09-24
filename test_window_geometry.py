import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import unittest,tempfile
from unittest.mock import patch
from PySide6.QtCore import QRect
from PySide6.QtWidgets import QApplication,QScrollArea
from storage import save_settings,load_settings
from main import Window
from settings_ui import SettingsDialog
from window_geometry import fitted,state
class GeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def test_missing_screen_tiny_and_malformed(self):
        screens=[QRect(0,0,1366,728)]
        for saved in ({'x':9999,'y':-9000,'width':1200,'height':900},{'x':50,'y':50,'width':10,'height':1},{'x':'bad'},None):
            r=fitted(saved,screens);self.assertTrue(screens[0].contains(r));self.assertGreaterEqual(r.width(),640);self.assertGreaterEqual(r.height(),420)
    def test_negative_monitor_and_small_laptop(self):
        screens=[QRect(0,0,1920,1040),QRect(-1280,0,1280,984)]
        r=fitted({'x':-1000,'y':100,'width':900,'height':700},screens);self.assertLess(r.x(),0);self.assertTrue(screens[1].contains(r))
        small=QRect(0,0,480,300);r=fitted({},[small]);self.assertEqual(r,small)
    def test_actual_window_restart_and_small_scroll(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_settings(tmp,{'own':'JH1HST','window_geometry':{'x':9999,'y':9999,'width':10,'height':1}})
            w=Window(tmp)
            with patch('window_geometry.areas',return_value=[QRect(0,0,480,300)]):
                w.show();self.app.processEvents();self.app.processEvents()
                self.assertLessEqual(w.width(),480);self.assertLessEqual(w.height(),300)
                # v14 wraps the main QScrollArea so a fixed 4px accent line can
                # sit below the menu bar.  The safety scroll still exists, but it
                # is no longer the direct centralWidget.
                scroll=w.findChild(QScrollArea);self.assertIsNotNone(scroll)
                self.assertGreater(scroll.verticalScrollBar().maximum(),0)
                w.close()
            saved=load_settings(tmp)['window_geometry'];self.assertEqual(saved['width'],480)
            w=Window(tmp)
            with patch('window_geometry.areas',return_value=[QRect(0,0,1024,700)]):
                w.show();self.app.processEvents();self.assertGreaterEqual(w.width(),640);w.close()
    def test_dialog_controls_reachable_by_scrolling(self):
        d=SettingsDialog({},lambda values:None)
        with patch('window_geometry.areas',return_value=[QRect(0,0,360,240)]):
            d.show();self.app.processEvents();self.app.processEvents()
            self.assertLessEqual(d.width(),360);self.assertLessEqual(d.height(),240)
            scroll=d.findChild(QScrollArea);self.assertIsNotNone(scroll);self.assertGreater(scroll.verticalScrollBar().maximum(),0)
            d.reject()
    def test_maximized_minimized_normal_geometry(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_settings(tmp,{'own':'JH1HST'});w=Window(tmp);w.show();self.app.processEvents()
            w.showMaximized();self.app.processEvents();w.correct_window();self.app.processEvents()
            self.assertTrue(w.isMaximized());w.showMinimized();self.app.processEvents()
            value=state(w);self.assertTrue(value['maximized']);self.assertGreater(value['height'],100)
            w.showNormal();self.app.processEvents();w.close()
