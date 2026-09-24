"""All submission formats through the five-stage Qt wizard."""
import csv,io,tempfile,unittest
from pathlib import Path
from PySide6.QtWidgets import QApplication,QComboBox,QPlainTextEdit,QCheckBox
from contest_ui import ContestDialog
from contest_export import key
from contest_rules import RuleStore,default_rule
from cabrillo_templates import TemplateStore,default_template,V3
from storage import Repository
from model import QSO

class ContestWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.repo=Repository(self.tmp.name)
        self.q=QSO('2026-01-01','08:59','7','CW','JA1AAA','599','599','Japan','Soka Saitama Japan','001A')
        self.path=self.repo.path_for('JH1HST/1','',self.q.date);self.repo.open(self.path).append(self.q)
        self.original=self.path.read_bytes();RuleStore(self.tmp.name).save(default_rule())
    def wizard(self,fmt,version='3.0'):
        if fmt=='Cabrillo':
            t=default_template();t['version']=version
            if version=='2.0':t['headers']=[h for h in t['headers'] if h['tag'] not in V3]+[{'tag':'CATEGORY','required':True,'default':'','choices':[]}]
            TemplateStore(self.tmp.name).save(t)
        d=ContestDialog(self.repo,'JH1HST/1');self.addCleanup(d.deleteLater)
        d.format.setCurrentText(fmt);d.advance();d.check_all(True);d.advance()
        self.assertEqual(d.stack.currentIndex(),2,d.status.text())
        d.sent.setText('13L');d.fill_sent();d.extract();d.confirm_page()
        self.assertEqual(d.draft[key(d.selection.rows[0])]['received'],'001A')
        d.advance();d.rules.setCurrentIndex(1);d.advance()
        self.assertEqual(d.stack.currentIndex(),4,d.status.text())
        p=d.submission
        if fmt=='Cabrillo':p.templates.setCurrentIndex(1)
        return d,p
    def fill(self,p,values):
        for key,value in values.items():
            w=p.fields[key]
            if isinstance(w,QCheckBox):w.setChecked(value)
            elif isinstance(w,QComboBox):w.setCurrentText(value)
            elif isinstance(w,QPlainTextEdit):w.setPlainText(value)
            else:w.setText(value)
    def test_all_formats_prepare_invalidate_save_and_collision(self):
        for fmt,version,ext in [('JARL R1.0','', 'txt'),('JARL R2.1','','txt'),('Cabrillo','3.0','log'),('zLog令和版CSV','','csv')]:
            with self.subTest(format=fmt):
                d,p=self.wizard(fmt)
                p.prepare();self.assertIsNone(p.prepared)
                if fmt.startswith('JARL'):
                    values=dict(contest='試験コンテスト',category='X',name='試験 太郎',address='東京都',power='5',date='2026-01-02',signature='試験 太郎',email='test@example.com',oath=True)
                    if fmt=='JARL R1.0':values.update(licenseclass='第2級アマチュア無線技士',powertype='定格出力')
                elif fmt=='Cabrillo':
                    values={'CONTEST':'TEST','NAME':'Test Operator','ADDRESS':'Test address','CATEGORY-OPERATOR':'SINGLE-OP','CATEGORY-BAND':'ALL','CATEGORY-POWER':'LOW','CATEGORY-MODE':'CW'}
                else:values={'power_code':'L'}
                self.fill(p,values);p.prepare();self.assertIsNotNone(p.prepared,p.status.text())
                payload=p.prepared.data
                # Changing the destination requires another review.
                out=Path(self.tmp.name)/fmt.replace('/','-');out.mkdir()
                p.folder.setText(str(out));self.assertIsNone(p.prepared);self.assertFalse(p.save_button.isEnabled())
                p.prepare();self.assertIsNotNone(p.prepared,p.status.text());p.write()
                first=out/('JH1HST-1.'+ext);self.assertEqual(first.read_bytes(),payload)
                p.prepare();p.write();self.assertEqual((out/('JH1HST-1_001.'+ext)).read_bytes(),payload)
                self.assertEqual(self.path.read_bytes(),self.original)
                if fmt=='zLog令和版CSV':
                    rows=list(csv.reader(io.StringIO(payload.decode('utf-8-sig'))));self.assertEqual(len(rows),2);self.assertEqual(len(rows[1]),34)
                elif fmt.startswith('JARL'):self.assertIn('<SUMMARYSHEET VERSION='+fmt[5:]+'>',payload.decode('cp932'))
                else:self.assertIn('START-OF-LOG: 3.0',payload.decode())
                d.timer.stop();d.cancel_score()
    def test_jarl_r10_requires_licenseclass_in_ui_but_r21_does_not(self):
        d,p=self.wizard('JARL R1.0')
        base=dict(contest='試験コンテスト',category='X',name='試験 太郎',address='東京都',power='5',date='2026-01-02',signature='試験 太郎',email='test@example.com',oath=True)
        self.fill(p,base);p.prepare();self.assertIsNone(p.prepared);self.assertIn('従事者資格',p.status.text())
        self.fill(p,{'licenseclass':'第2級アマチュア無線技士'});p.prepare();self.assertIsNone(p.prepared);self.assertIn('出力の記載区分',p.status.text())
        self.fill(p,{'powertype':'定格出力'});p.prepare();self.assertIsNotNone(p.prepared,p.status.text())
        d.timer.stop();d.cancel_score()

        d,p=self.wizard('JARL R2.1')
        self.fill(p,base);p.prepare();self.assertIsNotNone(p.prepared,p.status.text())
        d.timer.stop();d.cancel_score()

    def test_cabrillo_2_and_source_change_before_save(self):
        d,p=self.wizard('Cabrillo','2.0')
        self.fill(p,{'CONTEST':'TEST','NAME':'Test Operator','ADDRESS':'Test address','CATEGORY':'SINGLE-OP ALL LOW'})
        p.prepare();self.assertIsNotNone(p.prepared,p.status.text());self.assertIn('START-OF-LOG: 2.0',p.preview.toPlainText())
        self.path.write_bytes(self.original+b'\r\n');p.write()
        self.assertFalse((Path(self.tmp.name)/'JH1HST-1.log').exists());self.assertFalse(p.save_button.isEnabled())
        self.assertIn('変更',p.status.text())
