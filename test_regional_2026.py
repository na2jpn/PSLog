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
IDS=['all_kushiro','all_aomori','ja9_hf_phone','ja9_hf_cw','ja9_vu','all_ja5','kamikawa_souya','oshima_hiyama','all_kumamoto','iwate_winter','nagasaki','wakayama','all_ja4','all_tohoku','niigata_low_band','niigata_branch','tochigi','all_kyushu','kagoshima','all_kanagawa','ja0_vhf','oita']

def rule(ident):return loads((ROOT/f'config/rules/{ident}_2026.txt').read_text(encoding='utf-8'))

def context(r,c):
    return dict(category=c['id'],station_type=c.get('station_types',['individual'])[0],power=min(c['max_power'] or 10,10),
        age=c.get('qualification',{}).get('max_age',70),operators=[dict(name='JA1AAA',age=18),dict(name='JA1BBB',age=17)],power_by_band={b:min(cap,10) for b,cap in c.get('power_by_band',{}).items()},licensedate=c.get('qualification',{}).get('license_since','2026-01-01'),operation_kind='stationary',
        declarations={k:('' if k=='junior_birthdate' else '確認した具体的な申告') for k in r['event'].get('regional',{}).get('declarations',{})},entry_categories=[c['id']],
        flags={f:True for f in r['event']['required_flags']+c['required_flags']})

def sample(r,c):
    eligible=c.get('eligible',{}).get('value','').split(',');recv=eligible[0] or r['event']['exchange']['codes'][0]
    bs=list(dict.fromkeys(c['bands'][:max(c['min_bands'],1)]+[g[0] for g in c.get('regional',{}).get('required_band_groups',[])]))
    rows=[]
    for i,b in enumerate(bs):
        w=next(w for w in r['event']['windows'] if not w['bands'] or b in w['bands']);start=w['start']
        if c.get('scoring_windows'):start=c['scoring_windows'][0]['start']
        mode='SSB' if c.get('required_mode_families')==['phone'] else c['modes'][0]
        rows.append(dict(date=start[:10],time=start[11:],band=b,mode=mode,call='JA1AA'+chr(65+i),sent=c['sent_codes'][0],exchange=recv,operator_name='JA1AAA',rst_sent='599',rst_received='599'))
    if c.get('regional',{}).get('min_operators',0)>1:
        rows.append(dict(rows[0],call='JA1ZZZ',operator_name='JA1BBB'))
    for quota in c.get('regional',{}).get('quotas',[]):
        for i in range(quota['min_calls']):rows.append(dict(rows[0],call='JA8ZZ'+chr(65+i),exchange=quota['codes'][i%len(quota['codes'])]))
    return rows

class RegionalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def test_every_category_score_export_and_source_unchanged(self):
        for ident in IDS:
            r=rule(ident)
            for c in r['event']['categories']:
                with self.subTest(contest=ident,category=c['id']):
                    ctx=context(r,c);rows=sample(r,c);original=deepcopy(rows)
                    s=score(r,rows,ctx);self.assertIsNotNone(s.total,s.problems);self.assertGreater(s.points,0);self.assertEqual(rows,original)
                    with tempfile.TemporaryDirectory() as tmp:
                        repo=Repository(tmp);p=repo.path_for('JH1HST','',rows[0]['date'])
                        for v in rows:
                            rst='599' if v['mode']=='CW' else '59'
                            repo.open(p).append(QSO(v['date'],v['time'],v['band'],v['mode'],v['call'],rst,rst,'元所在地','元自局所在地','元備考',''))
                        before=p.read_bytes();sel=select_logs(repo,[p],'JH1HST');d={key(rec):dict(sent=v['sent'],received=v['exchange'],operator_name=v['operator_name'],status='確認済み') for rec,v in zip(sel.rows,rows)}
                        info=dict(contest=r['event']['submission']['contest'],category=c.get('submission_code',c['id']),categoryname=c['name'],name='試験',address='試験',power=str(ctx['power']),date='2026-09-15',signature='試験',oath=True,email='test@example.com',opplace='東京都試験',multiop=c.get('operator')=='MO',multioplist='JA1AAA 試験 一アマ, JA1BBB 試験 二アマ',comments='確認済み',age=str(ctx['age']))
                        if c.get('qualification',{}).get('operators_max_age'):
                            from contest_qualification import operator_text
                            info['multioplist']=operator_text(ctx['operators'])
                        for fmt in r['event']['submission']['formats']:
                            result=plan(sel,r,d,fmt,info,context=ctx);text=result.preview()
                            self.assertIn('<CATEGORYCODE>'+info['category']+'</CATEGORYCODE>',text);self.assertIn('<TOTALSCORE>',text)
                        self.assertEqual(p.read_bytes(),before)
    def test_kushiro_band_groups_and_cross_mode_duplicate(self):
        r=rule('all_kushiro');c=next(c for c in r['event']['categories'] if c['id']=='XHV');ctx=context(r,c);rows=sample(r,c)
        self.assertIsNotNone(score(r,rows,ctx).total)
        bad=[dict(rows[0]),dict(rows[0],band='14',call='JA1BBB')];self.assertIsNone(score(r,bad,ctx).total)
        c=next(c for c in r['event']['categories'] if c['id']=='XHF');ctx=context(r,c);row=sample(r,c)[0]
        self.assertEqual(score(r,[row,dict(row,mode='SSB')],ctx).points,1)
    def test_aomori_village_and_phone_requirement(self):
        r=rule('all_aomori');c=next(c for c in r['event']['categories'] if c['id']=='X7');ctx=context(r,c);v=sample(r,c)[0]
        rows=[dict(v,exchange='0217',mode='CW'),dict(v,exchange='0217',mode='SSB'),dict(v,exchange='0217',mode='FM')]
        s=score(r,rows,ctx);self.assertEqual((s.points,s.multi1,s.total),(6,1,6))
        self.assertIsNone(score(r,rows[:1],ctx).total)
        self.assertIsNone(score(r,[dict(v,exchange='0241')],ctx).total)
    def test_ja9_geography_multiband_and_actual_operators(self):
        for ident in ['ja9_hf_phone','ja9_hf_cw','ja9_vu']:
            r=rule(ident);c=next(c for c in r['event']['categories'] if c['id']=='SM');ctx=context(r,c);rows=sample(r,c)
            self.assertIsNotNone(score(r,rows,ctx).total);self.assertIsNone(score(r,rows[:1],ctx).total)
            c=next(c for c in r['event']['categories'] if c['id']=='MM');ctx=context(r,c);rows=sample(r,c)
            self.assertIsNotNone(score(r,rows,ctx).total)
            self.assertIsNone(score(r,[dict(v,operator_name='JA1AAA') for v in rows],ctx).total)
            c=r['event']['categories'][0];ctx=context(r,c);v=sample(r,c)[0]
            s=score(r,[dict(v,sent='13',exchange='10')],ctx);self.assertEqual(s.points,0)
    def test_ja9_highest_eligible_qso_not_ft8(self):
        r=rule('ja9_vu');c=next(c for c in r['event']['categories'] if c['id']=='S144');ctx=context(r,c);v=sample(r,c)[0]
        rows=[dict(v,mode=m) for m in ['FM','CW','RTTY','FT8']]
        s=score(r,rows,ctx);self.assertEqual((s.points,s.multi1,s.total),(5,1,5));self.assertEqual([x['points'] for x in s.rows],[0,0,5,0])
        s=score(r,[rows[0],rows[1],dict(rows[2],date='2026-08-10')],ctx);self.assertEqual(s.points,3)
    def test_dialog_declarations_roundtrip(self):
        r=rule('all_aomori');c=next(c for c in r['event']['categories'] if c['id']=='XYL');ctx=context(r,c)
        d=EventDialog(r['event'],ctx);d.declarations['yl'].setText('本人が女性であることを申告');d.apply();self.assertEqual(d.context['declarations']['yl'],'本人が女性であることを申告');d.close()
    def test_shikoku_entrant_changes_multiplier_only(self):
        r=rule('all_ja5')
        for code,want in [('C7I',1),('C7G',2)]:
            c=next(c for c in r['event']['categories'] if c['id']==code);ctx=context(r,c);v=sample(r,c)[0]
            rows=[dict(v,exchange='3601'),dict(v,call='JA5BBB',exchange='3602')];s=score(r,rows,ctx)
            self.assertEqual((s.points,s.multi1,s.total),(2,want,2*want));self.assertEqual(rows[0]['exchange'],'3601')
        c=next(c for c in r['event']['categories'] if c['id']=='C7I');ctx=context(r,c);v=sample(r,c)[0]
        self.assertIn('106',score(r,[dict(v,exchange='106')],ctx).rows[0]['multiplier_values'])
    def test_kamikawa_quota_uses_distinct_base_calls_in_category(self):
        r=rule('kamikawa_souya');c=next(c for c in r['event']['categories'] if c['id']=='XHF');ctx=context(r,c);v=sample(r,c)[0]
        rows=[dict(v,call='JA8AAA',exchange='204'),dict(v,call='JA8AAA/8',band='14',exchange='214'),dict(v,call='JA1BBB',exchange='10')]
        self.assertIsNone(score(r,rows,ctx).total)
        rows[1]['call']='JA8CCC';s=score(r,rows,ctx);self.assertEqual((s.points,s.multi1,s.total),(5,3,15))
        rows[1]['band']='50';self.assertIsNone(score(r,rows,ctx).total)
        self.assertIsNone(score(r,[dict(v,exchange='101')],ctx).total)
    def test_oshima_literal_towns_movement_and_callsign_identity(self):
        r=rule('oshima_hiyama');c=next(c for c in r['event']['categories'] if c['id']=='GHF');ctx=context(r,c);v=sample(r,c)[0]
        rows=[dict(v,call='JA8AAA/8',exchange='01025B',sent='13',mode='DV'),dict(v,call='JA8AAA',exchange='01025D',sent='10',mode='CW')]
        s=score(r,rows,ctx);self.assertEqual((s.points,s.multi1,s.total),(1,1,1));self.assertIn('01025B',s.rows[0]['multiplier_values'])
        rows[1]['call']='JA8BBB';s=score(r,rows,ctx);self.assertEqual(s.multi1,2)
        rows[1]['sent']='0104';self.assertIsNone(score(r,rows,ctx).total)
    def test_iwate_points_and_zero_multiplier_validity(self):
        r=rule('iwate_winter')
        for code,recv,points,multi in [('7KN','0301',1,1),('7KN','13',2,1),('7TK','0301',2,1),('7TK','10',1,0)]:
            c=next(c for c in r['event']['categories'] if c['id']==code);ctx=context(r,c);v=sample(r,c)[0];s=score(r,[dict(v,exchange=recv)],ctx)
            self.assertEqual((s.points,s.multi1,s.total),(points,multi,points*multi))
        ctx['power']=100;self.assertIsNotNone(score(r,[dict(v,exchange='0301')],ctx).total)
        ctx['operation_kind']='portable';self.assertIsNone(score(r,[dict(v,exchange='0301')],ctx).total)
    def test_wakayama_entry_set_uses_category_bands(self):
        r=rule('wakayama');c=next(c for c in r['event']['categories'] if c['id']=='GC7');ctx=context(r,c);rows=sample(r,c)
        ctx['entry_categories']=['GC7','GC14'];self.assertIsNone(score(r,rows,ctx).total)
        ctx['entry_categories']=['GC7','GX430'];self.assertIsNotNone(score(r,rows,ctx).total)
    def test_local_power_caps_and_mode_matrix(self):
        for ident,code,limit in [('all_kumamoto','GFM',100),('all_kumamoto','GCMQ',5),('nagasaki','AKHFPH',10),('wakayama','GP7',10),('kamikawa_souya','YHF',50)]:
            r=rule(ident);c=next(c for c in r['event']['categories'] if c['id']==code);ctx=context(r,c);rows=sample(r,c);ctx['power']=limit
            self.assertIsNotNone(score(r,rows,ctx).total);ctx['power']=limit+.01;self.assertIsNone(score(r,rows,ctx).total)
        r=rule('nagasaki');self.assertEqual(len(r['event']['categories']),16);self.assertFalse(any('UVCW' in c['id'] for c in r['event']['categories']))
    def test_kanagawa_stage_numbers_power_and_junior_boundaries(self):
        r=rule('all_kanagawa');c=next(c for c in r['event']['categories'] if c['id']=='XCSA');ctx=context(r,c)
        v=sample(r,c)[0];rows=[dict(v,date='2026-06-06',time='15:00',band='14',sent='13'),dict(v,time='21:00',band='7',sent='10')]
        self.assertIsNotNone(score(r,rows,ctx).total)
        rows.append(dict(rows[1],time='21:01',call='JA1ZZZ',sent='12'));self.assertIsNone(score(r,rows,ctx).total)
        rows=rows[:2];rows[0]['time']='18:00';self.assertIsNone(score(r,rows,ctx).total)
        c=next(c for c in r['event']['categories'] if c['id']=='XPSU');ctx=context(r,c);rows=sample(r,c)
        self.assertIsNotNone(score(r,rows,ctx).total);ctx['power_by_band']['1200']=1.01;self.assertIsNone(score(r,rows,ctx).total)
        c=next(c for c in r['event']['categories'] if c['id']=='XCSJA');ctx=context(r,c);self.assertIsNotNone(score(r,sample(r,c),ctx).total);ctx['age']=19;self.assertIsNone(score(r,sample(r,c),ctx).total)
        c=next(c for c in r['event']['categories'] if c['id']=='XPSNA');ctx=context(r,c);ctx['licensedate']='2023-06-05';self.assertIsNone(score(r,sample(r,c),ctx).total)
    def test_kagoshima_kj_suffix_and_mo_cap(self):
        r=rule('kagoshima');c=next(c for c in r['event']['categories'] if c['id']=='G7');ctx=context(r,c);v=sample(r,c)[0]
        rows=[dict(v,exchange='4619'),dict(v,call='JA1BBB',exchange='4619KJ')];s=score(r,rows,ctx);self.assertEqual((s.points,s.multi1,s.total),(2,1,2));self.assertEqual(rows[1]['exchange'],'4619KJ')
        self.assertIsNone(score(r,[dict(v,exchange='4612KJ')],ctx).total)
        c=next(c for c in r['event']['categories'] if c['id']=='GMMC');ctx=context(r,c);ctx['power']=100.01;self.assertIsNone(score(r,sample(r,c),ctx).total)
        c=next(c for c in r['event']['categories'] if c['id']=='KJ');ctx=context(r,c);v=sample(r,c)[0];self.assertEqual(score(r,[dict(v,exchange='13')],ctx).total,1)
        ctx['declarations']['kj_history']='';self.assertIsNone(score(r,[v],ctx).total)
    def test_kyushu_high_power_solo_cw_goes_to_real_mop_code(self):
        r=rule('all_kyushu');c=next(c for c in r['event']['categories'] if c['id']=='XFMM');ctx=context(r,c);ctx['power']=200;v=sample(r,c)[0];v['mode']='CW';self.assertEqual(score(r,[v],ctx).total,1)
        c=next(c for c in r['event']['categories'] if c['id']=='XCSM');ctx['category']=c['id'];self.assertIsNone(score(r,[v],ctx).total)
        self.assertNotIn('XCMM',{c['id'] for c in r['event']['categories']})
    def test_tochigi_quota_replacement_and_outside_points(self):
        r=rule('tochigi');c=next(c for c in r['event']['categories'] if c['id']=='XSHF');ctx=context(r,c);v=sample(r,c)[0]
        s=score(r,[dict(v,sent='400101',exchange='1319')],ctx);self.assertEqual(s.total,1)
        s=score(r,[dict(v,sent='400101',exchange='430101')],ctx);self.assertEqual(s.points,1);self.assertIsNone(s.total)
        c=next(c for c in r['event']['categories'] if c['id']=='C50');ctx=context(r,c);v=sample(r,c)[0]
        self.assertIsNone(score(r,[dict(v,sent='1319',exchange='400101')],ctx).total)
        self.assertEqual(score(r,[dict(v,sent='1501',exchange='400101')],ctx).total,1)
    def test_ja4_base_point_and_two_disjoint_submissions(self):
        r=rule('all_ja4');c=next(c for c in r['event']['categories'] if c['id']=='G7');ctx=context(r,c);v=sample(r,c)[0]
        s=score(r,[v,dict(v,mode='SSB'),dict(v,mode='FM')],ctx);self.assertEqual((s.points,s.multi1,s.total),(2,1,2))
        ctx['entry_categories']=['G7','GHF'];self.assertIsNone(score(r,[v],ctx).total)
        ctx['entry_categories']=['G7','G14'];self.assertEqual(score(r,[v],ctx).total,1)
        self.assertNotIn('3101',r['event']['exchange']['codes']);self.assertIn('310101',r['event']['exchange']['codes'])
    def test_niigata_numbers_have_independent_definitions(self):
        r=rule('niigata_branch');c=next(c for c in r['event']['categories'] if c['id']=='GM7');ctx=context(r,c);v=sample(r,c)[0]
        ctx['entry_categories']=['GM7','GMHM'];self.assertEqual(score(r,[v],ctx).total,1)
        ctx['entry_categories']=['GM7','GC7'];self.assertIsNone(score(r,[v],ctx).total)
        self.assertEqual({c['regional']['section'] for c in rule('niigata_low_band')['event']['categories']},{'low'})
        self.assertNotIn('GMLM',{c['id'] for c in r['event']['categories']})
    def test_niigata_low_only_export_excludes_other_submission_sections(self):
        r=rule('niigata_low_band');c=next(c for c in r['event']['categories'] if c['id']=='GMLM');ctx=context(r,c)
        rows=sample(r,c)
        rows += [dict(rows[0],date='2026-05-17',time='13:00',band='7',call='JA0ZZZ'),dict(rows[0],date='2026-05-17',time='16:00',band='14',call='JA0YYY')]
        with tempfile.TemporaryDirectory() as tmp:
            repo=Repository(tmp);p=repo.path_for('JH1HST','',rows[0]['date'])
            for v in rows:repo.open(p).append(QSO(v['date'],v['time'],v['band'],v['mode'],v['call'],'599','599','原所在地','原自局所在地','原備考',''))
            before=p.read_bytes();sel=select_logs(repo,[p],'JH1HST')
            d={key(rec):dict(sent=v['sent'],received=v['exchange'],status='確認済み') for rec,v in zip(sel.rows,rows)}
            info=dict(contest=r['event']['submission']['contest'],category='GMLM',categoryname=c['name'],name='試験',address='試験',power='10',date='2026-09-15',signature='試験',oath=True,email='test@example.com',opplace='東京都試験',comments='確認済み')
            text=plan(sel,r,d,'JARL R1.0',info,context=ctx).preview()
            self.assertIn('<CATEGORYCODE>GMLM</CATEGORYCODE>',text)
            self.assertIn(rows[0]['call'],text)
            self.assertNotIn('JA0ZZZ',text);self.assertNotIn('JA0YYY',text)
            self.assertEqual(p.read_bytes(),before)
    def test_tohoku_inclusive_final_minute_and_high_bands(self):
        r=rule('all_tohoku');c=next(c for c in r['event']['categories'] if c['id']=='X1200UP');ctx=context(r,c);v=sample(r,c)[0]
        rows=[dict(v,date='2026-04-19',time='14:59',band='1200'),dict(v,date='2026-04-19',time='14:59',band='2400')];s=score(r,rows,ctx);self.assertEqual((s.points,s.multi1,s.total),(2,2,4))
        self.assertEqual(score(r,[dict(rows[0],time='15:00')],ctx).points,0);self.assertNotIn('XHF',{c['id'] for c in r['event']['categories']})
    def test_ja0_three_geographic_cases_cw_priority_and_junior(self):
        r=rule('ja0_vhf');c=next(c for c in r['event']['categories'] if c['id']=='SGSM');ctx=context(r,c);v=sample(r,c)[0]
        for sent,recv,points,multi in [('0901','13',1,0),('0901','0802',1,1),('13','10',0,0),('13','0901',1,1)]:
            s=score(r,[dict(v,sent=sent,exchange=recv)],ctx);self.assertEqual((s.points,s.multi1),(points,multi))
            if points:self.assertEqual(s.total,points*multi)
        rows=[dict(v,sent='13',exchange='0901',mode='FM'),dict(v,sent='13',exchange='0901',mode='CW')];s=score(r,rows,ctx);self.assertEqual([x['points'] for x in s.rows],[0,1])
        self.assertIsNone(score(r,[dict(rows[1],rst_received='59')],ctx).total)
        c=next(c for c in r['event']['categories'] if c['id']=='NNS50');ctx=context(r,c);rows=sample(r,c)
        ctx['declarations']['junior_birthdate']='2008-04-02';self.assertIsNotNone(score(r,rows,ctx).total)
        ctx['declarations']['junior_birthdate']='2008-04-01';self.assertIsNone(score(r,rows,ctx).total)
    def test_oita_independent_phone_modes_and_club_single_operator_rejection(self):
        r=rule('oita');c=next(c for c in r['event']['categories'] if c['id']=='VG1');ctx=context(r,c);v=sample(r,c)[0]
        rows=[dict(v,exchange='4401',mode=m) for m in ['SSB','FM','DMR','DMR','FT8']];s=score(r,rows,ctx);self.assertEqual((s.points,s.multi1,s.total),(3,1,3))
        ctx['station_type']='club';self.assertIsNone(score(r,rows,ctx).total)
        ctx['station_type']='individual';ctx['declarations']['area_basis']='';self.assertIsNotNone(score(r,rows,ctx).total)
    def test_independent_expected_category_counts_and_public_decimal_codes(self):
        expected={'all_kushiro':16,'all_aomori':56,'ja9_hf_phone':8,'ja9_hf_cw':8,'ja9_vu':9,'all_ja5':48,'kamikawa_souya':20,'oshima_hiyama':14,'all_kumamoto':42,'iwate_winter':4,'nagasaki':16,'wakayama':54,'all_ja4':26,'all_tohoku':28,'niigata_low_band':18,'niigata_branch':30,'tochigi':9,'all_kyushu':48,'kagoshima':31,'all_kanagawa':58,'ja0_vhf':14,'oita':41}
        self.assertEqual(set(IDS),set(expected))
        for ident,count in expected.items():self.assertEqual(len(rule(ident)['event']['categories']),count,ident)
        public={c.get('submission_code',c['id']) for c in rule('all_kumamoto')['event']['categories']};self.assertIn('GF1.9',public);self.assertIn('GC3.5',public);self.assertNotIn('GF19',public)
        self.assertEqual(rule('all_ja4')['event']['regional']['checklog_code'],'CHL');self.assertEqual(rule('all_tohoku')['event']['regional']['checklog_code'],'CHKLOG')
    def export_fixture(self,r,c,rows,ctx):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);repo=Repository(tmp.name);p=repo.path_for('JH1HST','',rows[0]['date'])
        for v in rows:
            rst='599' if v['mode']=='CW' else '59';repo.open(p).append(QSO(v['date'],v['time'],v['band'],v['mode'],v['call'],rst,rst,'元相手所在地','元運用地','元備考',''))
        sel=select_logs(repo,[p],'JH1HST');d={key(rec):dict(sent=v['sent'],received=v['exchange'],operator_name=v.get('operator_name',''),status='確認済み') for rec,v in zip(sel.rows,rows)}
        info=dict(contest=r['event']['submission']['contest'],category=c.get('submission_code',c['id']),categoryname=c['name'],name='試験',address='試験',power=str(ctx['power']),date='2026-09-15',signature='試験',oath=True,email='test@example.com',opplace='試験運用地',multiop=c.get('operator')=='MO',multioplist='JA1AAA 一アマ, JA1BBB 二アマ',comments='元意見')
        return p,sel,d,info
    def test_submission_checklog_alias_and_excluded_rows(self):
        for ident,code in [('all_ja4','CHL'),('all_tohoku','CHKLOG')]:
            r=rule(ident);c=r['event']['categories'][0];ctx=context(r,c);rows=sample(r,c);p,sel,d,info=self.export_fixture(r,c,rows,ctx);before=p.read_bytes()
            ctx['submission_mode']='checklog';info['category']=code;out=plan(sel,r,d,'JARL R1.0',info,context=ctx).preview();self.assertIn('<CATEGORYCODE>'+code+'</CATEGORYCODE>',out);self.assertIn('<TOTALSCORE>0</TOTALSCORE>',out);self.assertEqual(p.read_bytes(),before)
        r=rule('all_kumamoto');c=next(c for c in r['event']['categories'] if c['id']=='GC7');ctx=context(r,c);rows=sample(r,c);rows.append(dict(rows[0],band='14',call='JA6ZZZ'));p,sel,d,info=self.export_fixture(r,c,rows,ctx)
        out=plan(sel,r,d,'JARL R1.0',info,context=ctx).preview();self.assertIn('X 2026-01-11',out);self.assertIn('<SCORE BAND=TOTAL>1,1,1</SCORE>',out)
    def test_ja0_award_output_and_ja5_column_order(self):
        r=rule('ja0_vhf');c=next(c for c in r['event']['categories'] if c['id']=='NNS50');ctx=context(r,c);ctx['declarations']['junior_birthdate']='2008-04-02';rows=sample(r,c);p,sel,d,info=self.export_fixture(r,c,rows,ctx);before=p.read_bytes()
        out=plan(sel,r,d,'JARL R1.0',info,context=ctx).preview();self.assertIn('電信部門: CWのみ 1点',out);self.assertIn('ジュニア部門 生年月日: 2008-04-02',out);self.assertEqual(p.read_bytes(),before)
        r=rule('all_ja5');c=next(c for c in r['event']['categories'] if c['id']=='C7I');ctx=context(r,c);rows=sample(r,c);rows[0]['exchange']='3707';p,sel,d,info=self.export_fixture(r,c,rows,ctx)
        out=plan(sel,r,d,'JARL R1.0',info,context=ctx).preview();line=next(x for x in out.splitlines() if x.startswith('2026-07-18 '));fields=line.split();self.assertEqual(fields[2:5],['7','CW',rows[0]['call']]);self.assertEqual(fields[7:],['599','3707','37','1'])
    def test_operator_gui_and_multi_submission_filenames(self):
        from contest_submit_ui import DetailsDialog
        r=rule('ja9_vu');c=next(c for c in r['event']['categories'] if c['id']=='MM');ctx=context(r,c);rows=sample(r,c);p,sel,d,info=self.export_fixture(r,c,rows,ctx)
        dialog=DetailsDialog(sel,d,event=r['event']);self.assertEqual(dialog.operator_columns,1);dialog.table.item(0,dialog.operator_start).setText('JA1CCC');self.assertEqual(dialog.draft[key(sel.rows[0])]['operator_name'],'JA1CCC');dialog.close()
        r=rule('iwate_winter');filenames=[]
        for code in ['7TK','144TK']:
            c=next(c for c in r['event']['categories'] if c['id']==code);ctx=context(r,c);ctx['entry_categories']=['7TK','144TK'];p,sel,d,info=self.export_fixture(r,c,sample(r,c),ctx);filenames.append(plan(sel,r,d,'JARL R1.0',info,context=ctx).filename)
        self.assertEqual(len(set(filenames)),2)
    def test_pack_self_contained_roundtrip(self):
        import rule_pack
        from contest_rules import RuleStore
        with tempfile.TemporaryDirectory() as tmp:
            store=RuleStore(tmp);p=ROOT/'distribution/rules/regional_2026_r1.zip';preview=rule_pack.preview(store,p);self.assertEqual(len(preview.items),21);self.assertEqual(rule_pack.install(store,preview),21);self.assertEqual(rule_pack.install(store,rule_pack.preview(store,p)),0)
