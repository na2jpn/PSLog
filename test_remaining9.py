"""Acceptance tests for new definitions; progress is committed separately."""
from copy import deepcopy
from pathlib import Path
import unittest,tempfile
from PySide6.QtWidgets import QApplication
from contest_rules import loads,score
from contest import select_logs,entries
from contest_export import plan,key
from contest_submit_ui import DetailsDialog
from storage import Repository
from model import QSO
ROOT=Path(__file__).parent

def rule(ident):return loads((ROOT/f'config/rules/{ident}_{2025 if ident in ("cq-ww-cw","cq-ww-ssb") else 2026}.txt').read_text(encoding='utf-8'))
def setup(r,c):
    e=r['event'];ctx=dict(category=c['id'],station_type='individual',power=10,entry_categories=[c['id']],flags={f:True for f in e['required_flags']+c['required_flags']},declarations={})
    row=dict(own='JH1HST',date='2026-01-12',time='09:00',band=c['bands'][0],mode='CW',remote_mode='CW',call='JA1AAA',sent=c['sent_codes'][0],exchange='1321',rst_sent='599',rst_received='599')
    return ctx,row

class Remaining9Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def test_saitama_all_28_categories_and_export(self):
        r=rule('all_saitama');self.assertEqual(len(r['event']['categories']),28)
        for c in r['event']['categories']:
            with self.subTest(c=c['id']),tempfile.TemporaryDirectory() as tmp:
                ctx,v=setup(r,c);before=deepcopy(v);s=score(r,[v],ctx);self.assertEqual(s.total,3,s.problems);self.assertEqual(v,before)
                repo=Repository(tmp);p=repo.path_for('JH1HST','',v['date']);repo.open(p).append(QSO(v['date'],v['time'],v['band'],v['mode'],v['call'],'599','599','原QTH','原自局QTH','原備考',''))
                sel=select_logs(repo,[p],'JH1HST');d={key(sel.rows[0]):dict(sent=v['sent'],received=v['exchange'],remote_mode='CW',status='確認済み')};raw=p.read_bytes()
                info=dict(contest=r['name'],category=c['id'],categoryname=c['name'],name='試験',address='試験住所',power='10',date='2026-09-15',signature='試験',oath=True,zone='JST',multiop=c['operator']=='MO',multioplist='JA1AAA JA1BBB',comments='')
                for fmt in r['event']['submission']['formats']:
                    output=plan(sel,r,d,fmt,info,context=ctx).preview();self.assertIn('<TOTALSCORE>3</TOTALSCORE>',output);self.assertIn('1321',output)
                self.assertEqual(raw,p.read_bytes())
                dialog=DetailsDialog(sel,d,event=r['event']);self.assertIsNotNone(dialog.remote_mode_column);dialog.table.item(0,dialog.remote_mode_column).setText('SSB');self.assertEqual(entries(sel,dialog.draft)[0]['remote_mode'],'SSB');dialog.close()
    def test_saitama_cross_mode_duplicate_and_multis(self):
        r=rule('all_saitama');ctx,v=setup(r,r['event']['categories'][0])
        rows=[v,dict(v,remote_mode='SSB'),dict(v,mode='FM',remote_mode='CW'),dict(v,call='JA2BBB',exchange='20'),dict(v,call='JA2BBB',exchange='20',mode='SSB',remote_mode='CW')]
        s=score(r,rows,ctx);self.assertEqual((s.points,s.multi1,s.total),(8,2,16),s.problems);self.assertEqual(s.rows[2]['reason'],'重複')
        self.assertIsNone(score(r,[dict(v,remote_mode='')],ctx).total)
        self.assertEqual(score(r,[dict(v,mode='A2A')],ctx).points,3)
    def test_saitama_dictionary_time_and_entry_boundaries(self):
        r=rule('all_saitama');ctx,v=setup(r,r['event']['categories'][0]);codes=r['event']['exchange']['codes']
        self.assertEqual(len(r['event']['regional']['local_a']),72)
        for k in ['1321','134401','134410','130089','130093','02','101']:self.assertIn(k,codes)
        for k in ['13','1344','13008']:self.assertNotIn(k,codes)
        self.assertEqual(score(r,[v,dict(v,time='15:00',call='JA1BBB')],ctx).points,3)
        self.assertIsNone(score(r,[v],dict(ctx,entry_categories=['S-SA','X-SA'])).total)
        self.assertIsNone(score(r,[dict(v,sent='20')],ctx).total)
    def test_cqvhf_all_categories_score_export_and_original(self):
        from cabrillo_templates import loads as template_loads
        from contest_international import expected_headers
        from contest_timing import HISTORY_FLAG
        for ident in ['cq-vhf-ssbcw','cq-vhf-digi']:
            r=rule(ident);self.assertEqual(len(r['event']['categories']),12);e=r['event'];t=template_loads((ROOT/f'config/templates/cabrillo/{ident}_2026.txt').read_text(encoding='utf-8'))
            for c in e['categories']:
                with self.subTest(contest=ident,category=c['id']),tempfile.TemporaryDirectory() as tmp:
                    own='JH1HST/R' if c['id']=='ROVER' else 'JH1HST';ctx=dict(category=c['id'],station_type='individual',power=5,flags={f:True for f in e['required_flags']+c['required_flags']},declarations={'operator_count':'1','rover_locations':'PM95 to PM96, all equipment moved 100m'},operating_blocks=[{'start':e['windows'][0]['start'],'end':e['windows'][0]['start'][:10]+' 15:00'}]);ctx['flags'][HISTORY_FLAG]=True
                    # UTC14 equals JST23 on the same calendar day.
                    v=dict(own=own,date=e['windows'][0]['start'][:10],time='23:00',band=c['bands'][0],mode=c['modes'][0],call='JA1AAA',my_grid='PM95AA',his_grid='PM96AA',sent='PM95',exchange='PM96')
                    rows=[v,dict(v,my_grid='PM96',time='23:01')] if c['id']=='ROVER' else [v]
                    if c['id']=='ROVER':rows[1]['sent']='PM96'
                    before=deepcopy(rows);s=score(r,rows,ctx);self.assertIsNotNone(s.total,s.problems);self.assertEqual(rows,before)
                    repo=Repository(tmp);p=repo.path_for(own,'',v['date'])
                    for row in rows:repo.open(p).append(QSO(row['date'],row['time'],row['band'],row['mode'],row['call'],'','','原QTH','原自局','原備考',''))
                    sel=select_logs(repo,[p],own);d={key(rec):dict(sent=row['sent'],received=row['exchange'],my_grid=row['my_grid'],his_grid=row['his_grid'],status='確認済み') for rec,row in zip(sel.rows,rows)};raw=p.read_bytes()
                    info=dict(NAME='Test',ADDRESS='Test address',EMAIL='test@example.com',LOCATION='DX',OPERATORS='JA1AAA JA1BBB',**expected_headers(r,c,ctx));info.setdefault('CATEGORY-MODE','MIXED');info.setdefault('CATEGORY-POWER','LOW');info['CATEGORY-TRANSMITTER']='ONE'
                    out=plan(sel,r,d,'Cabrillo',info,t,context=ctx).preview();self.assertIn('CONTEST: '+ident.upper(),out);self.assertIn('CLAIMED-SCORE: '+str(s.total),out);qso=[x for x in out.splitlines() if x.startswith('QSO:')][0].split();self.assertEqual(len(qso),9);self.assertEqual(qso[4],'1400');self.assertEqual(qso[6],'PM95');self.assertNotIn('599',out);self.assertEqual(raw,p.read_bytes())
                    bad=dict(info,**{'CATEGORY-BAND':'INVALID'})
                    with self.assertRaises(ValueError):plan(sel,r,d,'Cabrillo',bad,t,context=ctx)
    def test_cqvhf_rover_return_and_band_multipliers(self):
        r=rule('cq-vhf-ssbcw');c=next(c for c in r['event']['categories'] if c['id']=='ROVER');e=r['event'];ctx=dict(category='ROVER',station_type='individual',power=10,flags={f:True for f in e['required_flags']+c['required_flags']},declarations={'operator_count':'1','rover_locations':'Two locations 100m apart'})
        v=dict(own='JH1HST/R',date='2026-07-04',time='23:00',band='50',mode='CW',call='JA1AAA',my_grid='PM95',his_grid='PM96')
        rows=[v,dict(v,my_grid='PM96'),dict(v,band='144'),dict(v,mode='SSB')]
        s=score(r,rows,ctx);self.assertEqual((s.points,s.multi1,s.total),(4,3,12),s.problems);self.assertEqual(s.rows[-1]['reason'],'重複')
        fixed=next(c for c in e['categories'] if c['id']=='SO_LOW_ALL');ct=dict(ctx,category=fixed['id'],flags={f:True for f in e['required_flags']+fixed['required_flags']})
        self.assertIsNone(score(r,rows,ct).total)
        self.assertIsNone(score(r,[dict(v,his_grid='ZZ00')],ctx).total)
    def test_cq160_all_categories_export_and_original(self):
        from cabrillo_templates import loads as template_loads
        from contest_international import expected_headers
        from contest_timing import HISTORY_FLAG
        from datetime import datetime,timedelta
        for ident in ['cq-160-cw','cq-160-ssb']:
            r=rule(ident);e=r['event'];t=template_loads((ROOT/f'config/templates/cabrillo/{ident}_2026.txt').read_text(encoding='utf-8'));self.assertEqual(len(e['categories']),6)
            for c in e['categories']:
                with self.subTest(contest=ident,category=c['id']),tempfile.TemporaryDirectory() as tmp:
                    start=e['windows'][0]['start'];jst=datetime.strptime(start,'%Y-%m-%d %H:%M')+timedelta(hours=9);end=(datetime.strptime(start,'%Y-%m-%d %H:%M')+timedelta(hours=1)).strftime('%Y-%m-%d %H:%M')
                    ctx=dict(category=c['id'],station_type='individual',power=5,flags={f:True for f in e['required_flags']+c['required_flags']},declarations={'own_cq_entity':'JA','own_continent':'AS'},operating_blocks=[{'start':start,'end':end}]);ctx['flags'][HISTORY_FLAG]=True
                    mode=c['modes'][0];rst='599' if mode=='CW' else '59';v=dict(own='JH1HST',date=jst.strftime('%Y-%m-%d'),time=jst.strftime('%H:%M'),band='1.9',mode=mode,call='W1AAA',sent='25',exchange='MA',cq_entity='K',continent='NA',rst_sent=rst,rst_received=rst)
                    s=score(r,[v],ctx);self.assertEqual((s.points,s.multi1,s.total),(10,1,10),s.problems)
                    repo=Repository(tmp);p=repo.path_for('JH1HST','',v['date']);repo.open(p).append(QSO(v['date'],v['time'],'1.9',mode,v['call'],rst,rst,'original','original','original',''))
                    sel=select_logs(repo,[p],'JH1HST');d={key(sel.rows[0]):dict(sent='25',received='MA',cq_entity='K',continent='NA',frequency='1810' if mode=='CW' else '1855',status='確認済み')};raw=p.read_bytes()
                    info=dict(NAME='Test',ADDRESS='Test address',EMAIL='test@example.com',LOCATION='DX',OPERATORS='JA1AAA JA1BBB',**expected_headers(r,c,ctx))
                    out=plan(sel,r,d,'Cabrillo',info,t,context=ctx).preview();self.assertIn('CLAIMED-SCORE: 10',out);self.assertIn('CONTEST: '+ident.upper(),out);self.assertIn(start[:10],out);self.assertEqual(raw,p.read_bytes());line=next(x for x in out.splitlines() if x.startswith('QSO:'));self.assertEqual(len(line.split()),11)
                    dialog=DetailsDialog(sel,d,event=e);self.assertIsNotNone(dialog.entity_column);self.assertEqual(dialog.table.item(0,dialog.entity_column).text(),'K');dialog.close()
    def test_cq160_points_provinces_and_mm(self):
        from contest_timing import HISTORY_FLAG
        r=rule('cq-160-cw');e=r['event'];c=e['categories'][0];ctx=dict(category=c['id'],station_type='individual',power=10,flags={f:True for f in e['required_flags']+c['required_flags']},declarations={'own_cq_entity':'JA','own_continent':'AS'},operating_blocks=[{'start':'2026-01-23 22:00','end':'2026-01-23 23:00'}]);ctx['flags'][HISTORY_FLAG]=True
        v=dict(own='JH1HST',date='2026-01-24',time='07:00',band='1.9',mode='CW',call='JA1AAA',sent='25',exchange='25',cq_entity='JA',continent='AS',rst_sent='599',rst_received='599')
        rows=[v,dict(v,call='HL1AAA',cq_entity='HL'),dict(v,call='DL1AAA',cq_entity='DL',continent='EU',exchange='14'),dict(v,call='W1AAA',cq_entity='K',continent='NA',exchange='MA'),dict(v,call='VE1AAA',cq_entity='VE',continent='NA',exchange='VO1'),dict(v,call='VE2AAA',cq_entity='VE',continent='NA',exchange='NF'),dict(v,call='MM1AAA/MM',cq_entity='',continent='')]
        s=score(r,rows,ctx);self.assertEqual((s.points,s.multi1,s.total),(52,5,260),s.problems)
        self.assertIsNone(score(r,[dict(v,cq_entity='')],ctx).total)
        self.assertIsNone(score(r,[dict(v,cq_entity='K',exchange='AK')],ctx).total)
        self.assertIsNone(score(r,[dict(v,rst_sent='')],ctx).total)
    def test_nara_all_categories_and_two_actual_multiplier_columns(self):
        r=rule('nara_vuhf');e=r['event'];self.assertEqual(len(e['categories']),24)
        for c in e['categories']:
            with self.subTest(category=c['id']),tempfile.TemporaryDirectory() as tmp:
                sent='00N' if c['id'].startswith('N') else '00';ctx=dict(category=c['id'],station_type='individual',power=10,entry_categories=[c['id']],flags={f:True for f in e['required_flags']+c['required_flags']},declarations={'call_license_year':'2000','operator_kind':'SO','all_locations':'実運用地'})
                rows=[]
                for i,b in enumerate(c['bands'][:c['min_bands']]):
                    w=next(w for w in e['windows'] if b in w['bands']);rows.append(dict(own='JH1HST',date=w['start'][:10],time=w['start'][11:],band=b,mode=c['modes'][0],call='JA3AA'+chr(65+i),sent=sent,exchange='02N',operator_name='JH1HST',rst_sent='599',rst_received='599'))
                s=score(r,rows,ctx);self.assertIsNotNone(s.total,s.problems)
                repo=Repository(tmp);p=repo.path_for('JH1HST','',rows[0]['date'])
                for v in rows:repo.open(p).append(QSO(v['date'],v['time'],v['band'],v['mode'],v['call'],'599','599','original','original','original',''))
                sel=select_logs(repo,[p],'JH1HST');d={key(rec):dict(sent=v['sent'],received=v['exchange'],operator_name='JH1HST',status='確認済み') for rec,v in zip(sel.rows,rows)};raw=p.read_bytes();info=dict(contest=r['name'],category=c['id'],categoryname=c['name'],name='試験',address='試験住所',power='10',date='2026-09-15',signature='試験',oath=True,zone='JST',opplace='実運用地',multiop=False,comments='')
                out=plan(sel,r,d,'JARL R1.0',info,context=ctx).preview();self.assertIn('Multi1 Multi2 PTS',out);self.assertIn('599'+sent+' 59902N A 02 1',out);self.assertIn('<TOTALSCORE>'+str(s.total)+'</TOTALSCORE>',out);self.assertEqual(raw,p.read_bytes())
    def test_nara_independent_product_and_year_boundaries(self):
        r=rule('nara_vuhf');c=next(c for c in r['event']['categories'] if c['id']=='NCM');e=r['event'];ctx=dict(category='NCM',station_type='individual',power=10,entry_categories=['NCM'],flags={f:True for f in e['required_flags']},declarations={'call_license_year':'2000','operator_kind':'SO','all_locations':'奈良県内'})
        v=dict(own='JH1HST',date='2026-08-08',time='19:00',band='28',mode='CW',call='JA1ABC/3',sent='00N',exchange='52N',operator_name='JH1HST',rst_sent='599',rst_received='599')
        rows=[v,dict(v,call='JA1ADC',exchange='02N'),dict(v,call='JA2ABC',band='50',time='20:00'),dict(v,call='JA2ABD',band='50',time='20:01',exchange='02N'),dict(v,call='JA2ACD',band='50',time='20:02')]
        s=score(r,rows,ctx);self.assertEqual((s.points,s.multi1,s.multi2,s.total),(5,3,4,60),s.problems)
        self.assertIsNone(score(r,rows,dict(ctx,entry_categories=['NCM','NC28'])).total)
        self.assertIsNone(score(r,[dict(v,exchange='27N')]+rows[2:],ctx).total)
        self.assertIsNone(score(r,rows,dict(ctx,declarations=dict(ctx['declarations'],call_license_year='2001'))).total)
        # Next-day contact is still the same band duplicate.
        s=score(r,rows+[dict(v,date='2026-08-09',time='12:00')],ctx);self.assertEqual(s.total,60)
    def test_kyoto_all_categories_and_additive_export(self):
        r=rule('kyoto');e=r['event'];self.assertEqual(len(e['categories']),32)
        for c in e['categories']:
            with self.subTest(category=c['id']),tempfile.TemporaryDirectory() as tmp:
                ctx=dict(category=c['id'],station_type='individual',power=10,entry_categories=[c['id']],flags={f:True for f in e['required_flags']+c['required_flags']},declarations={'participation_age':'50','young_birthdate':'-','first_license_date':'対象外'})
                rows=[]
                for i,b in enumerate(c['bands'][:c['min_bands']]):
                    w=next(w for w in e['windows'] if b in w['bands']);rows.append(dict(own='JH1HST',date=w['start'][:10],time=w['start'][11:],band=b,mode='CW',call='JA3AA'+chr(65+i),sent='W04TK' if c['id'].startswith('I') else 'STTK',exchange='W10603',rst_sent='599',rst_received='599'))
                s=score(r,rows,ctx);self.assertIsNotNone(s.total,s.problems);self.assertEqual(s.multi1,2*len(rows))
                repo=Repository(tmp);paths=[]
                for v in rows:
                    p=repo.path_for('JH1HST','',v['date']);repo.open(p).append(QSO(v['date'],v['time'],v['band'],v['mode'],v['call'],'599','599','original','original','original',''));paths.append(p)
                paths=list(dict.fromkeys(paths));sel=select_logs(repo,paths,'JH1HST');mapping={(v['date'],v['time'],v['call']):v for v in rows};d={}
                for rec in sel.rows:
                    v=mapping[(rec[1].date,rec[1].time,rec[1].call)];d[key(rec)]=dict(sent=v['sent'],received=v['exchange'],status='確認済み')
                raw={p:p.read_bytes() for p in paths};info=dict(contest=r['name'],category=c['id'],categoryname=c['name'],name='試験',address='試験住所',power='10',date='2026-09-15',signature='試験',oath=True,zone='JST',multiop=c['operator']=='MO',multioplist='JA1AAA 一アマ JA1BBB 二アマ',comments='')
                out=plan(sel,r,d,'JARL R1.0',info,context=ctx).preview();self.assertIn('<TOTALSCORE>'+str(s.total)+'</TOTALSCORE>',out);self.assertIn(',2</SCORE>',out)
                for p in paths:self.assertEqual(raw[p],p.read_bytes())
    def test_kyoto_rounding_and_region_suffix(self):
        from contest_remaining9 import kyoto_number,kyoto_factor
        r=rule('kyoto');e=r['event'];c=next(c for c in e['categories'] if c['id']=='O7');ctx=dict(category='O7',station_type='individual',power=10,entry_categories=['O7'],flags={f:True for f in e['required_flags']},declarations={'participation_age':'50','young_birthdate':'-','first_license_date':'2025-02-02'})
        v=dict(own='JH1HST',date='2026-02-08',time='13:00',band='7',mode='CW',call='JA3AAA',sent='STTK',exchange='W10603',rst_sent='599',rst_received='599');rows=[v,dict(v,call='JA3BBB',exchange='W10604'),dict(v,call='JA3CCC',exchange='W10TK')]
        s=score(r,rows,ctx);self.assertEqual((s.points,s.multi1,str(s.multi2),s.total),(3,3,'2.5',23),s.problems)
        self.assertEqual(kyoto_number(e,'G08DAB'),('G08D','AB'))
        for date,factor in [('2025-02-01','1.5'),('2024-02-05','1.5'),('2024-02-04','1.2'),('2023-02-06','1.2'),('2023-02-05','1')]:self.assertEqual(str(kyoto_factor(c,dict(ctx,declarations=dict(ctx['declarations'],first_license_date=date)))),factor)
        self.assertIsNone(score(r,rows,dict(ctx,entry_categories=['O7','OC'])).total)
        self.assertEqual(score(r,rows+[dict(v,call='JA3DDD',time='16:00')],ctx).total,23)
        self.assertEqual(score(r,rows+[dict(v,call='JA1DDD',exchange='OSTK')],ctx).total,23)
    def test_cqww_all_categories_and_normalized_cabrillo(self):
        from cabrillo_templates import loads as template_loads
        from contest_international import expected_headers
        from contest_timing import HISTORY_FLAG
        for ident in ['cq-ww-cw','cq-ww-ssb','cq-ww-rtty']:
            r=rule(ident);e=r['event'];t=template_loads((ROOT/f'config/templates/cabrillo/{ident}_{r["year"]}.txt').read_text(encoding='utf-8'));self.assertEqual(len(e['categories']),41 if ident.endswith('rtty') else 47)
            for c in e['categories']:
                with self.subTest(contest=ident,category=c['id']),tempfile.TemporaryDirectory() as tmp:
                    date=e['windows'][0]['start'][:10];mode=c['modes'][0];rst='59' if mode=='SSB' else '599';ctx=dict(category=c['id'],station_type='individual',power=5,flags={f:True for f in e['required_flags']+c['required_flags']},declarations={'own_cq_entity':'JA','own_continent':'AS','own_cq_zone':'25','overlay':'NONE','overlay_evidence':'-'});ctx['flags'][HISTORY_FLAG]=True
                    v=dict(own='JH1HST',date=date,time='09:00',band=c['bands'][0],mode=mode,call='W1AAA',sent='25',exchange='05 MA' if mode=='RTTY' else '05',cq_entity='K',continent='NA',rst_sent=rst,rst_received=rst,tx='0')
                    s=score(r,[v],ctx);self.assertEqual(s.total,9 if mode=='RTTY' else 6,s.problems)
                    repo=Repository(tmp);p=repo.path_for('JH1HST','',date);repo.open(p).append(QSO(date,'09:00',v['band'],mode,'W1AAA',rst,rst,'original','original','original',''));sel=select_logs(repo,[p],'JH1HST');d={key(sel.rows[0]):dict(sent=v['sent'],received=v['exchange'],cq_entity='K',continent='NA',frequency={'1.9':'1810','3.5':'3510','7':'7010','14':'14050','21':'21050','28':'28050'}[v['band']],tx='0',status='確認済み')};raw=p.read_bytes()
                    info=dict(NAME='Test',ADDRESS='Test address',EMAIL='test@example.com',LOCATION='DX',OPERATORS='JA1AAA JA1BBB',**expected_headers(r,c,ctx));out=plan(sel,r,d,'Cabrillo',info,t,context=ctx).preview();self.assertIn('CLAIMED-SCORE: '+str(s.total),out);self.assertEqual(raw,p.read_bytes());line=next(x for x in out.splitlines() if x.startswith('QSO:'));self.assertEqual(len(line.split()),14 if mode=='RTTY' else 12)
    def test_cqww_zero_points_multis_and_ms_new_multiplier(self):
        from contest_timing import HISTORY_FLAG
        r=rule('cq-ww-cw');e=r['event'];c=e['categories'][0];ctx=dict(category=c['id'],station_type='individual',power=10,flags={f:True for f in e['required_flags']+c['required_flags']},declarations={'own_cq_entity':'JA','own_continent':'AS','own_cq_zone':'25','overlay':'NONE','overlay_evidence':'-'})
        v=dict(own='JH1HST',date='2025-11-29',time='09:00',band='7',mode='CW',call='JA1AAA',sent='25',exchange='25',cq_entity='JA',continent='AS',rst_sent='599',rst_received='599')
        s=score(r,[v,dict(v,call='DL1AAA',exchange='14',cq_entity='DL',continent='EU'),dict(v,call='MM1AAA/MM',exchange='15',cq_entity='',continent='EU')],ctx);self.assertEqual((s.points,s.multi1,s.total),(6,5,30),s.problems)
        ms=next(x for x in e['categories'] if x['id']=='MS_LOW');ct=dict(ctx,category=ms['id'],flags={f:True for f in e['required_flags']+ms['required_flags']});ct['flags'][HISTORY_FLAG]=True
        a=dict(v,tx='0');b=dict(v,band='14',call='JA1BBB',tx='1',time='09:01');bad=dict(b,call='JA1CCC',time='09:02');self.assertIsNotNone(score(r,[a,b],ct).total);self.assertIsNone(score(r,[a,b,bad],ct).total)
    def test_cqww_overlay_is_separate_and_qualifications(self):
        r=rule('cq-ww-cw');e=r['event'];c=next(c for c in e['categories'] if c['id']=='SO_LOW_40M');ctx=dict(category=c['id'],station_type='individual',power=10,flags={f:True for f in e['required_flags']+c['required_flags']},declarations={'own_cq_entity':'JA','own_continent':'AS','own_cq_zone':'25','overlay':'ROOKIE','overlay_evidence':'2022-11-30'})
        v=dict(own='JH1HST',date='2025-11-29',time='09:00',band='7',mode='CW',call='DL1AAA',sent='25',exchange='14',cq_entity='DL',continent='EU',rst_sent='599',rst_received='599')
        s=score(r,[v,dict(v,band='14',call='F1AAA',cq_entity='F')],ctx);self.assertEqual((s.total,s.overlay_score),(6,24),s.problems)
        self.assertIsNone(score(r,[v],dict(ctx,declarations=dict(ctx['declarations'],overlay_evidence='2022-11-29'))).total)
        ct=dict(ctx,declarations=dict(ctx['declarations'],overlay='CLASSIC',overlay_evidence='2025-11-29 00:00 / 2025-11-30 01:00'))
        rows=[v,dict(v,date='2025-11-30',time='09:30',call='F1AAA',cq_entity='F')];s=score(r,rows,ct);self.assertEqual((s.total,s.overlay_score),(18,6),s.problems)
    def test_wpx_all_categories_and_real_serial_export(self):
        from cabrillo_templates import loads as template_loads
        from contest_international import expected_headers
        from contest_timing import HISTORY_FLAG
        for ident in ['cq-wpx-cw','cq-wpx-ssb','cq-wpx-rtty']:
            r=rule(ident);e=r['event'];t=template_loads((ROOT/f'config/templates/cabrillo/{ident}_2026.txt').read_text(encoding='utf-8'));self.assertEqual(len(e['categories']),23 if ident.endswith('rtty') else 26)
            for c in e['categories']:
                with self.subTest(contest=ident,category=c['id']),tempfile.TemporaryDirectory() as tmp:
                    date=e['windows'][0]['start'][:10];mode=c['modes'][0];rst='59' if mode=='SSB' else '599';ctx=dict(category=c['id'],station_type='individual',power=5,flags={f:True for f in e['required_flags']+c['required_flags']},declarations={'own_cq_entity':'JA','own_continent':'AS','overlay':'NONE','overlay_evidence':'-'},operating_blocks=[dict(start=date+' 00:00',end=date+' 01:00')]);ctx['flags'][HISTORY_FLAG]=True
                    v=dict(own='JH1HST',date=date,time='09:00',band=c['bands'][0],mode=mode,call='W1AAA',sent='001',exchange='009',cq_entity='K',continent='NA',rst_sent=rst,rst_received=rst,tx='0')
                    expected=6 if v['band'] in ('1.9','3.5','7') else 3;s=score(r,[v],ctx);self.assertEqual(s.total,expected,s.problems)
                    repo=Repository(tmp);p=repo.path_for('JH1HST','',date);repo.open(p).append(QSO(date,'09:00',v['band'],mode,'W1AAA',rst,rst,'original','original','original',''));sel=select_logs(repo,[p],'JH1HST');d={key(sel.rows[0]):dict(sent='001',received='009',cq_entity='K',continent='NA',frequency={'1.9':'1810','3.5':'3510','7':'7010','14':'14050','21':'21050','28':'28050'}[v['band']],tx='0',status='確認済み')};raw=p.read_bytes()
                    info=dict(NAME='Test',ADDRESS='Test address',EMAIL='test@example.com',LOCATION='DX',OPERATORS='JA1AAA JA1BBB',**expected_headers(r,c,ctx));out=plan(sel,r,d,'Cabrillo',info,t,context=ctx).preview();line=next(x for x in out.splitlines() if x.startswith('QSO:')).split();self.assertEqual(line[7],'001');self.assertEqual(line[10],'009');self.assertEqual(raw,p.read_bytes())
    def test_wpx_global_prefix_and_serial_scopes(self):
        from contest_timing import HISTORY_FLAG
        from contest_event import wpx_prefix
        for call,expected in [('HG19ABC','HG19'),('LY1000A','LY1000'),('PA/N8BJQ','PA0'),('XEFTJW','XE0'),('JA1AAA/3','JA3'),('JA1AAA/P','JA1')]:self.assertEqual(wpx_prefix(call),expected)
        r=rule('cq-wpx-cw');e=r['event'];c=e['categories'][0];ctx=dict(category=c['id'],station_type='individual',power=5,flags={f:True for f in e['required_flags']+c['required_flags']},declarations={'own_cq_entity':'JA','own_continent':'AS','overlay':'NONE','overlay_evidence':'-'},operating_blocks=[dict(start='2026-05-30 00:00',end='2026-05-30 01:00')]);ctx['flags'][HISTORY_FLAG]=True
        v=dict(own='JH1HST',date='2026-05-30',time='09:00',band='7',mode='CW',call='DL1AAA',sent='001',exchange='009',cq_entity='DL',continent='EU',rst_sent='599',rst_received='599')
        rows=[v,dict(v,band='14',time='09:01',sent='002')];s=score(r,rows,ctx);self.assertEqual((s.points,s.multi1,s.total),(9,1,9),s.problems)
        self.assertIsNone(score(r,[v,dict(rows[1],sent='001')],ctx).total)
        mc=next(c for c in e['categories'] if c['id']=='M2_HIGH');ct=dict(ctx,category=mc['id'],flags={f:True for f in e['required_flags']+mc['required_flags']});ct['flags'][HISTORY_FLAG]=True
        self.assertIsNotNone(score(r,[dict(v,tx='0'),dict(rows[1],sent='001',tx='1')],ct).total)
        ctx['declarations'].update(overlay='ROOKIE',overlay_evidence='2023-05-30');self.assertIsNotNone(score(r,[v],ctx).total)
