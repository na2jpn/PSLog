import csv, io, shutil, tempfile, unittest
from pathlib import Path

from model import QSO
from storage import Repository, VERSION
from exporting import hamlog
from jccjcg_batch import (collect,commit,qth_from_code,MODE_CODE_TO_QTH,MODE_RMKS_TO_BOTH,MODE_QTH_TO_CODE,MODE_MISMATCH)


class Patch021061Tests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.root=Path(self.t.name)
        (self.root/'config/db').mkdir(parents=True);(self.root/'logbook').mkdir();(self.root/'bak').mkdir()
        source=Path(__file__).parent/'config/db/locations.json';shutil.copy2(source,self.root/'config/db/locations.json')
        self.repo=Repository(self.root);self.path=self.root/'logbook/2026_JH1HST_.txt'
    def tearDown(self):self.t.cleanup()
    def write(self,qsos):
        body='\r\n'.join(q.to_ps() for q in qsos)+'\r\n';self.path.write_bytes(b'\xef\xbb\xbf'+body.encode())
    def q(self,his='Japan',code='',remarks=''):
        return QSO('2026-09-09','12:00','430','FM','JA1AAA','59','59',his,'Soka Saitama Japan',remarks,code)
    def test_hamlog_can_leave_both_remarks_blank(self):
        q=self.q(remarks='ONE <<RMKS2>> TWO')
        data,_=hamlog([('JH1HST',q,self.path,1)],{'rmks1':'出力しない','rmks2':'出力しない','hamlog_identity':False})
        row=next(csv.reader(io.StringIO(data.decode('cp932'))))
        self.assertEqual(row[12],'');self.assertEqual(row[13],'')
    def test_hamlog_identity_default_is_backward_compatible(self):
        q=self.q()
        data,_=hamlog([('JH1HST',q,self.path,1)],{'rmks1':'出力しない','rmks2':'出力しない'})
        row=next(csv.reader(io.StringIO(data.decode('cp932'))));self.assertIn('MYCALL:JH1HST',row[13])
    def test_code_to_qth_and_partial_day(self):
        self.write([self.q(code='1321')])
        rows=collect(self.repo,[self.path],'JH1HST',MODE_CODE_TO_QTH,'20260909','20260909')
        self.assertEqual(len(rows),1);self.assertEqual(rows[0].proposal().his_qth,'Soka Saitama Japan')
    def test_rmks_to_both_only_treats_whole_rmks_as_code(self):
        self.write([self.q(remarks='16001H'),self.q(remarks='16001H 05HW')])
        rows=collect(self.repo,[self.path],'JH1HST',MODE_RMKS_TO_BOTH)
        self.assertEqual(len(rows),1);after=rows[0].proposal();self.assertEqual(after.code,'16001H');self.assertIn('Nakanojo',after.his_qth)
    def test_qth_to_code(self):
        self.write([self.q(his='Soka Saitama Japan')])
        rows=collect(self.repo,[self.path],'JH1HST',MODE_QTH_TO_CODE)
        self.assertEqual(len(rows),1);self.assertEqual(rows[0].proposal().code,'1321')
    def test_mismatch_offers_both_directions_and_commit_backs_up(self):
        self.write([self.q(his='Soka Saitama Japan',code='100107')])
        rows=collect(self.repo,[self.path],'JH1HST',MODE_MISMATCH)
        self.assertEqual(len(rows),1);c=rows[0];self.assertTrue(c.can_adopt_his_qth);self.assertTrue(c.can_adopt_jccjcg)
        self.assertEqual(c.proposal('his_qth').code,'1321');self.assertIn('Sumida',c.proposal('jccjcg').his_qth)
        count,files=commit(self.repo,[(c,'his_qth')]);self.assertEqual((count,files),(1,1));self.assertTrue(list((self.root/'bak').glob('*.bak')))
        self.assertEqual(self.repo.open(self.path).log.records[0][1].code,'1321')
    def test_bare_jcg_resolves_to_county_without_guessing_municipality(self):
        self.assertEqual(qth_from_code(self.root,'16001'),'Agatsumagun Gumma Japan')
        self.assertEqual(qth_from_code(self.root,'16001H'),'Nakanojo Agatsumagun Gumma Japan')
    def test_batch_recovery_accepts_jccjcg_kind(self):
        from storage import Snapshot
        from batch_recovery import create,recover_locked
        self.write([self.q(code='1321')])
        snap=Snapshot.read(self.path)
        before=self.path.read_bytes();after=before.replace(b'Japan',b'Soka Saitama Japan',1)
        intent=create(self.repo,'jccjcg',[(self.path,snap,after)],{})
        recover_locked(self.repo.book)
        self.assertEqual(self.path.read_bytes(),after);self.assertFalse(intent.path.exists())

    def test_ui_sources_use_common_version_and_batch_menu(self):
        root=Path(__file__).parent
        for name in ('blacklist_ui.py','pota_ui.py','qsl_ui.py','search_ui.py','sota_ui.py'):
            text=(root/name).read_text(encoding='utf-8');self.assertNotIn('PSLog 1.00 —',text,name);self.assertIn('VERSION',text,name)
        main=(root/'main.py').read_text(encoding='utf-8');self.assertIn("'ログ一括処理'",main);self.assertIn("addAction('JCC/JCG…')",main)
        contest=(root/'contest_ui.py').read_text(encoding='utf-8');self.assertIn('source_form=QWidget()',contest);self.assertIn('AlignTop',contest)
        search=(root/'search_ui.py').read_text(encoding='utf-8');self.assertIn("button('HIS QTHへ反映'",search)

if __name__=='__main__':unittest.main()
