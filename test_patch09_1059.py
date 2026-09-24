import json
import unittest
from pathlib import Path

from storage import VERSION
from category_filters import classify_categories,category_facets


class Patch09Tests(unittest.TestCase):
    def test_version(self):
        self.assertEqual(VERSION,'1.14')

    def test_category_classifier_never_drops_registered_categories(self):
        checked=0
        for path in Path('config/rules').glob('*.txt'):
            try:
                rule=json.loads(path.read_text(encoding='utf-8'))
            except Exception:
                continue
            categories=rule.get('event',{}).get('categories',[])
            if not categories:
                continue
            classified=classify_categories(categories)
            self.assertEqual(len(classified),len(categories),path.name)
            self.assertEqual([e['id'] for e in classified],[c.get('id','') for c in categories],path.name)
            self.assertEqual([e['name'] for e in classified],[c.get('name','') for c in categories],path.name)
            checked+=1
        self.assertGreater(checked,10)

    def test_category_classifier_has_safe_fallbacks(self):
        odd={'id':'WEIRD-X','name':'特殊記念種目','bands':[],'modes':[],'max_power':None}
        f=category_facets(odd)
        self.assertEqual(f['region'],'その他／未分類')
        self.assertEqual(f['operation'],'その他／未分類')
        self.assertEqual(f['mode'],'その他／未分類')
        self.assertEqual(f['band'],'その他／未分類')
        self.assertEqual(f['power'],'通常／その他')

    def test_main_embedded_history_has_callsign_first_and_scope_status(self):
        source=Path('main.py').read_text(encoding='utf-8')
        self.assertIn("['相手コール','日時 JST','Band','Mode','送 / 受','QTH','JCC/JCG','QSL']",source)
        self.assertIn("['相手コール','日時 JST','Band','Mode','送 / 受','コンテストナンバー']",source)
        self.assertIn("選択中のコンテストログ：{count}交信 ／ 要確認行{issues}件。",source)
        self.assertIn("{self.station[0]} 全ログ：{len(self.rows)}交信 ／ 要確認行{issues}件。",source)

    def test_selected_tab_bottom_edge_is_not_drawn(self):
        source=Path('main.py').read_text(encoding='utf-8')
        tab=source[source.index('class SessionTabBar'):source.index('class Window')]
        self.assertIn('if selected:',tab)
        self.assertIn('painter.drawLine(rect.topLeft(),rect.topRight())',tab)
        self.assertIn('painter.drawLine(rect.topLeft(),rect.bottomLeft())',tab)
        self.assertIn('painter.drawLine(rect.topRight(),rect.bottomRight())',tab)

    def test_rule_view_uses_variable_height_left_aligned_rows(self):
        source=Path('rule_view_ui.py').read_text(encoding='utf-8')
        self.assertIn("key.setFixedWidth(175)",source)
        self.assertIn('text.setWordWrap(True)',source)
        self.assertIn('QSizePolicy.Policy.Expanding',source)
        self.assertIn('Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignTop',source)

    def test_submission_candidate_guidance_is_emphasized(self):
        source=Path('contest_ui.py').read_text(encoding='utf-8')
        self.assertIn("font-size:13pt; font-weight:700",source)
        self.assertIn('件の候補があります。コンテストを選択してください。',source)

    def test_category_selection_dialog_is_generic_and_preserves_original_choice(self):
        source=Path('contest_event_ui.py').read_text(encoding='utf-8')
        self.assertIn('class CategorySelectDialog',source)
        self.assertIn('その他／未分類',source)
        self.assertIn("候補 {len(visible)}件 ／ 登録部門 {len(self.entries)}件",source)
        self.assertIn("item.setData(256,entry['id'])",source)
        self.assertIn('self.category.findData(dialog.selected_id)',source)


if __name__=='__main__':
    unittest.main()
