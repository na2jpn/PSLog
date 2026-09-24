import unittest
from input_normalization import jccjcg_code,jccjcg_parts
from model import QSO
from session_state import contest_session,contest_colors,serializable

class Patch09Tests(unittest.TestCase):
    def test_code_only_normalization_and_jcg_supplement(self):
        self.assertEqual(jccjcg_code('JCC 100101'),'100101')
        self.assertEqual(jccjcg_code('ＪＣＧ １２３４５ａ'),'12345A')
        self.assertEqual(jccjcg_code('12345'),'12345')
        self.assertEqual(jccjcg_parts('100101'),('JCC','100101'))
        self.assertEqual(jccjcg_parts('12345A'),('JCG','12345A'))
        self.assertEqual(jccjcg_parts('12345'),('JCG','12345'))

    def test_qso_save_normalizes_old_prefix(self):
        q=QSO('2026-09-19','12:00','430','FM','JJ1HHJ','59','59','Chiyoda Tokyo Japan','Soka Saitama Japan','','ＪＣＣ １００１０１')
        q.validate();self.assertEqual(q.code,'100101')

    def test_award_sources_accept_shared_code_parser(self):
        award=open('award_registry.py',encoding='utf-8').read()
        aja=open('aja.py',encoding='utf-8').read()
        special=open('special_awards.py',encoding='utf-8').read()
        self.assertIn('jccjcg_parts(code)',award)
        self.assertIn('jccjcg_parts(q.code)',aja)
        self.assertIn('jccjcg_parts(q.code)',special)

    def test_contest_color_stays_with_session_when_order_changes(self):
        a=contest_session('A','202609','JH1HST','7','CW','')
        b=contest_session('B','202609','JH1HST','7','CW','')
        sessions=[a,b]
        first=contest_colors(sessions)
        aid,bid=a['id'],b['id']
        sessions[:]=[b,a]
        second=contest_colors(sessions)
        self.assertEqual(first[aid],second[aid])
        self.assertEqual(first[bid],second[bid])
        self.assertNotIn('_tab_color_index',serializable(a))

    def test_main_source_enables_and_connects_tab_drag(self):
        text=open('main.py',encoding='utf-8').read()
        self.assertIn('self.setMovable(True)',text)
        self.assertIn('self.session_tabs.tabMoved.connect(self._workspace_moved)',text)

if __name__=='__main__':unittest.main()
