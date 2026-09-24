import tempfile,unittest
from pathlib import Path
from storage import Repository,VERSION,parse
from free_radio import *
from free_search import FreeCriteria,free_search
from session_state import free_session,restore,MAX_FREE,session_title

class FreeRadio111Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.repo=Repository(self.root);self.repo.book.mkdir();self.repo.free_book.mkdir();self.repo.bak.mkdir()
    def tearDown(self):self.tmp.cleanup()
    def test_version_and_mapping(self):
        self.assertEqual(VERSION,'1.14')
        self.assertEqual(radio_values('CB'),('27','AM'))
        self.assertEqual(radio_values('DCR'),('351','DIGITAL'))
        self.assertEqual(radio_values('LCR'),('142/146','DIGITAL'))
        self.assertEqual(radio_values('BLU'),('2400','DIGITAL'))
        self.assertEqual(radio_values('ETC'),('N/A','N/A'))
    def test_free_call_kana_conversion_and_kanji_rejection(self):
        self.assertEqual(validate_free_call('サイタマab123'),'さいたまAB123')
        self.assertEqual(validate_free_call('ｻｲﾀﾏab123'),'さいたまAB123')
        with self.assertRaises(ValueError):validate_free_call('埼玉AB123')
    def test_model_name_is_optional(self):
        self.assertEqual(validate_model(''),'')
        path=ensure_free_logbook(self.repo,'さいたまAB123','DCR','','2026-09-25')
        self.assertEqual(path.name,'2026_さいたまAB123_DCR.txt')
        self.assertEqual(free_file_identity(path),('2026','さいたまAB123','DCR',''))
        self.assertEqual(free_models(self.repo,'DCR'),[])
        profiles=free_profiles(self.repo)
        self.assertEqual(profiles[0]['model'],'')
        ensure_free_logbook(self.repo,'さいたまAB123','DCR','IC-DPR7S','2026-09-25')
        blank_only=free_files(self.repo,call='さいたまAB123',kind='DCR',model='')
        self.assertEqual([p.name for p in blank_only],['2026_さいたまAB123_DCR.txt'])

    def test_log_identity_and_unicode_qso(self):
        path=ensure_free_logbook(self.repo,'さいたまAB123','DCR','IC-DPR7S','2026-09-25')
        self.assertEqual(free_file_identity(path),('2026','さいたまAB123','DCR','IC-DPR7S'))
        q=FreeQSO('2026-09-25','00:10','351','DIGITAL','とうきょうCD456','59','59','Tokyo','Saitama','','100101')
        session=self.repo.open(path);session.append(q)
        log=parse(path.read_bytes());self.assertEqual(log.records[0][1].call,'とうきょうCD456')
    def test_cross_kind_search(self):
        for kind,model in [('DCR','A'),('LCR','B')]:
            path=ensure_free_logbook(self.repo,'さいたまAB123',kind,model,'2026-09-25');band,mode=radio_values(kind)
            self.repo.open(path).append(FreeQSO('2026-09-25','00:10',band,mode,'とうきょうCD456','59','59','','','',''))
        result=free_search(self.repo,FreeCriteria('さいたまAB123',call='とうきょうCD456'))
        self.assertEqual({h.free_kind for h in result.hits},{'DCR','LCR'})
        self.assertEqual(len(result.hits),2)
    def test_free_cross_year_edit_uses_free_book(self):
        path=ensure_free_logbook(self.repo,'さいたまAB123','DCR','RADIO','2026-12-31')
        session=self.repo.open(path);session.append(FreeQSO('2026-12-31','23:59','351','DIGITAL','とうきょうCD456','59','59','','','',''))
        session.edit(1,FreeQSO('2027-01-01','00:01','351','DIGITAL','とうきょうCD456','59','59','','','',''))
        target=self.repo.free_book/'2027_さいたまAB123_DCR_RADIO.txt'
        self.assertTrue(target.exists());self.assertEqual(len(parse(target.read_bytes()).records),1)
        self.assertEqual(len(parse(path.read_bytes()).records),0)

    def test_full_backup_contains_free_radio_log(self):
        import zipfile
        from full_backup import create
        path=ensure_free_logbook(self.repo,'さいたまAB123','DCR','RADIO','2026-09-25')
        self.repo.open(path).append(FreeQSO('2026-09-25','00:10','351','DIGITAL','とうきょうCD456','59','59','','','',''))
        out=self.root.parent/'free111-backup.zip'
        try:
            create(self.repo,out)
            with zipfile.ZipFile(out) as z:self.assertIn('logbook_flr/'+path.name,z.namelist())
        finally:
            out.unlink(missing_ok=True)

    def test_free_session_limit_restores_four(self):
        raw=[free_session(i+1,f'さいたまAB12{i}','DCR',f'M{i}') for i in range(5)]
        sessions,_,_=restore({'workspace_sessions':raw})
        self.assertEqual(sum(s['type']=='free' for s in sessions),MAX_FREE)
        self.assertTrue(session_title(sessions[0]).startswith('[F]'))

if __name__=='__main__':unittest.main()
