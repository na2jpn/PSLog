import tempfile,unittest
from pathlib import Path
from model import QSO
from storage import VERSION,Repository
from session_state import standard_session,contest_session
from contest_rules import RuleStore
from rule_view_data import contest_sections,party_sections,award_sections
from party import PARTIES
from award_registry import AWARDS
from exporting import prepare_rows

class Patch06Tests(unittest.TestCase):
    def test_version(self):
        self.assertEqual(VERSION,'1.14')

    def test_new_workspace_defaults(self):
        self.assertEqual((standard_session(1,{})['band'],standard_session(1,{})['mode']),('430','FM'))
        self.assertEqual((contest_session('TEST','202609')['band'],contest_session('TEST','202609')['mode']),('7','SSB'))

    def test_rule_view_data_builds_for_registered_data(self):
        store=RuleStore('.')
        found_okayama=False
        for path in store.files():
            try:rule,_=store.read(path)
            except Exception:continue
            sections=contest_sections(rule)
            self.assertTrue(sections)
            if rule.get('id')=='all_okayama':
                found_okayama=True
                text='\n'.join(str(value) for _,_,rows in sections for _,value,_ in rows)
                rows={label:value for _,_,items in sections for label,value,_ in items}
                self.assertEqual(rows['交信対象'],
                    '県内局：国内で運用するすべてのアマチュア局。県外局：岡山県内で運用するアマチュア局。')
                self.assertIn('同一相手局・同一バンド',text)
        self.assertTrue(found_okayama)
        for key in PARTIES:self.assertTrue(party_sections(key))
        with tempfile.TemporaryDirectory() as tmp:
            for name in AWARDS:self.assertTrue(award_sections(tmp,name))

    def test_rmks_mapping_adif_and_hamlog(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=Repository(tmp);path=repo.path_for('JH1HST','','2026-09-21');s=repo.open(path)
            q=QSO('2026-09-21','12:00','7','CW','JA1AAA','599','599','Tokyo','Soka','BURO <<RMKS2>> OP:Tanaka','1301')
            s.append(q);row=('JH1HST',q,path,1)
            plan=prepare_rows([s],[row],'adx',remark_mapping={'rmks1':'COMMENT','rmks2':'QSLMSG'})
            text=plan.data.decode('utf-8')
            self.assertIn('<COMMENT>BURO</COMMENT>',text);self.assertIn('<QSLMSG>OP:Tanaka</QSLMSG>',text)
            plan=prepare_rows([s],[row],'csv',remark_mapping={'rmks1':'Remarks1','rmks2':'Remarks2'})
            text=plan.data.decode('cp932')
            self.assertIn('"BURO"',text);self.assertIn('MYCALL:JH1HST MYQTH:Soka OP:Tanaka',text)

    def test_source_contains_patch06_ui_contract(self):
        main=Path('main.py').read_text(encoding='utf-8')
        search=Path('search_ui.py').read_text(encoding='utf-8')
        contest=Path('contest_ui.py').read_text(encoding='utf-8')
        export=Path('export_ui.py').read_text(encoding='utf-8')
        helptext=Path('help_ui.py').read_text(encoding='utf-8')
        for needle in ('PathLabel','全件表示','コンテストルール表示…','QSOパーティルール表示…','アワード条件表示…'):
            self.assertIn(needle,main)
        self.assertIn("filename='',autorun=False",search)
        self.assertIn('件の候補があります。コンテストを選択してください。',contest)
        self.assertIn('1 / 3　出力対象・基本条件',export)
        self.assertIn('2 / 3　出力項目の対応',export)
        self.assertIn('3 / 3　確認・出力',export)
        self.assertNotIn('法令上免責できない責任まで免除する趣旨ではありません。',helptext)

if __name__=='__main__':unittest.main()
