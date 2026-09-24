import tempfile,unittest,shutil,json
from pathlib import Path
from unittest.mock import patch
from PySide6.QtWidgets import QApplication,QMessageBox
from clubs import load as load_clubs,number
from club_ui import ClubDialog
from locations import load,find,confirmed,candidates
from location_overrides import Overrides
from location_ui import LocationDialog
from storage import StorageError,ExternalChange,Repository
from model import QSO
from contest_rules import default_rule,RuleStore
from contest_ui import ContestDialog
from contest_export import plan,key
from contest import select_logs

class ReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
    def fixture(self):
        repo=Repository(self.root);q=QSO('2026-01-01','12:00','7','CW','JA1AAA','599','599','Japan','Tokyo Japan','001A','');path=repo.path_for('JH1HST','',q.date);repo.open(path).append(q);selection=select_logs(repo,[path],'JH1HST');draft={key(selection.rows[0]):{'sent':'13','received':'001A'}};return repo,selection,draft
    def test_club_alphabetic_prefix_and_leading_zero(self):
        self.assertEqual(number('０１ａ－１－００７'),'01A-1-007');self.assertEqual(number('13−1−7'),'13-1-7')
        with self.assertRaises(ValueError):number('01A-1-1\nEVIL')
        self.assertEqual(number('',optional=True),'');db=load_clubs(self.root);self.assertEqual(len(db.rows),887);self.assertEqual(db.lookup('01a-1-1')['name'],'ハムラジオ大雪クラブ');self.assertIsNone(db.lookup('01A-1-0001'))
    def test_club_integrity_and_no_silent_fallback(self):
        source=Path(__file__).parent/'config/db';target=self.root/'config/db';target.mkdir(parents=True)
        shutil.copy(source/'club_db.csv',target/'club_db.csv')
        with self.assertRaises(StorageError):load_clubs(self.root)
        shutil.copy(source/'club_db_meta.json',target/'club_db_meta.json');self.assertEqual(len(load_clubs(self.root).rows),887);(target/'club_db.csv').write_bytes((target/'club_db.csv').read_bytes()+b'\n')
        with self.assertRaises(StorageError):load_clubs(self.root)
    def test_club_search_pagination_and_pick(self):
        d=ClubDialog(load_clubs(self.root));self.assertEqual(d.table.rowCount(),100);d.move(1);self.assertEqual(d.page,1);d.search.setText('０１Ａ-1-1');self.assertEqual(d.page,0);self.assertGreater(d.table.rowCount(),0);d.table.selectRow(0);d.apply();self.assertEqual(d.result_value['number'],'01A-1-1');d.deleteLater()
    def test_jarl_alpha_club_number_output(self):
        repo,s,draft=self.fixture();info=dict(contest='TEST',category='X',name='氏名',address='住所',power='5',signature='署名',date='2026-01-02',oath=True,clubnumber='０１ａ－１－１',clubname='クラブ')
        text=plan(s,default_rule(),draft,'JARL R2.1',info).preview();self.assertIn('<REGCLUBNUMBER>01A-1-1</REGCLUBNUMBER>',text);self.assertNotIn('REGCLUBNAME',text)
    def test_club_name_assist_preserves_manual_input(self):
        repo,s,draft=self.fixture();RuleStore(self.root).save(default_rule());w=ContestDialog(repo,'JH1HST');w.advance();w.check_all(True);w.advance();w.draft=draft;w.advance();w.rules.setCurrentIndex(1);w.advance();p=w.submission;p.fields['clubnumber'].setText('01A-1-1');self.assertEqual(p.fields['clubname'].text(),'ハムラジオ大雪クラブ');p.fields['clubnumber'].clear();self.assertEqual(p.fields['clubname'].text(),'')
        p.fields['clubname'].setText('手入力');p.fields['clubnumber'].setText('01A-1-1');self.assertEqual(p.fields['clubname'].text(),'手入力');p.use_club();self.assertEqual(p.fields['clubname'].text(),'ハムラジオ大雪クラブ');w.deleteLater()
    def test_confirmed_spelling_is_local_and_reused(self):
        row=find(load(self.root),'東京都墨田区')[0];self.assertFalse(row['verified_qth']);o=Overrides(self.root);o.remember(row,'Sumida Tokyo Japan');data=load(self.root);r=find(data,'東京都墨田区')[0];self.assertEqual(r['qth_source'],'ユーザー確認済み');self.assertEqual(confirmed(data,r['name'],r['source_code']),'Sumida Tokyo Japan');self.assertEqual(candidates(data,r)[0][1],'ユーザー確認済み');self.assertFalse(find(load('/not-a-data-root'),'東京都墨田区')[0]['verified_qth'])
    def test_overrides_external_change_history_and_remove(self):
        row=find(load(self.root),'東京都墨田区')[0];a=Overrides(self.root);b=Overrides(self.root);a.remember(row,'Sumida Tokyo Japan')
        with self.assertRaises(ExternalChange):b.remember(row,'Other Tokyo Japan')
        before=a.path.read_bytes();a.forget(row);history=list((a.path.parent/'history').glob('*.json'));self.assertEqual(history[0].read_bytes(),before);self.assertFalse(find(load(self.root),'東京都墨田区')[0]['verified_qth'])
    def test_jcg_saved_at_town_not_whole_county(self):
        data=load(self.root);row=find(data,'上板町')[0];other=[r for r in data['rows'] if r['kind']=='JCG' and r['code']==row['code'] and r['source_code']!=row['source_code']];self.assertTrue(other);Overrides(self.root).remember(row,'Kamiita Itanogun Tokushima Japan');merged=load(self.root);self.assertNotIn('qth_source',next(r for r in merged['rows'] if r['name']==other[0]['name']));self.assertIn('qth_source',find(merged,'上板町')[0])
    def test_dialog_remember_is_opt_in_and_cancel_does_not_write(self):
        d=LocationDialog(self.root,'東京都墨田区');d.table.selectRow(0);d.qth.setCurrentText('Sumida Tokyo Japan');d.confirm.setChecked(True);d.apply();self.assertFalse((self.root/'config/db/location_overrides.json').exists());d.deleteLater()
        d=LocationDialog(self.root,'東京都墨田区');d.table.selectRow(0);d.qth.setCurrentText('Sumida Tokyo Japan');d.confirm.setChecked(True);d.remember.setChecked(True);d.reject();self.assertFalse((self.root/'config/db/location_overrides.json').exists());d.deleteLater()
        d=LocationDialog(self.root,'東京都墨田区');d.table.selectRow(0);d.qth.setCurrentText('Sumida Tokyo Japan');d.confirm.setChecked(True);d.remember.setChecked(True);d.apply();self.assertTrue((self.root/'config/db/location_overrides.json').exists());d.deleteLater()

    def test_import_reuses_user_spelling_and_respects_assist_off(self):
        from importing import prepare
        from storage import save_settings
        from test_hamlog_import import BASE,csvbytes
        row=find(load(self.root),'東京都墨田区')[0];Overrides(self.root).remember(row,'Sumida Tokyo Japan');record=BASE.copy();record[7]=row['source_code'];record[11]=row['name'];source=self.root/'input.csv';source.write_bytes(csvbytes([record]));repo=Repository(self.root)
        p=prepare(repo,source,'JH1HST');self.assertIn('Sumida Tokyo Japan',p.log.records[0][1].his_qth)
        save_settings(self.root,{'location_assist':False});p=prepare(repo,source,'JH1HST');self.assertNotIn('Sumida',p.log.records[0][1].his_qth);self.assertIn('東京都墨田区',p.log.records[0][1].remarks)
