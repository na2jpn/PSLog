"""Independent acceptance examples and all-category export regression."""
from copy import deepcopy
from pathlib import Path
import json,tempfile,unittest
from PySide6.QtWidgets import QApplication
from contest_rules import loads,score
from contest_export import plan,key
from contest import select_logs
from model import QSO
from storage import Repository
from contest_event_ui import EventDialog
ROOT=Path(__file__).parent
RULES={'ishikari':26,'yamagata_sakuranbo':25,'yamanashi':8,'all_ja8':36,'okhotsk':26,'all_miyagi':28,'kansai_vus':40,'kcj':13,'kcj-topband':6,'all_ja0_160m':2,'all_ja0_35':2,'all_ja0_7':2,'scalg-6m-cw':6,'all_mie_33':53,'oidemase_yamaguchi':18,'all_gifu':42,'tokai_qso':56,'tsugaru_kaikyo':12,'all_akita':48,'shiga':45,'all_gunma':104,'kanagawa_emergency':20}
TRACKED={k:[f'config/rules/{k}_{2025 if k=="all_ja0_160m" else 2026}.txt'] for k in RULES if k not in ('all_ja0_35','all_ja0_7','oidemase_yamaguchi')}
TRACKED['all_ja0_80m_40m']=['config/rules/all_ja0_35_2026.txt','config/rules/all_ja0_7_2026.txt']
for k in ('oidemase_yamaguchi_hf','oidemase_yamaguchi_vushf'):TRACKED[k]=['config/rules/oidemase_yamaguchi_2026.txt']

def rule(ident):return loads((ROOT/f'config/rules/{ident}_{2025 if ident=="all_ja0_160m" else 2026}.txt').read_text(encoding='utf-8'))
def category(r,code):return next(c for c in r['event']['categories'] if c['id']==code.replace('.','_'))
def setup(r,c):
    e=r['event'];x=c.get('regional',{});q=c.get('qualification',{})
    ctx=dict(category=c['id'],station_type=c.get('station_types',['individual'])[0],power=c.get('min_power_exclusive',0)+1 if 'min_power_exclusive' in c else min(c['max_power'] or 10,10),age=q.get('max_age',q.get('min_age',50)),licensedate=q.get('license_since','2026-01-01'),flags={f:True for f in e['required_flags']+c['required_flags']},entry_categories=[c['id']],declarations={k:'確認した具体的な根拠' for k in e['regional']['declarations']})
    d=ctx['declarations'];d.update(half_date=e['windows'][0]['start'][:10],cw_license='2025-07-21' if c['id']=='5' else '2020',beginner_birthdate='2000-01-01',senior_birthyear='1956',om_birthdate='1956-01-01',junior_birth='2008-01-01',entry_band_sets='',entry_basis='')
    bs=list(c['bands'][:max(1,c['min_bands'])])
    for g in x.get('required_band_groups',[]):bs+=g[:1]
    for g in x.get('band_minima',[]):bs+=g['bands'][:g['min']]
    if r['id']=='all_gunma' and c['id'][1:] in ('D','G','J'):bs=[c['bands'][0],'50']
    bs=list(dict.fromkeys(bs));d['scoring_bands']=', '.join(bs[:3])
    if x.get('selected_bands'):bs=c['bands'][:3];d['scoring_bands']=', '.join(bs)
    if r['id']=='kanagawa_emergency' and c['id'].endswith('A'):bs=['7','50']
    recv=e['exchange']['codes'][0]
    if r['id']=='all_ja8':recv='106D'
    sent=c['sent_codes'][0]
    if r['id']=='kanagawa_emergency':sent=e['regional']['postal_codes'][0] if c['id'].startswith('K') else '1319';recv=e['regional']['postal_codes'][0]
    if r['id']=='scalg-6m-cw':sent='25' if c['id']=='5' else '20';recv='00'
    mode='SSB' if c.get('required_mode_families') else c['modes'][0]
    rows=[]
    for i,b in enumerate(bs):
        w=next(w for w in e['windows'] if b in w['bands']);start=c.get('scoring_windows',[w])[0]['start']
        rows.append(dict(own='JH1HST',date=start[:10],time=start[11:],band=b,mode=mode,call='JA0AA'+chr(65+i),sent=sent,exchange=recv,operator_name='JA1AAA',rst_sent='599' if mode=='CW' else '59',rst_received='599' if mode=='CW' else '59'))
    if r['id']=='all_gunma' and c['id'][1] in ('C','J','K','L') and (len(c['id'])==2 or c['id'][1]=='C'):rows.append(dict(rows[0],mode='SSB',call='JA0ZZZ'))
    if c.get('participation'):
        from contest_participation import HISTORY
        ctx['flags'][HISTORY]=True
        rows=[dict(rows[0],call='JA0A'+chr(65+i)+'A',operator_name='JA1AAA' if i<8 else 'JA1BBB') for i in range(10)]
        ctx['qso_operators']=[dict(name='JA1AAA',age=18,qsos=8,role=''),dict(name='JA1BBB',age=50,qsos=2,role='')]
    return ctx,rows

class Remaining28Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def fixture(self,r,c,rows,ctx):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);repo=Repository(tmp.name);p=repo.path_for('JH1HST','',rows[0]['date'])
        for v in rows:repo.open(p).append(QSO(v['date'],v['time'],v['band'],v['mode'],v['call'],'599' if v['mode']=='CW' else '59','599' if v['mode']=='CW' else '59','元所在地','元自局所在地','元備考',''))
        sel=select_logs(repo,[p],'JH1HST');draft={key(rec):dict(sent=v['sent'],received=v['exchange'],operator_name=v['operator_name'],status='確認済み',checklog=v.get('checklog',False)) for rec,v in zip(sel.rows,rows)}
        names='JA1AAA JA1BBB' if c.get('participation') else 'JA1AAA 試験 一アマ, JA1BBB 試験 二アマ'
        info=dict(contest=r['event']['submission']['contest'],category=c.get('submission_code',c['id']),categoryname=c['name'],name='試験',address='試験住所',power=str(ctx['power']),date='2026-09-15',signature='試験',oath=True,email='test@example.com',tel='0000000000',opplace='試験運用地',opcall='JH1HST' if r['id']=='scalg-6m-cw' and ctx['station_type']=='club' else '',multiop=c.get('operator')=='MO',multioplist=names,comments='元意見',age=str(ctx['age']))
        return p,sel,draft,info
    def test_all_categories_score_export_and_original_bytes(self):
        for ident in RULES:
            r=rule(ident);self.assertEqual(len(r['event']['categories']),RULES[ident])
            for c in r['event']['categories']:
                with self.subTest(contest=ident,category=c['id']):
                    ctx,rows=setup(r,c);before=deepcopy(rows);s=score(r,rows,ctx);self.assertIsNotNone(s.total,s.problems);self.assertGreater(s.points,0);self.assertEqual(rows,before)
                    p,sel,d,info=self.fixture(r,c,rows,ctx);original=p.read_bytes()
                    for fmt in r['event']['submission']['formats']:
                        out=plan(sel,r,d,fmt,info,context=ctx).preview();self.assertIn('<CATEGORYCODE>'+info['category']+'</CATEGORYCODE>',out);self.assertIn('<TOTALSCORE>'+str(s.total)+'</TOTALSCORE>',out)
                    self.assertEqual(original,p.read_bytes())
    def test_age_exchange_points_and_shared_multiplier(self):
        r=rule('all_ja8');c=category(r,'GX04');ctx,rows=setup(r,c);v=rows[0]
        samples=[dict(v,call='JA8AA'+chr(65+i),exchange='106'+t) for i,t in enumerate('AJMX')];s=score(r,samples,ctx);self.assertEqual((s.points,s.multi1,s.total),(15,1,15));self.assertIsNone(score(r,[dict(v,exchange='106Z')],ctx).total)
        r=rule('all_mie_33');c=category(r,'XD2-7');ctx,rows=setup(r,c);v=rows[0];samples=[dict(v,call='JA3AA'+chr(65+i),exchange=x) for i,x in enumerate(['54ME','54MEJ','00MEJ','20'])];s=score(r,samples,ctx);self.assertEqual((s.points,s.multi1,s.total),(5,2,10));self.assertEqual(samples[-2]['exchange'],'00MEJ')
    def test_kcj_domestic_foreign_zero_multiplier_and_zone_alias(self):
        for ident in ('kcj','kcj-topband'):
            r=rule(ident);c=category(r,'CP');ctx,rows=setup(r,c);v=rows[0]
            s=score(r,[dict(v,exchange=x,call='JA1AA'+chr(65+i)) for i,x in enumerate(['ST','TK','25','25'])],ctx);self.assertEqual((s.points,s.multi1,s.total),(6,3,18))
            s=score(r,[dict(v,exchange=x,call='JA1AA'+chr(65+i)) for i,x in enumerate(['1','01','OG','MT'])],ctx);self.assertEqual((s.points,s.multi1),(6,3))
            c=category(r,'DX');ctx,rows=setup(r,c);v=rows[0];s=score(r,[dict(v,exchange='25')],ctx);self.assertEqual((s.points,s.multi1,s.total),(1,0,0))
            self.assertIsNone(score(r,[dict(v,exchange='41')],ctx).total)
    def test_ja0_or_call_area_and_serial_preservation(self):
        for ident in ('all_ja0_160m','all_ja0_35','all_ja0_7'):
            r=rule(ident);c=r['event']['categories'][0];ctx,rows=setup(r,c);v=rows[0]
            s=score(r,[dict(v,call='JA0IXW',sent='009',exchange='017'),dict(v,call='JA0ABW',sent='010',exchange='123'),dict(v,call='JR1XXX',sent='011',exchange='005')],ctx);self.assertEqual((s.points,s.multi1,s.total),(7,1,7))
            s=score(r,[dict(v,own='JG0SXC/1',call='JA5FNX/0')],ctx);self.assertEqual((s.points,s.multi1,s.total),(3,1,3));self.assertEqual(s.rows[0]['multiplier_values'],['JA5'])
            self.assertIsNone(score(r,[dict(v,sent='9')],ctx).total)
            p,sel,d,info=self.fixture(r,c,[dict(v,sent='009',exchange='017')],ctx);out=plan(sel,r,d,'JARL R1.0',info,context=ctx).preview();line=next(x for x in out.splitlines() if x.startswith(v['date']+' '));self.assertEqual(line.split()[2:5],[v['call'],'599009','599017'])
    def test_yamagata_band_groups_and_yamanashi_quota(self):
        r=rule('yamagata_sakuranbo');c=category(r,'XALL');ctx,rows=setup(r,c);self.assertIsNotNone(score(r,rows,ctx).total);self.assertIsNone(score(r,[rows[0],rows[-1]],ctx).total)
        r=rule('yamanashi');c=category(r,'Y-1');ctx,rows=setup(r,c);self.assertIsNone(score(r,[dict(rows[0],exchange='13')],ctx).total);self.assertEqual(score(r,rows,ctx).total,3)
        c=category(r,'O-1');ctx,rows=setup(r,c);v=rows[0];s=score(r,[v,dict(v,mode='SSB'),dict(v,mode='FM')],ctx);self.assertEqual((s.points,s.multi1),(6,1))
    def test_shiga_three_bands_and_non_fd_factor(self):
        r=rule('shiga');c=category(r,'OFM');ctx,rows=setup(r,c);v=rows[0]
        samples=[dict(v,exchange='13',sent='10'),dict(v,exchange='2301',sent='10',call='JA3BBB',band='50'),dict(v,exchange='2302',sent='10',call='JA3CCC',band='144')];s=score(r,samples,ctx);self.assertEqual((s.points,s.multi1,s.multi2,s.total),(11,3,2,66))
        self.assertEqual(score(r,samples[:1],ctx).total,0)
        self.assertEqual(score(r,[dict(samples[1],call='JL3ZKV/3')],ctx).points,6)
        p,sel,d,info=self.fixture(r,c,samples,ctx);out=plan(sel,r,d,'JARL R1.0',info,context=ctx).preview();self.assertIn('滋賀交信バンド係数2',out);self.assertNotIn('<FDCOEFF>',out)
        c=category(r,'QRP');ctx,rows=setup(r,c);self.assertIsNotNone(score(r,rows,ctx).total);self.assertIsNone(score(r,rows[:2],ctx).total)
        rows.append(dict(rows[0],band='50',call='JA3ZZZ'));self.assertEqual(score(r,rows,ctx).points,15)
    def test_sprint_time_boundaries(self):
        r=rule('shiga');c=category(r,'CMSA');ctx,rows=setup(r,c);self.assertIsNotNone(score(r,rows,ctx).total);self.assertEqual(score(r,[dict(v,time='12:00') for v in rows],ctx).points,0)
        self.assertEqual(score(r,[dict(v,time='13:00') for v in rows],ctx).points,0)
    def test_postal_band_windows_and_all_category(self):
        r=rule('kanagawa_emergency');c=category(r,'XA');ctx,rows=setup(r,c);v=rows[0]
        a=[dict(v,band='7',time='19:59'),dict(v,band='50',time='20:00',call='JA1BBB')];self.assertEqual(score(r,a,ctx).total,4)
        self.assertIsNone(score(r,[dict(v,band='3.5'),dict(v,band='7',call='JA1BBB')],ctx).total)
        self.assertEqual(score(r,[dict(v,band='7',time='20:00')],ctx).points,0)
        self.assertEqual(score(r,[dict(v,band='7',mode='FM')],ctx).points,0)
        self.assertIsNone(score(r,[dict(v,sent='13')],ctx).total)
        c=category(r,'X7');ctx,rows=setup(r,c);v=rows[0];ctx['declarations']['postal_confirmation']='';self.assertIsNone(score(r,[dict(v,exchange='9999999')],ctx).total);ctx['declarations']['postal_confirmation']='県内の運用地を原記録と照合';self.assertEqual(score(r,[dict(v,exchange='9999999')],ctx).total,1)
    def test_miyagi_high_band_end_and_entry_pair(self):
        r=rule('all_miyagi');c=category(r,'X1200UP');ctx,rows=setup(r,c);v=rows[0];s=score(r,[dict(v,date='2026-01-18',time='12:59',band=b) for b in ('1200','2400')],ctx);self.assertEqual((s.points,s.multi1,s.total),(6,2,12));self.assertEqual(score(r,[dict(v,date='2026-01-18',time='13:00')],ctx).points,0)
        ctx['entry_categories']=['X1200UP','X7'];self.assertIsNotNone(score(r,rows,ctx).total);ctx['entry_categories']=['X1200UP','XFA'];self.assertIsNone(score(r,rows,ctx).total)
    def test_kansai_real_band_normalization_and_mixed_phone(self):
        r=rule('kansai_vus');c=category(r,'C10G');ctx,rows=setup(r,c);v=rows[0];s=score(r,[dict(v,band=b) for b in ['10.1G','10.4G','24G']],ctx);self.assertEqual((s.points,s.multi1,s.total),(2,2,4))
        c=category(r,'CM');ctx,rows=setup(r,c);v=rows[0];self.assertIsNone(score(r,[dict(v,band=b) for b in ['10G','24000']],ctx).total)
        c=category(r,'F28');ctx,rows=setup(r,c);self.assertIsNone(score(r,[dict(rows[0],mode='CW')],ctx).total)
        c=category(r,'CC');ctx,rows=setup(r,c);self.assertEqual(score(r,rows,ctx).total,1)
    def test_gunma_reclassification_and_first_duplicate(self):
        r=rule('all_gunma');c=category(r,'2C430');ctx,rows=setup(r,c);v=rows[0];self.assertIsNone(score(r,[v],ctx).total);self.assertTrue(any('2A430' in x for x in score(r,[v],ctx).problems))
        s=score(r,[dict(v,mode='SSB'),v],ctx);self.assertEqual(s.points,1);self.assertIsNotNone(s.total,s.problems)
        c=category(r,'2J');ctx,rows=setup(r,c);s=score(r,[v,dict(v,mode='SSB',call='JA1BBB')],ctx);self.assertTrue(any('2L' in x for x in s.problems))
        c=category(r,'2Q1A');ctx,rows=setup(r,c);self.assertEqual(score(r,[dict(rows[0],band='1200')],ctx).points,0)
    def test_tsugaru_three_geographies_and_movement(self):
        r=rule('tsugaru_kaikyo');c=category(r,'ASM');ctx,rows=setup(r,c);v=rows[0]
        s=score(r,[dict(v,sent='0201',exchange=x,call='JA8AA'+chr(65+i)) for i,x in enumerate(['0104','0202','13'])],ctx);self.assertEqual((s.points,s.multi1,s.total),(6,3,18))
        self.assertIsNone(score(r,[dict(v,sent='0201'),dict(v,sent='0104',call='JA1BBB')],ctx).total)
        c=category(r,'KSM');ctx,rows=setup(r,c);self.assertEqual(score(r,[dict(rows[0],exchange='0104')],ctx).points,1)
    def test_yamaguchi_one_runtime_two_dates_and_exclusive_entry(self):
        r=rule('oidemase_yamaguchi');c=category(r,'GVU');ctx,rows=setup(r,c);v=rows[0]
        s=score(r,[dict(v,exchange='33006A',mode=m) for m in ['CW','SSB','FM']],ctx);self.assertEqual((s.points,s.multi1,s.total),(4,1,4))
        ctx['entry_categories']=['GVU','GS','GHF','GHC'];self.assertIsNotNone(score(r,rows,ctx).total);ctx['entry_categories']=['GVU','GO'];self.assertIsNone(score(r,rows,ctx).total)
        c=category(r,'GO');ctx,rows=setup(r,c);v=rows[0];self.assertEqual(score(r,[dict(v,band='7',date='2026-05-17')],ctx).points,0)
    def test_sc_optional_multiplier_not_qso_validity(self):
        r=rule('scalg-6m-cw');c=category(r,'1');ctx,rows=setup(r,c);v=rows[0];s=score(r,[dict(v,call='JA1AA'+chr(65+i),exchange=x) for i,x in enumerate(['51','99','00','26','27','50'])],ctx);self.assertEqual((s.points,s.multi1,s.total),(6,4,24));self.assertEqual(score(r,[dict(v,exchange='27')],ctx).total,0)
    def test_half_operation_cannot_hide_second_day(self):
        r=rule('all_gifu');c=category(r,'X-SHH');ctx,rows=setup(r,c);v=rows[0];self.assertIsNotNone(score(r,rows,ctx).total);rows.append(dict(v,date='2026-06-14',time='07:00',checklog=True));self.assertIsNone(score(r,rows,ctx).total)
    def test_youth_assignment_counts_not_number_of_operators(self):
        for ident,code in [('all_gifu','X-MJ'),('tokai_qso','X-MAJ')]:
            r=rule(ident);c=category(r,code);ctx,rows=setup(r,c);self.assertIsNotNone(score(r,rows,ctx).total)
            rows[7]['operator_name']='JA1BBB';ctx['qso_operators'][0]['qsos']=7;ctx['qso_operators'][1]['qsos']=3;self.assertEqual(score(r,rows,ctx).total is None,ident!='all_gifu')
            ctx['qso_operators'][0]['qsos']=8;ctx['qso_operators'][1]['qsos']=2;self.assertEqual(score(r,rows,ctx).total is None,ident!='all_gifu')
    def test_akita_exceptions_and_up_real_bands(self):
        r=rule('all_akita');c=category(r,'GS1200C');ctx,rows=setup(r,c);v=rows[0];s=score(r,[dict(v,band=b) for b in ['1200','2400']],ctx);self.assertEqual(s.total,4)
        c=category(r,'GSQC');ctx,rows=setup(r,c);self.assertIsNotNone(score(r,rows,ctx).total)
        c=category(r,'GS7C');ctx,rows=setup(r,c);ctx['entry_categories']=['GS7C','GS7P'];self.assertIsNone(score(r,rows,ctx).total)
        c=category(r,'GSHC');ctx,rows=setup(r,c);ctx['entry_categories']=['GSHC','GSVC'];self.assertIsNotNone(score(r,rows,ctx).total)
    def test_draft_gui_and_declaration_roundtrip(self):
        r=rule('shiga');c=category(r,'QRP');ctx,rows=setup(r,c);dialog=EventDialog(r['event'],ctx);dialog.declarations['scoring_bands'].setText('7, 50, 144');dialog.apply();self.assertEqual(dialog.context['declarations']['scoring_bands'],'7, 50, 144');dialog.close()
        from contest_submit_ui import DetailsDialog
        r=rule('tokai_qso');c=category(r,'X-MAJ');ctx,rows=setup(r,c);p,sel,d,info=self.fixture(r,c,rows,ctx);dialog=DetailsDialog(sel,d,event=r['event']);self.assertEqual(dialog.operator_columns,1);dialog.table.item(0,dialog.operator_start).setText('JA1ZZZ');self.assertEqual(dialog.draft[key(sel.rows[0])]['operator_name'],'JA1ZZZ');dialog.close()
    def test_pack_roundtrip_and_tracked_count(self):
        from contest_rules import RuleStore
        import rule_pack
        self.assertEqual(len(TRACKED),22)
        with tempfile.TemporaryDirectory() as tmp:
            store=RuleStore(tmp);path=ROOT/'distribution/rules/remaining28_r1.zip';p=rule_pack.preview(store,path);self.assertEqual(len(p.items),22);self.assertEqual(rule_pack.install(store,p),22);self.assertEqual(rule_pack.install(store,rule_pack.preview(store,path)),0)

    def test_qualification_dates_and_checklog_prefixes(self):
        r=rule('scalg-6m-cw');c=category(r,'5');ctx,rows=setup(r,c)
        ctx['declarations']['cw_license']='2025-07-20';self.assertIsNone(score(r,rows,ctx).total)
        ctx['declarations']['cw_license']='2025-07-21';self.assertIsNotNone(score(r,rows,ctx).total)
        self.assertIsNone(score(r,[dict(rows[0],sent='24')],ctx).total)
        c=category(r,'6');ctx,rows=setup(r,c);ctx['declarations']['senior_birthyear']='2000';self.assertIsNone(score(r,rows,ctx).total)
        r=rule('oidemase_yamaguchi');c=category(r,'GO');ctx,rows=setup(r,c);ctx['declarations']['om_birthdate']='1956-06-01';self.assertIsNone(score(r,rows,ctx).total)
        r=rule('all_akita');c=category(r,'GSJC');ctx,rows=setup(r,c);ctx['declarations']['junior_birth']='2000-01-01';self.assertIsNone(score(r,rows,ctx).total)
        for ident in ('kcj','kcj-topband'):
            r=rule(ident);c=category(r,'CP');ctx,rows=setup(r,c);self.assertIsNone(score(r,[dict(rows[0],own='8N1TEST')],ctx).total)
            ctx['submission_mode']='checklog';self.assertEqual(score(r,[dict(rows[0],own='8N1TEST')],ctx).total,0)
    def test_source_urls_years_and_schema_rejection(self):
        from contest_rules import dumps
        for ident in RULES:
            r=rule(ident)
            if ident!='all_akita':self.assertTrue(r['url'].startswith('http'),ident)
        r=rule('all_ja0_160m');self.assertEqual(r['year'],2025);self.assertNotIn('2026参考版',r['event']['submission']['instructions'])
        for value in ('unknown',[],{}):
            r=rule('shiga');r['event']['regional']['profile']=value
            with self.assertRaises(ValueError):dumps(r)
        r=rule('yamagata_sakuranbo');r['event']['categories'][0]['regional']['band_minima']='bad'
        with self.assertRaises(ValueError):dumps(r)
    def test_unknown_postal_and_ambiguous_county_are_explicit(self):
        r=rule('ishikari');c=category(r,'C7');ctx,rows=setup(r,c);ctx['declarations']['abuta_locality']='';self.assertIsNone(score(r,[dict(rows[0],exchange='01006')],ctx).total)
        ctx['declarations']['abuta_locality']='JA8ABC、倶知安町、後志所属を実交換の運用地で確認';self.assertIsNotNone(score(r,[dict(rows[0],exchange='01006')],ctx).total)
        r=rule('kanagawa_emergency');c=category(r,'X7');ctx,rows=setup(r,c);ctx['declarations']['postal_confirmation']='9999999、県内地名と実運用記録を確認';rows=[dict(rows[0],exchange='9999999')];p,sel,d,info=self.fixture(r,c,rows,ctx);out=plan(sel,r,d,'JARL R1.0',info,context=ctx).preview();self.assertIn('9999999、県内地名',out)
    def test_unambiguous_entry_overlap_and_zero_point_rows_are_retained(self):
        r=rule('all_akita');c=category(r,'ASMC');ctx,rows=setup(r,c);ctx['entry_categories']=['ASMC','ASHC'];self.assertIsNotNone(score(r,rows,ctx).total)
        ctx['declarations']['entry_band_sets']='ASMC=7,50;ASHC=7,14';self.assertIsNone(score(r,rows,ctx).total)
        r=rule('kcj');c=category(r,'C7');ctx,rows=setup(r,c);rows+=[dict(rows[0],time='21:01'),dict(rows[0],time='21:02',band='14')];p,sel,d,info=self.fixture(r,c,rows,ctx);out=plan(sel,r,d,'JARL R1.0',info,context=ctx).preview();self.assertEqual(len([x for x in out.splitlines() if x.startswith('2026-08-15 ')]),3)
        r=rule('kanagawa_emergency');c=category(r,'X7');ctx,rows=setup(r,c);rows.append(dict(rows[0],band='50',time='20:00'));p,sel,d,info=self.fixture(r,c,rows,ctx);out=plan(sel,r,d,'JARL R1.0',info,context=ctx).preview();self.assertEqual(len([x for x in out.splitlines() if x.startswith('2026-04-04 ')]),2)

    def test_missing_kcj_exchange_kept_and_scalg_checklog_requirements(self):
        r=rule('kcj');c=category(r,'C7');ctx,rows=setup(r,c);rows.append(dict(rows[0],time='21:03',call='JA1ZZZ',exchange='?'));s=score(r,rows,ctx);self.assertEqual(s.points,1);self.assertIsNotNone(s.total,s.problems)
        p,sel,d,info=self.fixture(r,c,rows,ctx);out=plan(sel,r,d,'JARL R1.0',info,context=ctx).preview();self.assertIn('599?',out)
        r=rule('scalg-6m-cw');c=category(r,'1');ctx,rows=setup(r,c);p,sel,d,info=self.fixture(r,c,rows,ctx);ctx['submission_mode']='checklog';info['category']='8'
        out=plan(sel,r,d,'JARL R1.0',info,context=ctx).preview();self.assertIn('1 CW従免初取得年',out)
        ctx['declarations']['key_model']=''
        with self.assertRaises(ValueError):plan(sel,r,d,'JARL R1.0',info,context=ctx)
