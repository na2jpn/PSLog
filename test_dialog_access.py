"""Small-screen reachability across the principal non-contest dialogs."""
import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from PySide6.QtCore import QRect
from PySide6.QtWidgets import QApplication,QScrollArea,QPushButton,QTabWidget
from storage import Repository
from preferences import DEFAULTS
from window_geometry import SafeDialog
from import_ui import ImportDialog
from export_ui import ExportDialog
from restore_ui import RestoreDialog
from search_ui import SearchDialog
from settings_ui import SettingsDialog
from blacklist_ui import BlacklistDialog
from qsl_ui import QSLDialog
from pota_ui import PotaDialog
from sota_ui import SotaDialog
from help_ui import HelpDialog

class DialogAccessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def test_small_screen_buttons_tabs_and_cancel(self):
        with tempfile.TemporaryDirectory() as folder:
            repo=Repository(folder)
            factories=[lambda:ImportDialog(repo,'JH1HST'),lambda:ExportDialog(repo,'JH1HST'),
                lambda:RestoreDialog(repo),lambda:SearchDialog(repo,'JH1HST'),
                lambda:SettingsDialog(DEFAULTS,lambda _:None),lambda:BlacklistDialog(folder),
                lambda:QSLDialog(repo,'JH1HST'),lambda:PotaDialog(repo,'JH1HST'),
                lambda:SotaDialog(repo,'JH1HST'),lambda:HelpDialog('使い方')]
            with patch('window_geometry.areas',return_value=[QRect(0,0,480,320)]):
                for factory in factories:
                    dialog=factory()
                    with self.subTest(dialog=type(dialog).__name__):
                        self.assertIsInstance(dialog,SafeDialog);dialog.show();self.app.processEvents();self.app.processEvents()
                        self.assertLessEqual(dialog.width(),480);self.assertLessEqual(dialog.height(),320)
                        outer=dialog.layout().itemAt(0).widget();self.assertIsInstance(outer,QScrollArea)
                        for tabs in dialog.findChildren(QTabWidget):
                            for i in range(tabs.count()):tabs.setCurrentIndex(i);self.app.processEvents()
                        buttons=[b for b in dialog.findChildren(QPushButton) if b.isVisible() and b.isEnabled()]
                        self.assertTrue(buttons)
                        for button in buttons:
                            ancestor=button.parentWidget()
                            while ancestor is not None:
                                if isinstance(ancestor,QScrollArea):ancestor.ensureWidgetVisible(button,0,0);self.app.processEvents()
                                ancestor=ancestor.parentWidget()
                            self.assertTrue(outer.viewport().rect().intersects(button.rect().translated(button.mapTo(outer.viewport(),button.rect().topLeft()))))
                        dialog.reject();self.assertFalse(dialog.isVisible());dialog.deleteLater();self.app.processEvents()
            self.assertFalse(list(Path(folder).rglob('*.txt')))
