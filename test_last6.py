"""Cross-profile acceptance: all public categories, boundary cases, real exports."""
from test_remaining9 import ROOT,rule
from copy import deepcopy
from datetime import datetime,timedelta
from pathlib import Path
import unittest,tempfile
from PySide6.QtWidgets import QApplication
from model import QSO
from storage import Repository
from contest import select_logs,entries
from contest_rules import score
from contest_export import plan,key
from cabrillo_templates import loads as template_loads
from contest_international import expected_headers
from contest_timing import HISTORY_FLAG
IDS=['all_asian_dx_cw','all_asian_dx_phone','jarl_world_wide_rtty','ww-digi','all_okayama_ft','miyazaki']

def fixture(ident,category=None):
    r=rule(ident);e=r['event'];c=next((c for c in e['categories'] if c['id']==category),e['categories'][0]);start=datetime.strptime(e['windows'][0]['start'],'%Y-%m-%d %H:%M');dt=start+(timedelta(hours=9) if e['timezone']=='UTC' else timedelta())
    d={'own_entity':'JA','own_continent':'AS','exchange_age':'30','youth':'NONE','youth_birth':'-','unknown_grid':'確認','first24':'確認','kenjin':'県外、1990-2000宮崎市居住','operator_kind':'SO','locations':'実運用地'}
    ctx=dict(category=c['id'],station_type='individual',power=5,entry_categories=[c['id']],flags={f:True for f in e['required_flags']+c['required_flags']},declarations=d,age=18 if c['id']=='SOJR' else 70,licensedate='2026-01-01',operating_blocks=[{'start':start.strftime('%Y-%m-%d %H:%M'),'end':(start+timedelta(minutes=60)).strftime('%Y-%m-%d %H:%M')}]);ctx['flags'][HISTORY_FLAG]=True
    mode=c['modes'][0];rst='' if ident in ('ww-digi','all_okayama_ft') else '599' if mode in ('CW','RTTY') else '59'
    v=dict(own='JH1HST',date=dt.strftime('%Y-%m-%d'),time=dt.strftime('%H:%M'),band=c['bands'][0],mode=mode,call='HL1AAA',sent='30',exchange='40',country='HL',continent='AS',rst_sent=rst,rst_received=rst,tx='0')
    if ident in ('ww-digi','all_okayama_ft'):v.update(sent='PM95',exchange='PM96',my_grid='PM95',his_grid='PM96',call='JA1AAA',country='JA')
    if ident=='miyazaki':
        sent='4501KJ' if c['id']=='MKJ' else '4501' if c['id'].startswith('M') else '10';d['sent_region']=sent;v.update(sent=sent,exchange='4502',call='JA6AAA',country='JA')
    if c['id'] in ('SOJR','SOSV'):d['exchange_age']=v['sent']=str(ctx['age'])
    rows=[v]
    if c['min_bands']>1:rows.append(dict(v,band=c['bands'][1],time=(dt+timedelta(minutes=10)).strftime('%H:%M'),mode='SSB' if c.get('required_mode_families') else mode,rst_sent='59' if c.get('required_mode_families') else rst,rst_received='59' if c.get('required_mode_families') else rst))
    return r,c,ctx,rows

def export_case(tmp,r,c,ctx,rows,whole=False):
    repo=Repository(tmp);paths=[]
    for v in rows:
        p=repo.path_for(v['own'],'',v['date']);repo.open(p).append(QSO(v['date'],v['time'],v['band'],v['mode'],v['call'],v.get('rst_sent',''),v.get('rst_received',''),'原QTH','原自局','原備考',''))
        if p not in paths:paths.append(p)
    sel=select_logs(repo,paths,rows[0]['own']);d={key(rec):dict(sent=v.get('sent',''),received=v.get('exchange',''),country=v.get('country'),continent=v.get('continent'),my_grid=v.get('my_grid',''),his_grid=v.get('his_grid',''),tx=v.get('tx',''),checklog=v.get('checklog',False),status='確認済み') for rec,v in zip(sel.rows,rows)};before={p:p.read_bytes() for p in paths};outs=[]
    for fmt in r['event']['submission']['formats']:
        if fmt=='Cabrillo':
            t=template_loads((ROOT/f'config/templates/cabrillo/{r["id"]}_2026.txt').read_text(encoding='utf-8'));h=expected_headers(r,{'_whole_checklog':True} if whole else c,ctx);info=dict(NAME='Test',ADDRESS='Address',EMAIL='test@example.com',LOCATION='DX',OPERATORS='JA1AAA JA1BBB',**h);out=plan(sel,r,d,fmt,info,t,context=ctx).preview()
        else:
            info=dict(contest=r['event']['submission']['contest'],category='CHECKLOG' if whole else c.get('submission_code',c['id']),categoryname=c['name'],name='試験',address='試験住所',power='5',date='2026-09-15',signature='試験',oath=True,zone=r['event']['submission']['zone'],multiop=c.get('operator')=='MO',multioplist='JA1AAA JA1BBB',comments='',opplace='試験運用地');out=plan(sel,r,d,fmt,info,context=ctx).preview()
        outs.append(out)
    assert all(p.read_bytes()==b for p,b in before.items())
    return outs

class LastSixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def test_all_118_categories_score_export_and_source_unchanged(self):
        counts=[]
        for ident in IDS:
            cats=rule(ident)['event']['categories'];counts.append(len(cats))
            for category in cats:
                with self.subTest(contest=ident,category=category['id']),tempfile.TemporaryDirectory() as tmp:
                    r,c,ctx,rows=fixture(ident,category['id']);before=deepcopy(rows);s=score(r,rows,ctx);self.assertIsNotNone(s.total,s.problems);self.assertEqual(rows,before)
                    outs=export_case(tmp,r,c,ctx,rows)
                    for out in outs:self.assertIn('JH1HST',out);self.assertIn('CLAIMED-SCORE: '+str(s.total) if 'START-OF-LOG' in out else '<TOTALSCORE>'+str(s.total)+'</TOTALSCORE>',out)
        self.assertEqual(counts,[22,22,5,28,12,29])
    def test_aadx_geography_bands_mm_and_wpx_multis(self):
        r,c,ctx,rows=fixture('all_asian_dx_cw','SOABHP');v=rows[0];v['band']='7'
        rs=[v,dict(v,band='3.5'),dict(v,band='1.9'),dict(v,call='DL1AAA',country='DL',continent='EU'),dict(v,call='JA1AAA',country='JA'),dict(v,call='DL1BBB/MM',country='',continent=''),dict(v,call='JD1AAA',country='JD1-OGASAWARA'),dict(v,call='JD1BBB',country='JD1-MINAMITORISHIMA',continent='OC')]
        s=score(r,rs,ctx);self.assertEqual((s.points,s.multi1,s.total),(14,6,84),s.problems)
        non=deepcopy(ctx);non['declarations'].update(own_entity='DL',own_continent='EU');s=score(r,[dict(v,call='JA1AAA',country='JA'),dict(v,call='JA1BBB',country='JA'),dict(v,call='JA2AAA',country='JA'),dict(v,call='W1AAA',country='K',continent='NA'),dict(v,call='JA1ABC/MM')],non);self.assertEqual((s.points,s.multi1,s.total),(3,2,6),s.problems)
        self.assertIsNone(score(r,[dict(v,exchange='00')],ctx).total)
        one=deepcopy(ctx);one['declarations']['exchange_age']='01';self.assertEqual(score(r,[dict(v,sent='01',exchange='01')],one).total,1)
    def test_aadx_first24_cutoff_and_ms_new_multi(self):
        r,c,ctx,rows=fixture('all_asian_dx_cw','SOABHP24');v=rows[0];ctx['operating_blocks']=[dict(start='2026-06-20 00:00',end='2026-06-22 00:00')]
        rs=[v,dict(v,date='2026-06-21',time='08:59',call='HL2AAA'),dict(v,date='2026-06-21',time='09:00',call='HL3AAA')];s=score(r,rs,ctx);self.assertEqual(s.points,6,s.problems);self.assertIn('24',s.rows[-1]['reason'])
        with tempfile.TemporaryDirectory() as tmp:self.assertEqual(sum(x.startswith('QSO:') for x in export_case(tmp,r,c,ctx,rs)[0].splitlines()),3)
        from contest_last6 import first24
        self.assertEqual(first24(dict(operating_blocks=[dict(start='2026-06-20 00:00',end='2026-06-20 12:00'),dict(start='2026-06-20 13:00',end='2026-06-22 00:00')])),datetime(2026,6,21,1))
        r,c,ctx,rows=fixture('all_asian_dx_cw','MSHP');v=rows[0];rs=[v,dict(v,tx='1',band='7',call='DL1AAA',country='DL',continent='EU',time='09:01')];self.assertIsNotNone(score(r,rs,ctx).total)
        rs.append(dict(rs[1],call='DL2AAA',time='09:02'));self.assertIsNone(score(r,rs,ctx).total)
    def test_rtty_mainland_islands_mm_age_youth(self):
        from contest_last6 import call_area
        for call,area in [('JA1AAA','1'),('7K1AAA','1'),('8J20AAA','0'),('JA1RL/3','3'),('VK/JA1YRL','0'),('JA1RL/7K4','4')]:self.assertEqual(call_area(call),area)
        r,c,ctx,rows=fixture('jarl_world_wide_rtty','SOLP');v=rows[0];rs=[dict(v,call='JA1AAA',country='JA',exchange='00'),dict(v,call='7K1AAA',country='JA',exchange='99'),dict(v,call='8J20AAA',country='JA'),dict(v,call='JD1AAA',country='JD1-OGASAWARA'),dict(v,call='JD1BBB',country='JD1-MINAMITORISHIMA',continent='OC'),dict(v,call='W1AAA/MM',country='',continent='')];s=score(r,rs,ctx);self.assertEqual((s.points,s.multi1,s.total),(13,4,52),s.problems)
        ctx['declarations'].update(youth='YOUTH',youth_birth='2001-10-17');self.assertIsNotNone(score(r,[v],ctx).total)
        with tempfile.TemporaryDirectory() as tmp:
            for out in export_case(tmp,r,c,ctx,[v]):self.assertIn('CATEGORY-OVERLAY: YOUTH' if out.startswith('START-OF-LOG:') else '<AGE>YOUTH</AGE>',out)
        ctx['declarations']['youth_birth']='2000-10-17';self.assertIsNone(score(r,[v],ctx).total)
    def test_ww_digi_distance_duplicates_and_unknown_export(self):
        r,c,ctx,rows=fixture('ww-digi','SO_ONE_LOW_ALL');v=rows[0]
        s=score(r,[v,dict(v,mode='FT8'),dict(v,call='JA2AAA',his_grid='PM97',exchange='PM97'),dict(v,band='7')],ctx);self.assertEqual((s.points,s.multi1,s.total),(3,2,6),s.problems)
        unknown=dict(v,call='JA3AAA',his_grid='ZZ00',exchange='ZZ00');s=score(r,[v,unknown],ctx);self.assertIsNone(s.total);self.assertFalse(s.problems);self.assertTrue(s.unscored_submission);self.assertIsNone(s.rows[-1]['points'])
        with tempfile.TemporaryDirectory() as tmp:
            out=export_case(tmp,r,c,ctx,[v,unknown])[0];self.assertNotIn('CLAIMED-SCORE:',out);self.assertIn('ZZ00',out);self.assertNotIn('599',out)
        self.assertIsNone(score(r,[dict(v,my_grid='ZZ00')],ctx).total)
    def test_grid_user_example_40w_no_report_and_mo_changes(self):
        r,c,ctx,rows=fixture('all_okayama_ft','L-SD');v=rows[0];v.update(band='7',my_grid='PM95AA');ctx['power']=40;s=score(r,[v,dict(v,mode='FT8')],ctx);self.assertEqual(s.total,1,s.problems)
        self.assertIsNone(score(r,[dict(v,mode='FT2')],ctx).total);self.assertIsNone(score(r,[dict(v,his_grid='ZZ00')],ctx).total)
        ctx['entry_categories']=['L-SD','H-SD'];self.assertIsNotNone(score(r,[v],ctx).total);ctx['entry_categories']=['L-SD','L-SDP'];self.assertIsNone(score(r,[v],ctx).total)
        r,c,ctx,rows=fixture('ww-digi','MO_ONE_LOW');v=rows[0];rs=[dict(v,time='21:'+f'{i:02}',band='7' if i%2 else '14',call=f'JA1A{chr(65+i)}') for i in range(10)];self.assertIsNone(score(r,rs,ctx).total)
    def test_miyazaki_foreign_no_multi_kj_and_manual_duplicate(self):
        r,c,ctx,rows=fixture('miyazaki','M7');v=rows[0];foreign=dict(v,call='DL1AAA',sent='',exchange='',country='DL',continent='EU');s=score(r,[v,foreign],ctx);self.assertEqual((s.points,s.multi1,s.total),(2,2,4),s.problems)
        r,c,ctx,rows=fixture('miyazaki','MKJ');v=rows[0];foreign=dict(v,call='DL1AAA',exchange='',country='DL',continent='EU');s=score(r,[v,foreign],ctx);self.assertEqual((s.points,s.multi1,s.total),(2,1,2),s.problems)
        with tempfile.TemporaryDirectory() as tmp:
            out=export_case(tmp,r,c,ctx,[v,foreign])[0];self.assertIn('DL1AAA',out);self.assertIn('CALLSIGN SENTNo RCVNo MULTI PTS',out)
        r,c,ctx,rows=fixture('miyazaki','X7');v=rows[0];s=score(r,[dict(v,exchange='10'),dict(v,call='JA6BBB',exchange='4502KJ'),dict(v,call='JA6CCC',exchange='4502')],ctx);self.assertEqual((s.points,s.multi1,s.total),(2,1,2),s.problems)
        s=score(r,[dict(v,checklog=True),dict(v,exchange='4503')],ctx);self.assertEqual(s.total,1,s.problems)
    def test_event_end_boundary_checklogs_and_rsts(self):
        for ident in IDS:
            r,c,ctx,rows=fixture(ident);v=rows[0];end=datetime.strptime(r['event']['windows'][-1]['end'],'%Y-%m-%d %H:%M')+(timedelta(hours=9) if r['event']['timezone']=='UTC' else timedelta());edge=dict(v,date=end.strftime('%Y-%m-%d'),time=end.strftime('%H:%M'),call='JA9ZZZ');s=score(r,rows+[edge],ctx);self.assertEqual(s.rows[-1]['reason'],'開催時間・ステージ対象外')
            if ident not in ('miyazaki',):
                with self.subTest(ident=ident),tempfile.TemporaryDirectory() as tmp:
                    ctx['submission_mode']='checklog';out=export_case(tmp,r,c,ctx,rows,True)[0];self.assertIn('CHECKLOG',out)

        r,c,ctx,rows=fixture('ww-digi');ctx['submission_mode']='checklog'
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(ValueError):export_case(tmp,r,c,ctx,[dict(rows[0],mode='NOTFT8')],True)
