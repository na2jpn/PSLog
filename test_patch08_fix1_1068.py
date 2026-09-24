import tempfile,unittest
from dataclasses import replace
from pathlib import Path
from model import QSO
from storage import Repository,VERSION
from qsl_batch import prepare,decisions,set_selected,selected_hits,commit,report_paths

class Patch08Fix1V1068Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.repo=Repository(self.root/'data');self.source=self.root/'receive.txt';self.out=self.root/'out'
        self.base=QSO('2026-09-13','07:45','7','CW','JL7AIA','599','599','Japan','Soka Saitama Japan','AK AT-TEST','')
    def add(self,q,own='JH1HST'):
        self.repo.open(self.repo.path_for(own,'',q.date)).append(q)
    def plan(self,line):
        self.source.write_text(line,encoding='utf-8');return prepare(self.repo,self.source,'JH1HST','JST','hQSL.R')

    def test_version_stays_1068(self):
        self.assertEqual(VERSION,'1.14')

    def test_one_input_may_select_multiple_valid_qsos(self):
        self.add(self.base)
        self.add(replace(self.base,remarks='04 FOX'))
        p=self.plan('2026-09-13 07:45 JL7AIA');e=p.entries[0]
        self.assertEqual(len(e.candidates),2);self.assertFalse(selected_hits(e))
        set_selected(e,e.candidates[0],True);set_selected(e,e.candidates[1],True)
        self.assertEqual(len(selected_hits(e)),2);self.assertIsNone(e.pick)
        rows=decisions(p);self.assertEqual(len(rows),2);self.assertTrue(all(r['state']=='更新予定' for r in rows))
        _,journal,_=commit(self.repo,p,self.out)
        result,unprocessed=report_paths(journal);self.assertIsNone(unprocessed)
        text=result.read_text(encoding='utf-8-sig')
        self.assertIn('AK AT-TEST hQSL.R',text);self.assertIn('04 FOX hQSL.R',text)

    def test_portable_difference_inside_three_minutes_is_manual_candidate(self):
        q=replace(self.base,date='2026-07-26',time='09:54',call='JH6JRN/6',band='21',remarks='4610 KG')
        self.add(q)
        p=self.plan('2026-07-26 09:54 JH6JRN');e=p.entries[0]
        self.assertFalse(e.candidates);self.assertEqual(len(e.manual_candidates),1)
        self.assertEqual(e.manual_candidates[0].qso.call,'JH6JRN/6')
        self.assertEqual(decisions(p)[0]['state'],'手動候補')
        set_selected(e,e.manual_candidates[0],True)
        r=decisions(p)[0];self.assertEqual(r['state'],'更新予定');self.assertTrue(r['manual']);self.assertIn('移動表記差',r['reason'])

    def test_far_same_call_is_not_manual_candidate(self):
        q=replace(self.base,time='13:46',call='JQ1TIV')
        self.add(q)
        p=self.plan('2026-09-13 07:45 JQ1TIV');e=p.entries[0]
        self.assertFalse(e.candidates);self.assertFalse(e.manual_candidates)
        self.assertEqual(decisions(p)[0]['state'],'未一致')

if __name__=='__main__':unittest.main()
