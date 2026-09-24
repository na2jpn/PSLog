"""User-decided freedom of entry: real scoring/export and unchanged originals."""
import unittest,tempfile
from copy import deepcopy
from pathlib import Path
from PySide6.QtWidgets import QApplication
from contest_rules import score
from contest_export import plan,key
from contest import select_logs
from storage import Repository
from model import QSO
from contest_calendar import working_rule
import test_regional_2026 as regional
import test_last6 as last
from cabrillo_templates import loads as load_template
from contest_international import expected_headers

class UserPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def test_ja9_high_bands_and_explicit_single_band(self):
        r=regional.rule('ja9_vu');c=next(c for c in r['event']['categories'] if c['id']=='SM');ctx=regional.context(r,c);v=regional.sample(r,c)[0]
        s=score(r,[dict(v,band='24G'),dict(v,band='77G',call='JA9ZZZ')],ctx)
        self.assertEqual(s.points,6,s.problems);self.assertIsNotNone(s.total,s.problems)
        ctx['category']='S10G'
        for b in ['10.1G','10.4G']:self.assertEqual(score(r,[dict(v,band=b)],ctx).points,3)
        self.assertEqual(score(r,[dict(v,band='77G')],ctx).points,0)
        ctx['category']='SM';self.assertIsNone(score(r,[dict(v,band='77G')],ctx).total)
    def test_calendar_ui_defaults_and_override_persist(self):
        from contest_event_ui import EventDialog
        r=regional.rule('niigata_low_band');c=r['event']['categories'][0];ctx=regional.context(r,c)
        dlg=EventDialog(r['event'],ctx);self.assertIn('2026-06-14',dlg.calendar.toPlainText())
        dlg.calendar.setPlainText('2027-06-20 19:00 / 2027-06-20 22:00');dlg.apply()
        self.assertEqual(dlg.result(),dlg.Accepted,dlg.status.text());self.assertTrue(dlg.context['calendar_advisory'])
        self.assertEqual(dlg.context['calendar_windows'][0]['start'],'2027-06-20 19:00')
        second=EventDialog(r['event'],dlg.context);self.assertIn('2027-06-20',second.calendar.toPlainText());second.close();dlg.close()
    def test_new_year_and_outside_time_export_without_changing_qso(self):
        r=regional.rule('niigata_low_band');c=next(c for c in r['event']['categories'] if c['id']=='GMLM');ctx=regional.context(r,c)
        ctx.update(calendar_advisory=True,calendar_windows=[dict(start='2027-06-20 19:00',end='2027-06-20 22:00',bands=['1.9','3.5'])])
        original=deepcopy(r);v=dict(regional.sample(r,c)[0],date='2027-06-20',time='23:00');s=score(r,[v],ctx)
        self.assertEqual(s.total,1,s.problems);self.assertTrue(s.timing_summary);self.assertEqual(r,original)
        with tempfile.TemporaryDirectory() as tmp:
            repo=Repository(tmp);p=repo.path_for('JH1HST','',v['date']);repo.open(p).append(QSO(v['date'],v['time'],v['band'],v['mode'],v['call'],'599','599','原','原','原',''))
            raw=p.read_bytes();sel=select_logs(repo,[p],'JH1HST');d={key(sel.rows[0]):dict(sent=v['sent'],received=v['exchange'],status='確認済み')}
            info=dict(contest=r['event']['submission']['contest'],category='GMLM',categoryname=c['name'],name='試験',address='試験',power='10',date='2027-06-21',signature='試験',oath=True,email='test@example.com',opplace='東京',comments='')
            out=plan(sel,r,d,'JARL R1.0',info,context=ctx).preview();self.assertIn('2027-06-20',out);self.assertIn('23:00',out);self.assertEqual(raw,p.read_bytes())
    def test_gifu_declaration_can_differ_from_log_count(self):
        import test_remaining28 as m
        r=m.rule('all_gifu');c=m.category(r,'X-MJ');ctx,rows=m.setup(r,c)
        ctx['qso_operators'][0]['qsos']=75;ctx['qso_operators'][1]['qsos']=25
        for v in rows:v.pop('operator_name',None)
        s=score(r,rows,ctx);self.assertIsNotNone(s.total,s.problems)
        from contest_participation import submission_info
        out=submission_info(r,ctx,{'multioplist':'','comments':''},'JH1HST');self.assertIn('75交信',out['comments']);self.assertEqual(ctx['category'],'X-MJ')
    def test_unknown_digital_score_and_export(self):
        import test_remaining9 as m
        r=m.rule('cq-vhf-digi');c=next(c for c in r['event']['categories'] if c['id']=='SO_LOW_ALL')
        ctx=dict(category=c['id'],station_type='individual',power=10,flags={f:True for f in r['event']['required_flags']+c['required_flags']},declarations={})
        v=dict(own='JH1HST',date='2026-07-18',time='23:00',band='50',mode='NEW-DIGI',call='JA1AAA',sent='PM95',exchange='PM96',my_grid='PM95',his_grid='PM96',rst_sent='',rst_received='')
        s=score(r,[v],ctx);self.assertEqual(s.total,1,s.problems)
        with tempfile.TemporaryDirectory() as tmp:
            outputs=last.export_case(tmp,r,c,ctx,[v]);self.assertIn('DG',outputs[0])
    def test_rtty_provisional_name_and_mhz_output(self):
        r,c,ctx,rows=last.fixture('jarl_world_wide_rtty','SOLP');rows[0].update(band='14',sent='00');ctx['declarations']['exchange_age']='00'
        with tempfile.TemporaryDirectory() as tmp:
            repo=Repository(tmp);v=rows[0];p=repo.path_for(v['own'],'',v['date']);repo.open(p).append(QSO(v['date'],v['time'],v['band'],v['mode'],v['call'],'599','599','','','',''));raw=p.read_bytes();sel=select_logs(repo,[p],v['own']);draft={key(sel.rows[0]):dict(sent='00',received='99',country='HL',continent='AS',status='確認済み',checklog=True)}
            t=load_template((last.ROOT/'config/templates/cabrillo/jarl_world_wide_rtty_2026.txt').read_text(encoding='utf-8'));info=dict(CONTEST='JARL-RTTY-EDITED',NAME='Test',ADDRESS='Test',EMAIL='test@example.com',**expected_headers(r,c,ctx))
            # Whole checklog avoids minimum-contact entry conditions for an X-only log.
            ctx['submission_mode']='checklog';info['CATEGORY-OPERATOR']='CHECKLOG'
            out=plan(sel,r,draft,'Cabrillo',info,t,context=ctx).preview();self.assertIn('CONTEST: JARL-RTTY-EDITED',out);self.assertIn('X-QSO: 14 ',out);self.assertIn('00',out);self.assertIn('99',out);self.assertEqual(raw,p.read_bytes())
