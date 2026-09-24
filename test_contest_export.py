import csv,io,tempfile,unittest,json
from pathlib import Path
from copy import deepcopy
from dataclasses import replace
from unittest.mock import patch
from decimal import Decimal
from PySide6.QtWidgets import QApplication,QMessageBox
from storage import Repository,Snapshot,ExternalChange
from model import QSO
from contest import select_logs
from contest_rules import RuleStore,default_rule,score
from contest_export import plan,save,key,SubmitProfiles,ZLOG_HEADER
from cabrillo_templates import default_template,TemplateStore,validate,loads,V2,V3
from cabrillo_template_ui import TemplateEditor,TemplatesDialog
from contest_ui import ContestDialog
from contest_submit_ui import DetailsDialog

class ExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.repo=Repository(self.tmp.name);self.q=QSO('2026-01-01','08:59','7','CW','JA1AAA','599','599','Japan','Tokyo Japan','FD 001A BURO','');self.path=self.repo.path_for('JH1HST/1','',self.q.date);self.repo.open(self.path).append(self.q);self.selection=select_logs(self.repo,[self.path],'JH1HST/1');self.rule=default_rule();self.draft={key(self.selection.rows[0]):{'sent':'13L','received':'001A','status':'確認済み'}};self.info=dict(contest='テストコンテスト',category='X',name='試験 太郎',address='東京都 試験住所',power='5',date='2026-01-02',signature='試験 太郎',oath=True)
    def output(self,fmt='JARL R2.1',info=None,template=None,**kw):return plan(self.selection,self.rule,self.draft,fmt,info or self.info,template,**kw)
    def cab(self):
        t=default_template();info={'CONTEST':'TEST','NAME':'Test Operator','ADDRESS':'Test address','CATEGORY-OPERATOR':'SINGLE-OP','CATEGORY-BAND':'ALL','CATEGORY-POWER':'LOW','CATEGORY-MODE':'CW'};return t,info
    def test_jarl_versions_fd_zero_and_jst_utc(self):
        self.rule['multi2'].update(kind='fixed',value=0);self.info.update(fd=True,opplace='試験運用地',powersupply='電池',clubnumber='13-01-007',clubname='試験クラブ',licenseclass='第2級アマチュア無線技士')
        for version in ('R1.0','R2.1'):
            text=self.output('JARL '+version).preview();self.assertIn(f'<SUMMARYSHEET VERSION={version}>',text);self.assertIn('<TOTALSCORE>0</TOTALSCORE>',text);self.assertIn('<FDCOEFF>0</FDCOEFF>',text);self.assertIn('<REGCLUBNUMBER>13-01-007</REGCLUBNUMBER>',text);self.assertIn('2026-01-01 08:59 7 CW JA1AAA 599 13L 599 001A 001A 1',text)
            self.assertEqual('<REGCLUBNAME>' in text,version=='R1.0');self.assertEqual('<SCORE BAND=7MHz>1,1,1</SCORE>' in text,version=='R1.0')
        self.info['zone']='UTC';self.assertIn('2025-12-31 23:59',self.output().preview());self.assertEqual(self.path.read_bytes(),self.selection.sessions[0].snapshot.data)
    def test_jarl_r10_licenseclass_is_emitted_when_present_and_core_export_stays_compatible(self):
        # The interactive R1.0 screen requires licenseclass, but the low-level
        # writer must still be able to read/rebuild historical R1.0 submissions
        # that omitted this field.
        text=self.output('JARL R1.0').preview();self.assertNotIn('<LICENSECLASS>',text)
        self.assertIn('<SUMMARYSHEET VERSION=R2.1>',self.output('JARL R2.1').preview())
        self.info['licenseclass']='第2級アマチュア無線技士'
        self.assertIn('<LICENSECLASS>第2級アマチュア無線技士</LICENSECLASS>',self.output('JARL R1.0').preview())
    def test_jarl_prevents_injection_missing_exchange_and_oath(self):
        self.info['name']='hello\n<NAME>bad</NAME>'
        with self.assertRaises(ValueError):self.output()
        self.info['name']='Name';self.info['oath']=False
        with self.assertRaises(ValueError):self.output()
        self.info['oath']=True;self.draft[key(self.selection.rows[0])]['sent']=''
        with self.assertRaises(ValueError):self.output()
    def test_cabrillo_utc_layout_frequency_and_overflow(self):
        t,info=self.cab();p=self.output('Cabrillo',info,t);text=p.preview();self.assertTrue(text.startswith('START-OF-LOG: 3.0\r\n'));self.assertTrue(text.endswith('END-OF-LOG:\r\n'));qso=next(x for x in text.splitlines() if x.startswith('QSO:'));self.assertEqual(qso.split(),['QSO:','7000','CW','2025-12-31','2359','JH1HST/1','599','13L','JA1AAA','599','001A']);self.assertTrue(p.warnings)
        t['frequency']='actual'
        with self.assertRaises(ValueError):self.output('Cabrillo',info,t)
        self.draft[key(self.selection.rows[0])]['frequency']='7005';self.assertIn('QSO:  7005',self.output('Cabrillo',info,t).preview())
        t['columns'][6]['width']=2
        with self.assertRaises(ValueError):self.output('Cabrillo',info,t)
    def test_cabrillo_v2_template_and_header_rules(self):
        t,info=self.cab();t['version']='2.0'
        with self.assertRaises(ValueError):validate(t)
        t['headers']=[h for h in t['headers'] if h['tag'] not in V3]+[{'tag':'CATEGORY','required':True,'default':'','choices':[]},{'tag':'ARRL-SECTION','required':False,'default':'','choices':[]}];info.update(CATEGORY='SINGLE-OP ALL LOW',**{'ARRL-SECTION':'DX'});text=self.output('Cabrillo',info,t).preview();self.assertIn('START-OF-LOG: 2.0',text);self.assertIn('CATEGORY: SINGLE-OP ALL LOW',text);self.assertNotIn('CATEGORY-OPERATOR:',text)
        info['CATEGORY']='SINGLE-OP\nQSO: injected'
        with self.assertRaises(ValueError):self.output('Cabrillo',info,t)
    def test_template_literal_rst_and_exchange_parts(self):
        t,info=self.cab();t['columns'][5].update(source='literal',literal='-');t['columns'][6].update(part=2);self.draft[key(self.selection.rows[0])]['sent']='001 PM95';text=self.output('Cabrillo',info,t).preview();qso=next(x for x in text.splitlines() if x.startswith('QSO:'));self.assertEqual(qso.split()[6:8],['-','PM95'])
    def test_zlog_matches_current_loader_columns_and_khz(self):
        self.draft[key(self.selection.rows[0])]['frequency']='7005.5';info={'zone':'UTC','power_code':'P','memo':True};p=self.output('zLog令和版CSV',info);self.assertTrue(p.data.startswith(b'\xef\xbb\xbf'));rows=list(csv.reader(io.StringIO(p.preview())));self.assertEqual(len(rows[1]),34);self.assertEqual(rows[0],'Date,Time,TimeZone,CallSign,RSTSent,NrSent,RSTRcvd,NrRcvd,Serial,Mode,Band,Power,Multi1,Multi2,NewMulti1,NewMulti2,Points,Operator,Memo,CQ,Dupe,Reserve,TX,Power2,Reserve2,Reserve3,Freq,QsyViolation,PCName,Forced,QslState,Invalid,Area,RBN Verified'.split(','));r=rows[1];self.assertEqual(r[:12],['2025/12/31','23:59:00','UTC','JA1AAA','599','13L','599','001A','1','CW','7','P']);self.assertEqual(r[12:17],['001A','','True','False','1']);self.assertEqual(r[18],self.q.remarks);self.assertEqual(r[26],'7005.5');self.assertEqual(r[30:34],['0','False','','False'])
    def test_zlog_rejects_loader_fallback_and_decimal_points(self):
        self.selection.rows[0]=(self.selection.rows[0][0],replace(self.q,mode='FT8 AS'),self.path,1)
        with self.assertRaises(ValueError):self.output('zLog令和版CSV',{'power_code':'P'})
        self.selection.rows[0]=(self.selection.rows[0][0],self.q,self.path,1);self.rule['points']['cw']=0.5
        with self.assertRaises(ValueError):self.output('zLog令和版CSV',{'power_code':'P'})
    def test_save_nonoverwrite_log_and_template_guards(self):
        t,info=self.cab();path,s=TemplateStore(self.tmp.name).save(t);p=self.output('Cabrillo',info,t,guards=[(path,s)]);a=save(p,self.tmp.name);b=save(p,self.tmp.name);self.assertEqual(a.name,'JH1HST-1.log');self.assertEqual(b.name,'JH1HST-1_001.log');path.write_bytes(path.read_bytes()+b' ')
        with self.assertRaises(ExternalChange):save(p,self.tmp.name)
        p=self.output();self.path.write_bytes(self.path.read_bytes()+b'\n')
        with self.assertRaises(ExternalChange):save(p,self.tmp.name)
    def test_profile_only_remembers_required_identity_fields(self):
        profiles=SubmitProfiles(self.tmp.name);self.assertFalse(profiles.path.exists());info=dict(self.info,clubnumber='13-01-007',clubname='試験クラブ');profiles.remember('jarl',info);read=SubmitProfiles(self.tmp.name).values['jarl'];self.assertEqual(set(read),{'name','address','power','signature','clubnumber','clubname'});self.assertEqual(read['clubnumber'],'13-01-007');self.assertEqual(read['clubname'],'試験クラブ');self.assertNotIn('contest',read);self.assertNotIn('date',read)
        profiles=SubmitProfiles(self.tmp.name);profiles.remember('jarl',dict(self.info,clubnumber='13-01-008'));read=SubmitProfiles(self.tmp.name).values['jarl'];self.assertEqual(read['clubnumber'],'13-01-008');self.assertEqual(read['clubname'],'試験クラブ')
        profiles.path.write_text('{}')
        with self.assertRaises(ExternalChange):profiles.remember('jarl',self.info)
    def test_scoring_decimal_precision(self):
        self.rule['multi1']['kind']='off';self.rule['duplicate']['enabled']=False;self.rule['points']['cw']=0.1;s=score(self.rule,[dict(call='JA1AAA',band='7',mode='CW',exchange='1') for _ in range(10)]);self.assertEqual(s.total,Decimal('1.0'));self.assertEqual(s.total,1)
    def test_template_editor_roundtrip_and_duplicate_key(self):
        store=TemplateStore(self.tmp.name);e=TemplateEditor(store);e.fields['id'].setText('test');e.save();self.assertIsNotNone(e.saved_path);self.assertEqual(store.read(e.saved_path)[0]['id'],'test');e.version.setCurrentText('2.0')
        with patch.object(QMessageBox,'question',return_value=QMessageBox.Yes):e.change_version_headers()
        self.assertIn('CATEGORY',[h['tag'] for h in e.collect()['headers']]);e.deleteLater();m=TemplatesDialog(self.tmp.name);self.assertEqual(m.list.count(),1);m.deleteLater()
        with self.assertRaises(ValueError):loads('{"schema":1,"schema":1}')
    def test_stage5_file_save_profile_and_invalidation(self):
        RuleStore(self.tmp.name).save(self.rule);d=ContestDialog(self.repo,'JH1HST/1');d.format.setCurrentIndex(1);d.advance();d.check_all(True);d.advance();d.draft=deepcopy(self.draft);d.advance();d.rules.setCurrentIndex(1);d.advance();self.assertEqual(d.stack.currentIndex(),4);p=d.submission
        for k,v in self.info.items():
            if k=='oath':p.fields[k].setChecked(v)
            else:p.fields[k].setText(v)
        p.fields['email'].setText('test@example.com')
        p.prepare();self.assertIsNotNone(p.prepared,p.status.text());p.fields['name'].setText('別の氏名');self.assertIsNone(p.prepared);p.prepare();p.write();self.assertTrue((Path(self.tmp.name)/'output'/'contest'/'JH1HST-1.txt').exists());self.assertTrue((Path(self.tmp.name)/'config'/'contest_submit.cfg').exists());d.deleteLater()
    def test_details_cancel_leaves_original_working_values(self):
        d=DetailsDialog(self.selection,self.draft);d.table.item(0,4).setText('7005');d.reject();self.assertNotIn('frequency',self.draft[key(self.selection.rows[0])]);self.assertEqual(d.draft[key(self.selection.rows[0])]['frequency'],'7005');d.deleteLater()

    def test_zlog_power_suffix_split_is_explicit(self):
        p=self.output('zLog令和版CSV',{'split_power':True});r=list(csv.reader(io.StringIO(p.preview())))[1];self.assertEqual(r[5],'13');self.assertEqual(r[11],'L')
        p=self.output('zLog令和版CSV',{'power_code':'P'});r=list(csv.reader(io.StringIO(p.preview())))[1];self.assertEqual(r[5],'13L');self.assertEqual(r[11],'P')
    def test_stage5_cabrillo_header_edit_and_save(self):
        RuleStore(self.tmp.name).save(self.rule);t,info=self.cab();TemplateStore(self.tmp.name).save(t);d=ContestDialog(self.repo,'JH1HST/1');d.format.setCurrentIndex(2);d.advance();d.check_all(True);d.advance();d.draft=deepcopy(self.draft);d.advance();d.rules.setCurrentIndex(1);d.advance();p=d.submission;p.templates.setCurrentIndex(1)
        from PySide6.QtWidgets import QComboBox,QPlainTextEdit
        for k,v in info.items():
            w=p.fields[k]
            if isinstance(w,QComboBox):w.setCurrentText(v)
            elif isinstance(w,QPlainTextEdit):w.setPlainText(v)
            else:w.setText(v)
        p.prepare();self.assertIsNotNone(p.prepared,p.status.text());p.write();self.assertTrue((Path(self.tmp.name)/'output'/'contest'/'JH1HST-1.log').exists());d.deleteLater()

    def test_known_dv_and_exact_large_score(self):
        self.selection.rows[0]=(self.selection.rows[0][0],replace(self.q,mode='DV'),self.path,1);self.rule['points']['digital']=12345678.0
        p=self.output('zLog令和版CSV',{'power_code':'L'});r=list(csv.reader(io.StringIO(p.preview())))[1];self.assertEqual(r[9],'DV');self.assertEqual(r[16],'12345678')
        self.assertIn('<TOTALSCORE>12345678</TOTALSCORE>',self.output().preview())
