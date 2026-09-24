from copy import deepcopy
from pathlib import Path
import tempfile,unittest
from PySide6.QtWidgets import QApplication
from contest_rules import score,loads,dumps,RuleStore
from contest_event_ui import EventDialog
from contest_timing import HISTORY_FLAG,parse_blocks
from contest_ui import score_breakdown
from test_contest_event import rule,entry,CTX


def setup(timing):
    r=rule();r['event']['categories'][0]['timing']=timing
    c=deepcopy(CTX);c['flags'][HISTORY_FLAG]=True
    return r,c

def operating():return dict(operating=dict(max_minutes=60,min_off_minutes=60))
def stay(action='exclude',ids=None):return dict(band_change=dict(kind='stay',min_minutes=10,tx_ids=ids or [],on_violation=action))
def blocks(*pairs):return [dict(start='2026-08-22 '+a,end='2026-08-22 '+b) for a,b in pairs]

class TimingTests(unittest.TestCase):
    def test_disabled_for_ordinary_categories(self):
        self.assertEqual(score(rule(),[entry(),entry(time='21:01',band='14')],CTX).total,4)
    def test_confirmed_history_required(self):
        r,c=setup(stay());c['flags'][HISTORY_FLAG]=False
        self.assertIsNone(score(r,[entry()],c).total)
        c['flags']=None;self.assertIsNone(score(r,[entry()],c).total)
    def test_no_inferred_off_time(self):
        r,c=setup(operating())
        self.assertIsNone(score(r,[entry(),entry(time='23:59')],c).total)
    def test_exact_hour_break_and_limit(self):
        r,c=setup(operating());c['operating_blocks']=blocks(('21:00','21:30'),('22:30','23:00'))
        s=score(r,[entry(),entry(time='22:59',call='JA1BBB')],c)
        self.assertEqual(s.total,2);self.assertIn('運用時間 60分',score_breakdown(s))
    def test_short_break_counts_as_operating(self):
        r,c=setup(operating());c['operating_blocks']=blocks(('21:00','21:30'),('22:29','22:59'))
        s=score(r,[entry(),entry(time='22:58',call='JA1BBB')],c)
        self.assertIsNone(s.total);self.assertTrue(any('119分' in p for p in s.problems))
    def test_zero_point_and_duplicate_contacts_need_coverage(self):
        r,c=setup(operating());c['operating_blocks']=blocks(('21:00','21:30'))
        for change in ({},{'exchange':'invalid'},{'band':'14'}):
            # Single-band category must not hide other-band operation history.
            r['event']['categories'][0]['bands']=['7']
            r['scoring']['eligible']=dict(field='exchange',op='eq',value='11')
            s=score(r,[entry(),entry(time='22:00',**change)],c)
            self.assertIsNone(s.total);self.assertTrue(any('運用区間に' in p for p in s.problems))
    def test_end_exclusive_overlap_and_closed_stage(self):
        r,c=setup(operating())
        for values in (blocks(('21:00','21:20')),blocks(('21:00','21:30'),('21:20','21:40')),blocks(('20:00','21:30'))):
            c['operating_blocks']=values;self.assertIsNone(score(r,[entry(time='21:20')],c).total)
        c['operating_blocks']=[dict(start='2026-08-22 23:30',end='2026-08-23 06:30')]
        self.assertIsNone(score(r,[entry(time='23:30')],c).total)
    def test_utc_blocks_and_year_boundary(self):
        r,c=setup(operating());r['event']['timezone']='UTC';r['event']['windows']=[dict(start='2026-12-31 23:00',end='2027-01-01 01:00',bands=[])]
        c['operating_blocks']=[dict(start='2026-12-31 23:30',end='2027-01-01 00:30')]
        self.assertEqual(score(r,[entry(date='2027-01-01',time='09:29')],c).total,1)
    def test_stay_9_10_minutes_exclusion_and_later_recontact(self):
        r,c=setup(stay());rows=[entry(),entry(band='14',time='21:09'),entry(band='14',time='21:10'),entry(time='21:11',call='JA1BBB'),entry(time='21:20',call='JA1BBB')]
        original=deepcopy(rows);s=score(r,rows,c)
        self.assertEqual([x['points'] for x in s.rows],[1,0,1,0,1]);self.assertEqual(s.total,6)
        self.assertEqual(rows,original);self.assertIn('2件',s.timing_summary[0])
    def test_unsorted_input_is_checked_chronologically(self):
        r,c=setup(stay());s=score(r,[entry(time='21:09',band='14'),entry()],c)
        self.assertEqual([x['points'] for x in s.rows],[0,1])
    def test_two_series_and_missing_id(self):
        r,c=setup(stay(ids=['1','2']))
        self.assertIsNone(score(r,[entry()],c).total)
        self.assertEqual(score(r,[entry(tx='1'),entry(tx='2',band='14',time='21:01')],c).total,4)
        s=score(r,[entry(tx='1'),entry(tx='2',band='14',time='21:01'),entry(tx='1',band='14',time='21:09')],c)
        self.assertEqual(s.total,4)
    def test_hourly_boundary_and_first_qso_not_a_change(self):
        r,c=setup(dict(band_change=dict(kind='hourly',max_changes=1,tx_ids=[],on_violation='block')))
        rows=[entry(time='21:58'),entry(time='21:59',band='14'),entry(time='22:00',call='JA1BBB')]
        self.assertIsNotNone(score(r,rows,c).total)
        s=score(r,rows+[entry(time='22:01',band='14',call='JA1CCC')],c)
        self.assertIsNone(s.total);self.assertTrue(any('22時台' in p for p in s.problems))
    def test_hourly_count_separate_per_tx(self):
        r,c=setup(dict(band_change=dict(kind='hourly',max_changes=1,tx_ids=['0','1'],on_violation='block')))
        rows=[entry(tx='0'),entry(tx='1',band='14'),entry(tx='0',time='21:01',band='14'),entry(tx='1',time='21:01')]
        self.assertIsNotNone(score(r,rows,c).total)
    def test_same_minute_order_ambiguous(self):
        r,c=setup(stay());s=score(r,[entry(),entry(band='14')],c)
        self.assertIsNone(s.total);self.assertTrue(any('変更順' in p for p in s.problems))
    def test_roundtrip_schema_rejects_unknown_and_bad_values(self):
        r,c=setup(operating()|stay());self.assertEqual(loads(dumps(r)),r)
        for t in ({},{'operating':{'max_minutes':True,'min_off_minutes':60}},dict(band_change=dict(kind='hourly',max_changes=8,tx_ids=[],on_violation='exclude')),{'exec':'anything'}):
            r['event']['categories'][0]['timing']=t
            with self.assertRaises(ValueError):loads(dumps(r))
    def test_parser_strict_and_unchanged_context(self):
        self.assertEqual(len(parse_blocks('2026-08-22 21:00 / 2026-08-23 00:00')),1)
        for text in ['2026-8-22 21:00 / 2026-08-23 00:00','bad','2026-08-22 21:00 / 2026-08-22 21:00']:
            with self.assertRaises(ValueError):parse_blocks(text)
        r,c=setup(stay());original=deepcopy((r,c));score(r,[entry()],c);self.assertEqual((r,c),original)

class TimingUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def test_apply_and_reconfirmation_after_edit(self):
        r,c=setup(operating());c['operating_blocks']=blocks(('21:00','22:00'))
        d=EventDialog(r['event'],c);self.assertTrue(d.flags[HISTORY_FLAG].isChecked())
        d.blocks.setPlainText('2026-08-22 21:00 / 2026-08-22 21:30');self.assertFalse(d.flags[HISTORY_FLAG].isChecked())
        d.flags[HISTORY_FLAG].setChecked(True);d.apply();self.assertEqual(d.context['operating_blocks'],blocks(('21:00','21:30')));d.deleteLater()
    def test_invalid_block_stays_open(self):
        r,c=setup(operating());d=EventDialog(r['event'],c);d.blocks.setPlainText('invalid');d.apply()
        self.assertEqual(d.result(),0);self.assertTrue(d.status.text());d.deleteLater()
    def test_rule_editor_preserves_each_category_and_json(self):
        from contest_timing_ui import CategoryRulesDialog
        from contest_rule_ui import RuleEditor
        r=rule();second=deepcopy(r['event']['categories'][0]);second['id']='B';r['event']['categories'].append(second)
        d=CategoryRulesDialog(r['event']);d.operating.setChecked(True);d.max_minutes.setValue(1800)
        d.category.setCurrentIndex(1);d.band_change.setChecked(True);d.kind.setCurrentIndex(1);d.limit.setValue(8);d.ids.setText('0,1');d.apply()
        self.assertEqual(d.value['categories'][0]['timing']['operating']['max_minutes'],1800)
        self.assertEqual(d.value['categories'][1]['timing']['band_change']['max_changes'],8)
        self.assertNotIn('timing',r['event']['categories'][0])
        r['event']=d.value
        with tempfile.TemporaryDirectory() as root:
            editor=RuleEditor(RuleStore(root),r);self.assertEqual(editor.collect()['event'],r['event']);editor.deleteLater()
        d.deleteLater()
    def test_draft_tx_change_resets_confirmation_only_when_needed(self):
        from contest_ui import ContestDialog
        from storage import Repository
        with tempfile.TemporaryDirectory() as root:
            w=ContestDialog(Repository(root));w.event_contexts={'test':{'flags':{HISTORY_FLAG:True}}};w.draft={'row':{'tx':'0'}}
            w.update_details_draft({'row':{'tx':'0','my_grid':'PM95'}});self.assertTrue(w.event_contexts['test']['flags'][HISTORY_FLAG])
            w.update_details_draft({'row':{'tx':'1'}});self.assertNotIn(HISTORY_FLAG,w.event_contexts['test']['flags']);w.timer.stop();w.deleteLater()
    def test_export_rechecks_operating_context_and_never_drops_required_tx(self):
        from storage import Repository
        from model import QSO
        from contest import select_logs
        from contest_export import plan,key
        with tempfile.TemporaryDirectory() as root:
            repo=Repository(root);p=repo.path_for('JH1HST','','2026-08-22');repo.open(p).append(QSO('2026-08-22','21:00','7','CW','JA1AAA','599','599','Tokyo Japan','Soka Japan','11',''))
            original=p.read_bytes();s=select_logs(repo,[p],'JH1HST');draft={key(s.rows[0]):dict(sent='13',received='11',status='確認済み',tx='0')}
            info=dict(contest='試験',category='A',name='試験',address='試験',power='100',date='2026-08-24',signature='試験',oath=True)
            r,c=setup(operating());c['operating_blocks']=blocks(('21:00','22:00'))
            self.assertIn('運用時間 60分',plan(s,r,draft,'JARL R2.1',info,context=c).warnings[0])
            c['operating_blocks']=blocks(('21:00','23:00'))
            with self.assertRaisesRegex(ValueError,'上限'):plan(s,r,draft,'JARL R2.1',info,context=c)
            r,c=setup(stay(ids=['0','1']))
            with self.assertRaisesRegex(ValueError,'系列表記'):plan(s,r,draft,'JARL R2.1',info,context=c)
            with self.assertRaisesRegex(ValueError,'TX列'):plan(s,r,draft,'Cabrillo',{},context=c)
            self.assertEqual(p.read_bytes(),original)

if __name__=='__main__':unittest.main()
