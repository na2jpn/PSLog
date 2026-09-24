"""Acceptance coverage for the final unresolved domestic-contest profiles."""
from pathlib import Path
from copy import deepcopy
from datetime import datetime,timedelta
import unittest,tempfile
from PySide6.QtWidgets import QApplication
from contest_rules import loads,score
from contest import select_logs,entries
from contest_export import plan,key
from contest_submit_ui import DetailsDialog
from storage import Repository
from model import QSO
ROOT=Path(__file__).parent
IDS=['kcwa_cw','all_hyogo','hiroshima_was','shizuoka']
def rule(ident):return loads((ROOT/f'config/rules/{ident}_{2025 if ident=="kcwa_cw" else 2026}.txt').read_text(encoding='utf-8'))
def fixture(ident,cid=None):
    r=rule(ident);e=r['event'];c=next((c for c in e['categories'] if c['id']==cid),e['categories'][0]);band=c['bands'][0];w=next(w for w in e['windows'] if band in w['bands']);mode='SSB' if c.get('required_mode_families') else c['modes'][0];rst='599' if mode=='CW' else '59';local=e['regional']['local_a'];out=e['regional']['local_b'];d={'own_region':local[0],'location':'確認した運用地','locations':'各帯同一運用地','submission_number':'1','qrp':'NO','equipment':'機種と測定方法'}
    v=dict(own='JH1HST',date=w['start'][:10],time=w['start'][11:],band=band,mode=mode,call='JA1AAA',sent=local[0],exchange=local[-1],rst_sent=rst,rst_received=rst,country='JA',other_station='individual',operator_name='JA1AAA')
    ctx=dict(category=c['id'],station_type=c.get('station_types',['individual'])[0],power=1 if 'HP' in c['id'] else 5,entry_categories=[c['id']],flags={f:True for f in e['required_flags']+c['required_flags']},declarations=d)
    if ident=='kcwa_cw':v.update(sent='ST001',exchange='KT010');d['own_region']='ST'
    if ident=='all_hyogo' and c['id'].startswith('O-'):d['own_region']=v['sent']=out[0]
    if ident=='hiroshima_was' and c['id'].startswith('G-'):d['own_region']=v['sent']='PM95'
    if ident=='shizuoka':
        if c['id'].endswith('X'):d['own_region']=v['sent']=out[0]
        if 'HP' in c['id']:d['qrp']='YES';v['own']='JH1HST/QRP'
    rows=[v]
    if c['min_bands']>1:rows.append(dict(v,band=c['bands'][1],sent='ST001' if ident=='kcwa_cw' else v['sent'],call='JA2BBB',time='10:01'))
    if c.get('regional',{}).get('min_operators'):rows.append(dict(v,call='JA2BBB',operator_name='JA2BBB',time=(datetime.strptime(v['time'],'%H:%M')+timedelta(minutes=1)).strftime('%H:%M')))
    return r,c,ctx,rows

def export_case(tmp,r,c,ctx,rows):
    repo=Repository(tmp);paths=[]
    for v in rows:
        p=repo.path_for(v['own'],'',v['date']);repo.open(p).append(QSO(v['date'],v['time'],v['band'],v['mode'],v['call'],v.get('rst_sent',''),v.get('rst_received',''),'原相手QTH','原自局QTH','原備考',''))
        if p not in paths:paths.append(p)
    sel=select_logs(repo,paths,rows[0]['own'],joint=r['id']=='iburi_hidaka' and len({v['own'] for v in rows})>1);pending=list(rows);ordered=[]
    for rec in sel.rows:
        index=next(i for i,v in enumerate(pending) if (v['own'],v['date'],v['time'],v['band'],v['mode'],v['call'])==(rec[0],rec[1].date,rec[1].time,rec[1].band,rec[1].mode,rec[1].call));ordered.append(pending.pop(index))
    draft={key(rec):dict(**{k:v.get(k,'') for k in ('sent','country','continent','operator_name','other_station','communication','qso_power','own_location','island','area')},received=v.get('exchange',''),status='確認済み',checklog=v.get('checklog',False)) for rec,v in zip(sel.rows,ordered)};before={p:p.read_bytes() for p in paths};outputs=[]
    info=dict(contest=r['event']['submission']['contest'],category=c.get('submission_code',c['id']),categoryname=c['name'],name='試験',address='試験住所',power=str(ctx['power']),date='2026-09-15',signature='試験',oath=True,zone='JST',multiop=c.get('operator')=='MO',multioplist='JA1AAA JA2BBB',opplace='運用地',tel='000-0000-0000',email='test@example.com',comments='')
    for fmt in r['event']['submission']['formats']:outputs.append(plan(sel,r,draft,fmt,info,context=ctx))
    assert all(p.read_bytes()==b for p,b in before.items())
    dialog=DetailsDialog(sel,draft,event=r['event'])
    for col,field in dialog.extra_columns.items():assert dialog.table.item(0,col).text()==draft[key(sel.rows[0])].get(field,'')
    dialog.close();return outputs

class FinalNineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def test_all_categories_score_export_original(self):
        self.assertEqual([len(rule(i)['event']['categories']) for i in IDS],[3,54,25,54])
        for ident in IDS:
            for cat in rule(ident)['event']['categories']:
                with self.subTest(contest=ident,category=cat['id']),tempfile.TemporaryDirectory() as tmp:
                    r,c,ctx,rows=fixture(ident,cat['id']);before=deepcopy(rows);s=score(r,rows,ctx);self.assertIsNotNone(s.total,s.problems);self.assertEqual(rows,before)
                    for p in export_case(tmp,r,c,ctx,rows):self.assertIn('<TOTALSCORE>'+str(s.total)+'</TOTALSCORE>',p.preview())
    def test_kcwa_serial_region_and_category_checklog(self):
        r,c,ctx,rows=fixture('kcwa_cw','B7');v=rows[0];rs=[v,dict(v,call='JA2BBB',sent='ST003',exchange='KT9999'),dict(v,band='3.5',sent='ST001')];s=score(r,rs,ctx);self.assertEqual((s.points,s.multi1,s.total),(2,1,2),s.problems)
        with tempfile.TemporaryDirectory() as tmp:self.assertIn('X ',export_case(tmp,r,c,ctx,rs)[0].preview())
        self.assertIsNone(score(r,[dict(v,other_station='club')],ctx).total)
        self.assertIsNone(score(r,[v,dict(v,call='JA2BBB')],ctx).total)
    def test_hyogo_2701_foreign_qrp_phone_and_second_call(self):
        r,c,ctx,rows=fixture('all_hyogo','I-MS-7');v=rows[0];s=score(r,[v,dict(v,call='JA3BBB',exchange='2701'),dict(v,call='DL1AAA',exchange='',country='DL')],ctx);self.assertEqual((s.points,s.multi1,s.total),(3,1,3),s.problems)
        ctx['entry_categories']=['I-MS-144','I-MS-7'];ctx['declarations']['submission_number']='2';v['own']='JH1HST/3'
        with tempfile.TemporaryDirectory() as tmp:self.assertIn('<CALLSIGN>JH1HST-2/3</CALLSIGN>',export_case(tmp,r,c,ctx,[v])[0].preview())
        ctx['entry_categories']=['I-MS-ALL','I-MS-7'];self.assertIsNone(score(r,[v],ctx).total)
    def test_hiroshima_modes_real_band_and_invalid_exchange(self):
        r,c,ctx,rows=fixture('hiroshima_was','N-1200');v=rows[0];rs=[v,dict(v,mode='SSB',rst_sent='59',rst_received='59'),dict(v,mode='FT8',rst_sent='+05',rst_received='-01'),dict(v,mode='FT4',rst_sent='+05',rst_received='-01'),dict(v,band='2400'),dict(v,call='JA2BBB',exchange='999999')];s=score(r,rs,ctx);self.assertEqual((s.points,s.multi1,s.total),(20,2,40),s.problems)
        voice=dict(v,mode='DSTAR',communication='phone');data=dict(voice,communication='digital');self.assertEqual(score(r,[voice,data],ctx).points,10)
        self.assertIsNone(score(r,[dict(voice,communication='')],ctx).total)
        self.assertIsNone(score(r,[dict(v,mode='FT8',rst_sent='',rst_received='')],ctx).total)
    def test_shizuoka_qrp_all_contacts_and_10ghz_merge(self):
        r,c,ctx,rows=fixture('shizuoka','FMS');v=rows[0];v.update(own='JH1HST/QRP',time='17:00',qso_power='1');ctx['declarations']['qrp']='YES';s=score(r,[v,dict(v,call='JA2BBB/QRP'),dict(v,call='JA2BBB/Q')],ctx);self.assertEqual((s.points,s.multi1,s.total),(6,1,6),s.problems)
        self.assertIsNone(score(r,[v,dict(v,call='JA2AAA',qso_power='2',checklog=True)],ctx).total)
        rs=[dict(v,band='10.1G',time='14:00',qso_power='10'),dict(v,band='10.4G',time='14:01',qso_power='10')];s=score(r,rs,ctx);self.assertEqual((s.points,s.multi1,s.total),(20,1,20),s.problems)

    def test_was_combined_submission_and_snapshot_guard(self):
        from contest_bundle import item,combine
        with tempfile.TemporaryDirectory() as a,tempfile.TemporaryDirectory() as b:
            data=[]
            for cid,tmp in [('N-7',a),('G-14',b)]:
                r,c,ctx,rows=fixture('hiroshima_was',cid);ctx['entry_categories']=['N-7','G-14'];p=export_case(tmp,r,c,ctx,rows)[0];data.append(item(r,ctx,rows[0]['own'],p))
            combined=combine(data);self.assertEqual(combined.preview().count('<SUMMARYSHEET VERSION=R1.0>'),2)
            with self.assertRaises(ValueError):combine(data[:1])
            f=data[0]['plan'].sessions[0].path;f.write_bytes(f.read_bytes()+b'changed')
            with self.assertRaises(Exception):combine(data)
