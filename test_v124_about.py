from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PySide6.QtWidgets import QApplication,QPushButton
import help_ui
from product_info import COPYRIGHT,ORGANIZATION
from storage import VERSION

ROOT=Path(__file__).resolve().parent
APP=QApplication.instance() or QApplication([])


class AboutTests(unittest.TestCase):
    def test_license_screen_displays_all_canonical_documents_offline(self):
        dialog=help_ui.LicenseDialog(name='AUTHOR_NOTICE.txt')
        self.addCleanup(dialog.close)
        self.assertEqual(dialog.tabs.count(),3)
        self.assertEqual(dialog.tabs.currentIndex(),2)
        for index,(filename,_) in enumerate(help_ui.LICENSE_TABS):
            view=dialog.tabs.widget(index)
            self.assertTrue(view.isReadOnly())
            self.assertEqual(view.toPlainText(),(ROOT/filename).read_text(encoding='utf-8-sig'))
        self.assertIn(VERSION,dialog.windowTitle())
        self.assertIn(COPYRIGHT,dialog.tabs.widget(2).toPlainText())

    def test_about_has_always_visible_license_button_and_current_author(self):
        about=help_ui.HelpDialog('PSLogについて');self.addCleanup(about.close)
        about.resize(640,480);about.show();APP.processEvents()
        buttons=[b for b in about.findChildren(QPushButton) if b.text()=='ライセンスを表示']
        self.assertEqual(len(buttons),1);self.assertTrue(buttons[0].isVisible())
        with patch.object(help_ui.LicenseDialog,'exec',return_value=0) as run:
            buttons[0].click();self.assertEqual(run.call_count,1)
        self.assertIn(COPYRIGHT,help_ui.TEXTS['PSLogについて'])
        self.assertIn(ORGANIZATION,help_ui.TEXTS['PSLogについて'])

    def test_packaged_docs_and_internal_fallback(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);docs=root/'docs';docs.mkdir();bundle=root/'bundle';(bundle/'licenses').mkdir(parents=True)
            (docs/'LICENSE.md').write_text('current packaged license',encoding='utf-8')
            (bundle/'licenses/LICENSING.md').write_text('bundled policy',encoding='utf-8')
            with patch.object(help_ui,'data_directory',return_value=root), patch.object(help_ui.sys,'_MEIPASS',str(bundle),create=True):
                self.assertEqual(help_ui._license_text('LICENSE.md'),'current packaged license')
                self.assertEqual(help_ui._license_text('LICENSING.md'),'bundled policy')
        with self.assertRaises(ValueError):help_ui._license_text('../conf.cfg')

    def test_release_history_contains_only_requested_signature_entry(self):
        history=(ROOT/'meta/UPDATE_HISTORY.txt').read_text(encoding='utf-8-sig')
        top=history.split('Ver1.24',1)[1].split('Ver1.23',1)[0]
        lines=[line for line in top.splitlines() if line.startswith('・')]
        self.assertEqual(lines,['・Windows版の実行ファイルに、コードサイニング証明書によるデジタル署名を追加しました。'])


if __name__=='__main__':unittest.main()
