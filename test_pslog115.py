from pathlib import Path
import unittest

from storage import VERSION

ROOT=Path(__file__).resolve().parent

class PSLog115CoreTests(unittest.TestCase):
    def test_version_and_history_file(self):
        self.assertEqual(VERSION,'1.15')
        history=(ROOT/'meta/UPDATE_HISTORY.txt').read_text(encoding='utf-8-sig')
        self.assertIn('2026-09-29\u3000Ver1.15',history)
        self.assertIn('2026-09-25\u3000Ver1.14',history)
        self.assertIn('2026-09-15\u3000Ver1.01',history)
        self.assertNotIn('Ver1.00',history)

    def test_help_menu_and_about_use_shared_version(self):
        main=(ROOT/'main.py').read_text(encoding='utf-8')
        help_ui=(ROOT/'help_ui.py').read_text(encoding='utf-8')
        guide=(ROOT/'user_guide.py').read_text(encoding='utf-8')
        self.assertIn("'PSLogの更新履歴','PSLogについて'",main)
        self.assertIn("TEXTS['PSLogの更新履歴']=_history_text()",help_ui)
        self.assertIn("title=QLabel(f'PSLog {VERSION}')",help_ui)
        self.assertIn("GUIDE = f'''PSLog {VERSION} 操作案内",guide)
        self.assertNotIn('PSLog 1.14 操作案内',guide)

    def test_qsl_quick_is_draft_until_save(self):
        text=(ROOT/'search_ui.py').read_text(encoding='utf-8')
        start=text.index('class QSLQuickDialog')
        end=text.index('class DetailDialog',start)
        block=text[start:end]
        self.assertIn("self.code=QLineEdit(hit.qso.code)",block)
        self.assertIn("button('HIS QTHへ反映',self.apply_qth_from_code)",block)
        self.assertIn("self.close_button=button('閉じる',self.reject)",block)
        self.assertIn("self.save_button=button('保存',self.save)",block)
        add=block[block.index('def add_qsl_receipt'):block.index('def apply_qth_from_code')]
        self.assertNotIn('.apply(',add)
        save=block[block.index('def save'):]
        self.assertIn('self.hit.apply(q)',save)
        self.assertIn('self.saved=True;self.accept()',save)
        self.assertIn('変更内容を保存せず閉じますか？',block)
        self.assertIn('def has_changes(self):',block)

if __name__=='__main__':unittest.main()
