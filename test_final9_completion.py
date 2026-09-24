from datetime import datetime
from test_final9 import QApplication,rule,score,export_case,tempfile,unittest

def context(r,c,**declarations):
    return dict(category=c['id'],station_type=c.get('station_types',['individual'])[0],power=5,entry_categories=[c['id']],flags={f:True for f in r['event']['required_flags']+c['required_flags']},declarations=declarations)
def row(**kw):
    v=dict(own='JH1HST',date='2026-06-21',time='09:00',band='7',mode='CW',call='JA1AAA',sent='3201',exchange='10',rst_sent='599',rst_received='599',country='JA');v.update(kw);return v
class CompletionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def test_party_names_threshold_and_noncompetition(self):
        r=rule('qso_party');c=r['event']['categories'][0];ctx=context(r,c,own_country='JA');rs=[row(date='2026-01-02',time='09:00',call=f'JA{i%10}A{chr(65+i)}',sent='太郎 Taro',exchange='花子 Hana') for i in range(20)]
        s=score(r,rs,ctx);self.assertEqual(s.total,0,s.problems);self.assertEqual(s.party_stations,20);self.assertIsNone(score(r,rs[:19]+[dict(rs[0],band='21')],ctx).total)
        with tempfile.TemporaryDirectory() as tmp:self.assertIn('太郎 Taro',export_case(tmp,r,c,ctx,rs)[0].preview())
        self.assertEqual(score(r,[dict(v,mode='NEW-DATA') for v in rs],ctx).total,0)
        ctx['declarations']['own_country']='DL';self.assertIsNone(score(r,[dict(v,country='W') for v in rs],ctx).total)
    def test_shimane_normal_categories_bonus_and_distinct_modes(self):
        r=rule('shimane')
        for c in r['event']['categories']:
            if c['id'] in ('1D','1H'):continue
            inside=c['id'][0]=='1';local=r['event']['regional']['local_a'][0];ctx=context(r,c,own_region=local if inside else '10',bonus='NO',licensed_region='3202',portable_equipment='既設設備・電源とも使わず独立設備と電池');rs=[row(band=c['bands'][0],sent=ctx['declarations']['own_region'],exchange=local)]
            s=score(r,rs,ctx);self.assertEqual(s.total,1,s.problems)
            with tempfile.TemporaryDirectory() as tmp:export_case(tmp,r,c,ctx,rs)
            ctx['declarations']['bonus']='YES';s=score(r,rs,ctx)
            if inside and c['regional']['section'] in ('HFH','HFL'):self.assertEqual(s.total,1001,s.problems)
            else:self.assertIsNone(s.total)
        c=next(c for c in r['event']['categories'] if c['id']=='1C');ctx=context(r,c,own_region='3201',bonus='NO',licensed_region='3202',portable_equipment='確認')
        s=score(r,[row(),row(mode='SSB',rst_sent='59',rst_received='59'),row(mode='FM',rst_sent='59',rst_received='59')],ctx);self.assertEqual((s.points,s.multi1,s.total),(3,1,3),s.problems)
    def test_ajd_earliest_mobile_area_and_ten_log_export(self):
        r=rule('shimane');c=next(c for c in r['event']['categories'] if c['id']=='1D');ctx=context(r,c,own_region='3201',bonus='NO',licensed_region='3202',portable_equipment='確認');rs=[row(call=f'JA{i}AAA',time=f'09:{i:02}') for i in range(10)]
        rs[3]['call']='JH1BBB/3';rs+=[row(call='JA0CCC',time='09:10')]
        s=score(r,rs,ctx);self.assertEqual(s.total,0,s.problems);self.assertEqual(s.ajd_completion,'09:09');self.assertEqual(len(s.ajd_indexes),10)
        with tempfile.TemporaryDirectory() as tmp:
            p=export_case(tmp,r,c,ctx,rs)[0];self.assertEqual(p.qsos,10);self.assertIn('<TOTALSCORE>09:09</TOTALSCORE>',p.preview());self.assertNotIn('JA0CCC',p.preview())
        self.assertIsNone(score(r,rs[:9],ctx).total)
        same=[dict(v,call='JH1HST/'+str(i)) for i,v in enumerate(rs[:10])];self.assertIsNone(score(r,same,ctx).total)
    def test_iburi_categories_two_locations_shared_multi_and_islands(self):
        r=rule('iburi_hidaka')
        for c in r['event']['categories']:
            inside=c['id'].startswith('I');ctx=context(r,c,fixed_region='0105' if inside else '10',fixed_address='常置住所',portable_region='0113',portable_address='移動住所');v=row(date='2026-07-24',time='21:00',own='JA8AAA',sent=ctx['declarations']['fixed_region'],exchange='0105',own_location='fixed',band=c['bands'][0]);rs=[v]
            if inside:rs += [dict(v,own='JA8AAA/8',sent='0113',own_location='portable'),dict(v,call='JA1AAA/8')]
            s=score(r,rs,ctx);self.assertEqual((s.points,s.multi1),(3 if inside else 1,1),s.problems)
            with tempfile.TemporaryDirectory() as tmp:
                p=export_case(tmp,r,c,ctx,rs)[0];self.assertIn('<CATEGORYCODE>'+('管内' if inside else '管外')+'</CATEGORYCODE>',p.preview());self.assertIn(c['name'],p.preview())
            if inside:
                self.assertIsNone(score(r,[dict(v,own='JA8AAA/7',own_location='portable',sent='0113')],ctx).total)
                self.assertEqual(score(r,[dict(v,exchange='48',island='OG'),dict(v,call='JD1AAA',exchange='48',island='MT')],ctx).multi1,2)
                self.assertIsNone(score(r,[dict(v,exchange='48')],ctx).total)
        self.assertEqual(sum((datetime.strptime(w['end'],'%Y-%m-%d %H:%M')-datetime.strptime(w['start'],'%Y-%m-%d %H:%M')).total_seconds() for w in r['event']['windows'])/3600,32)
    def test_toyama_all_categories_pdf_and_full_band_material(self):
        from pathlib import Path
        from io import BytesIO
        from PySide6.QtCore import QByteArray,QBuffer,QIODevice
        from PySide6.QtPdf import QPdfDocument
        def PdfReader(stream):
            data=QByteArray(stream.getvalue());buf=QBuffer(data);buf.open(QIODevice.ReadOnly);doc=QPdfDocument();doc.load(buf);count=doc.pageCount();doc.close();return type("Pages",(),{"pages":[None]*count})()
        r=rule('toyama_emergency')
        for c in r['event']['categories']:
            ctx=context(r,c,own_region='東京都' if c['id']=='O-M' else '富山市',equipment='試験機と電池',antenna='携行可能アンテナ');v=row(date='2026-01-10',time='19:00',band=c['bands'][0],mode='FM',rst_sent='59',rst_received='59',sent='富山市 山田',exchange='高岡市 田中',area='高岡市',qso_power='5');rs=[v]
            if len(c['bands'])==1:rs.append(dict(v,band='50' if v['band']!='50' else '21',call='JA2BBB',exchange='TOYAMA SATO',area='富山市'))
            s=score(r,rs,ctx);self.assertIsNotNone(s.total,s.problems)
            with tempfile.TemporaryDirectory() as tmp:
                p=export_case(tmp,r,c,ctx,rs)[0];self.assertTrue(p.data.startswith(b'%PDF'));pdf=PdfReader(BytesIO(p.data));self.assertGreaterEqual(len(pdf.pages),2)
                if c['id']=='I-21' and __import__('os').environ.get('PSLOG_PDF_SAMPLES'):Path(__import__('os').environ['PSLOG_PDF_SAMPLES'],'toyama_filled_sample.pdf').write_bytes(p.data)
        c=next(c for c in r['event']['categories'] if c['id']=='HANDY');ctx=context(r,c,own_region='富山市',equipment='試験機',antenna='アンテナ');self.assertIsNone(score(r,[dict(v,mode='SSB',checklog=True)],ctx).total)
    def test_toyama_fifty_one_suffix_check_sheet_and_original_names(self):
        from pathlib import Path
        from io import BytesIO
        from PySide6.QtCore import QByteArray,QBuffer,QIODevice
        from PySide6.QtPdf import QPdfDocument
        def PdfReader(stream):
            data=QByteArray(stream.getvalue());buf=QBuffer(data);buf.open(QIODevice.ReadOnly);doc=QPdfDocument();doc.load(buf);count=doc.pageCount();doc.close();return type("Pages",(),{"pages":[None]*count})()
        r=rule('toyama_emergency');c=r['event']['categories'][0];ctx=context(r,c,own_region='富山市',equipment='試験機',antenna='アンテナ');rs=[row(date='2026-01-10',time=f'19:{i:02}',band='21',sent='TOYAMA YAMADA',exchange='高岡市 田中',area='高岡市',call=f'JA{i%10}A{chr(65+i//26)}{chr(65+i%26)}') for i in range(51)]
        with tempfile.TemporaryDirectory() as tmp:
            p=export_case(tmp,r,c,ctx,rs)[0];pdf=PdfReader(BytesIO(p.data));self.assertEqual(len(pdf.pages),5)
            if __import__('os').environ.get('PSLOG_PDF_SAMPLES'):Path(__import__('os').environ['PSLOG_PDF_SAMPLES'],'toyama_51_sample.pdf').write_bytes(p.data)
    def test_toyama_submission_ui_and_worker(self):
        from test_final9 import Repository,QSO,key,select_logs,ROOT
        from contest_ui import ContestDialog
        from storage import Snapshot
        with tempfile.TemporaryDirectory() as tmp:
            repo=Repository(tmp);path=repo.path_for('JH1HST','','2026-01-10');repo.open(path).append(QSO('2026-01-10','19:00','21','FM','JA1AAA','59','59','','','',''))
            w=ContestDialog(repo,'JH1HST');w.timer.stop();w.format.setCurrentText('所定様式PDF');r=rule('toyama_emergency');c=r['event']['categories'][0];ctx=context(r,c,own_region='富山市',equipment='試験機',antenna='アンテナ');w.selection=select_logs(repo,[path],'JH1HST');w.loaded_scope=('JH1HST',(str(path),),'','','',False);w.draft={key(w.selection.rows[0]):dict(sent='富山市 山田',received='高岡市 田中',area='高岡市',country='JA',status='確認済み')};w.rule=r;w.result=score(r,__import__('contest').entries(w.selection,w.draft),ctx);w.rule_path=ROOT/'config/rules/toyama_emergency_2026.txt';w.rule_snapshot=Snapshot.read(w.rule_path);w.event_context=lambda:ctx
            w.submission.set_context();f=w.submission.fields
            for k,v in dict(name='試験',address='試験住所',signature='試験',opplace='富山市',date='2026-09-15').items():f[k].setText(v)
            f['oath'].setChecked(True);w.submission.prepare();self.assertIsNotNone(w.submission.prepared,w.submission.status.text());self.assertTrue(w.submission.prepared.data.startswith(b'%PDF'));w.close()
    def test_joint_selector_does_not_affect_ordinary_selection(self):
        from test_final9 import Repository,QSO,select_logs
        from contest_ui import ContestDialog
        with tempfile.TemporaryDirectory() as tmp:
            repo=Repository(tmp);paths=[]
            for own in ('JA8AAA','JA8AAA/8','JA8AAA/7'):
                p=repo.path_for(own,'','2026-07-24');repo.open(p).append(QSO('2026-07-24','21:00','7','CW','JA1AAA','599','599','','','',''));paths.append(p)
            with self.assertRaises(ValueError):select_logs(repo,paths[:2],'JA8AAA')
            self.assertEqual(len(select_logs(repo,paths[:2],'JA8AAA',joint=True).rows),2)
            with self.assertRaises(ValueError):select_logs(repo,paths,'JA8AAA',joint=True)
            w=ContestDialog(repo,'JA8AAA');w.own.setCurrentText('JA8AAA');self.assertEqual(w.logs.count(),1);w.joint.setChecked(True);self.assertEqual(w.logs.count(),2);w.timer.stop();w.close()
