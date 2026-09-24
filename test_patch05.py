import unittest
from pathlib import Path

from model import QSO
from qsl_marks import change,tokens
from contest import candidates
from remarks_sections import primary,split_for_ui,compose,validate_component,append_primary
from session_state import standard_session,serializable,restore
from storage import VERSION


class Patch05RemarksTests(unittest.TestCase):
    def test_version(self):
        self.assertEqual(VERSION,'1.14')

    def test_legacy_rmks_is_unchanged(self):
        text='BURO OP:"Taro Yamada" ADIF_EXTRA:{"NAME":"Taro"}'
        self.assertEqual(primary(text),text)
        self.assertEqual(split_for_ui(text),(text,'',[]))
        self.assertEqual(compose(text),text)

    def test_rmks2_roundtrip_and_future_section(self):
        text='BURO 310103 <<RMKS2>> OP:Tanaka <<RMKS3>> future'
        self.assertEqual(primary(text),'BURO 310103')
        one,two,extra=split_for_ui(text)
        self.assertEqual(one,'BURO 310103')
        self.assertEqual(two,'OP:Tanaka')
        self.assertEqual(extra,[(3,'future')])
        self.assertEqual(compose(one,two,extra),text)

    def test_reserved_tag_is_rejected_only_as_component(self):
        with self.assertRaises(ValueError):validate_component('memo <<RMKS2>> other')
        self.assertEqual(compose('memo','other'),'memo <<RMKS2>> other')

    def test_qsl_updates_rmks1_and_preserves_rmks2(self):
        old='BURO <<RMKS2>> hQSL.R note'
        self.assertEqual(tokens(old),{'buro'})
        after,first,buro=change(old,'BURO.R')
        self.assertEqual(after,'BURO.R <<RMKS2>> hQSL.R note')
        self.assertTrue(first)
        self.assertFalse(buro)

    def test_append_primary_does_not_move_to_rmks2(self):
        self.assertEqual(append_primary('memo <<RMKS2>> second','ADIF_EXTRA:{}'),
                         'memo ADIF_EXTRA:{} <<RMKS2>> second')

    def test_contest_number_candidates_use_rmks1_only(self):
        self.assertEqual(candidates('001A <<RMKS2>> 999B'),['001A'])

    def test_tab_keeps_rmks2_visibility(self):
        s=standard_session(1,{'own':'JH1HST'})
        s['rmks2_visible']=True
        data=serializable(s)
        self.assertTrue(data['rmks2_visible'])
        sessions,_,_=restore({'workspace_sessions':[data],'own':'JH1HST'})
        self.assertTrue(sessions[0]['rmks2_visible'])

    def test_gui_source_has_requested_patch05_controls(self):
        main=Path('main.py').read_text(encoding='utf-8')
        search=Path('search_ui.py').read_text(encoding='utf-8')
        help_text=Path('help_ui.py').read_text(encoding='utf-8')
        self.assertIn("QCheckBox('RMKS2を表示')",main)
        self.assertIn("button('コンテスト提出へ…'",search)
        self.assertIn("QLabel('チェック済みを →')",search)
        self.assertIn('起動コマンドフラグについて',help_text)
        self.assertIn('--reset-window',help_text)


if __name__=='__main__':unittest.main()
