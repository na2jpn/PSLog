import json,os,tempfile,unittest
from pathlib import Path

from storage import Repository,VERSION
from model import QSO
from logbook_sources import ensure_logbook_directories,amateur_log_files,amateur_station_calls
from jccjcg_award_check import aggregate,STATE_WORKED,STATE_QSL
from update_package import PRESERVED_ROOTS


class Patch041074CoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);ensure_logbook_directories(self.root);self.repo=Repository(self.root)
        db=self.root/'config/db';db.mkdir(parents=True)
        rows=[
            {'code':'110101','name':'横浜市 鶴見区','prefecture':'神奈川 11','kind':'ward'},
            {'code':'110102','name':'横浜市 神奈川区','prefecture':'神奈川 11','kind':'ward'},
            {'code':'1102','name':'横須賀市','prefecture':'神奈川 11','kind':'city'},
            {'code':'11002','name':'足柄上郡','prefecture':'神奈川 11','kind':'gun'},
            {'code':'100101','name':'東京都 千代田区','prefecture':'東京 10','kind':'ward'},
        ]
        (db/'aja_locations.json').write_text(json.dumps({'schema':1,'rows':rows},ensure_ascii=False),encoding='utf-8')

    def add(self,call,suffix,date,time,band,his,code,remarks=''):
        p=self.repo.path_for(call,suffix,date);s=self.repo.open(p)
        s.append(QSO(date,time,band,'CW',his,'599','599','Japan','Soka Saitama Japan',remarks,code))
        return p

    def test_version_and_reserved_free_radio_directory(self):
        self.assertEqual(VERSION,'1.14')
        self.assertTrue((self.root/'logbook').is_dir())
        self.assertTrue((self.root/'logbook_flr').is_dir())
        self.assertEqual(self.repo.free_book,self.root/'logbook_flr')
        self.assertIn('logbook_flr',PRESERVED_ROOTS)

    def test_amateur_discovery_never_reads_free_radio_store(self):
        self.add('JH1HST','','2026-09-24','08:00','7','JA1AAA','1102')
        (self.root/'logbook_flr'/'2026_FLR_.txt').write_text('not an amateur log',encoding='utf-8')
        self.assertEqual([p.parent.name for p in amateur_log_files(self.repo)],['logbook'])
        self.assertEqual(amateur_station_calls(self.repo),['JH1HST'])

    def test_award_aggregate_maps_ward_to_city_and_jcg_letter_to_gun(self):
        self.add('JH1HST','','2026-09-24','08:00','7','JA1AAA','110101')
        self.add('JH1HST','', '2026-09-24','08:01','14','JA1BBB','11002A','hQSL.R')
        self.add('JH1HST/P','','2026-09-24','08:02','7','JA1CCC','11002B')
        result=aggregate(self.repo,'JH1HST',portable=True)
        self.assertEqual(result.files,2);self.assertEqual(result.qsos,3);self.assertEqual(result.matched,3)
        rows={r.code:r for p in result.prefectures for r in p.locations}
        self.assertEqual(rows['1101'].states['7'],STATE_WORKED)
        self.assertEqual(rows['11002'].states['14'],STATE_QSL)
        self.assertEqual(rows['11002'].states['7'],STATE_WORKED)
        self.assertEqual(rows['11002'].all_state,STATE_QSL)
        # Portable-off excludes the /P log.
        plain=aggregate(self.repo,'JH1HST',portable=False)
        plain_rows={r.code:r for p in plain.prefectures for r in p.locations}
        self.assertEqual(plain.files,1);self.assertEqual(plain_rows['11002'].states['7'],0)

    def test_prefecture_badges_require_every_master_unit(self):
        # With only one of three Kanagawa units worked there is no all-JCC/JCG badge.
        self.add('JH1HST','','2026-09-24','08:00','7','JA1AAA','110101','CARD.R')
        result=aggregate(self.repo,'JH1HST')
        kanagawa=next(p for p in result.prefectures if p.code=='11')
        self.assertEqual(kanagawa.badges(),[])

    def test_fix1_ui_source_uses_background_worker_and_lazy_children(self):
        text=(Path(__file__).with_name('jccjcg_award_check_ui.py')).read_text(encoding='utf-8')
        self.assertIn('QThread',text)
        self.assertIn('QProgressBar',text)
        self.assertIn('moveToThread',text)
        self.assertIn('ChildIndicatorPolicy.ShowIndicator',text)
        self.assertIn('itemExpanded.connect(self._populate_prefecture)',text)


try:
    import PySide6  # noqa: F401
    HAVE_QT=True
except Exception:
    HAVE_QT=False

@unittest.skipUnless(HAVE_QT,'PySide6 not installed')
class Patch041074GuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
        from PySide6.QtWidgets import QApplication
        cls.app=QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);ensure_logbook_directories(self.root);self.repo=Repository(self.root)
        p=self.repo.path_for('JH1HST','','2026-09-24');s=self.repo.open(p)
        s.append(QSO('2026-09-24','08:00','7','CW','JA1AAA','599','599','Japan','Soka Saitama Japan','','1102'))
        from search import search,Criteria
        self.hit=search(self.repo,Criteria(own='JH1HST')).hits[0]

    def test_edit_and_quick_qsl_button_order(self):
        from search_ui import EditDialog,QSLQuickDialog
        expected=['LoTW.R','hQSL.R','eQSL.R','BURO.R','QRZ.R','CARD.R','Other.R']
        edit=EditDialog(self.hit);self.assertEqual(list(edit.qsl_buttons),expected);edit.close()
        quick=QSLQuickDialog(self.repo,self.hit);self.assertEqual(list(quick.qsl_buttons),expected)
        quick.qsl_buttons['QRZ.R'].click();self.assertIn('QRZ.R',quick.hit.qso.remarks);self.assertTrue(quick.saved);quick.close()

    def test_search_has_separate_qsl_and_edit_buttons(self):
        from search_ui import SearchDialog
        d=SearchDialog(self.repo,'JH1HST',autorun=True)
        self.app.processEvents()
        self.assertEqual(d.qsl_button.text(),'QSL処理…');self.assertEqual(d.edit_button.text(),'交信を編集…')
        d.close()

    def test_award_tree_builds_prefecture_children_only_when_expanded(self):
        from jccjcg_award_check import AwardCheckResult,PrefectureStatus,LocationStatus,STATE_WORKED
        from jccjcg_award_check_ui import JccJcgAwardCheckDialog
        states={b:0 for b in ('7','14')};states['7']=STATE_WORKED;states['*']=STATE_WORKED
        loc=LocationStatus('JCC','1102','横須賀市','11','神奈川県',states)
        pref=PrefectureStatus('11','神奈川県',(loc,))
        result=AwardCheckResult('JH1HST',True,1,1,1,('7','14'),(pref,),())
        d=JccJcgAwardCheckDialog(self.repo,'JH1HST');d._render(result);d.result=result
        parent=d.tree.topLevelItem(0)
        self.assertEqual(parent.childCount(),0)
        parent.setExpanded(True);self.app.processEvents()
        self.assertEqual(parent.childCount(),1)
        self.assertEqual(parent.child(0).text(1),'1102')
        self.assertFalse(d.loading.isVisible())
        d.close()


if __name__=='__main__':unittest.main()
