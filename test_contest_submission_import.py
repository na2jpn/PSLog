import unittest
from contest_submission_import import parse_jarl, scores_equal

RULE={'id':'demo','event':{'regional':{},'categories':[{'id':'K1','timing':{}}]}}
CTX={'category':'K1'}

class SubmissionImportTests(unittest.TestCase):
    def test_parse_r10_standard(self):
        text='''<SUMMARYSHEET VERSION=R1.0>\r\n<CONTESTNAME>TEST</CONTESTNAME>\r\n<CATEGORYCODE>K1</CATEGORYCODE>\r\n<CATEGORYNAME>電信</CATEGORYNAME>\r\n<CALLSIGN>JH1HST/0</CALLSIGN>\r\n<TOTALSCORE>65</TOTALSCORE>\r\n<ADDRESS>埼玉</ADDRESS>\r\n<NAME>田中</NAME>\r\n<POWER>5</POWER>\r\n<LICENSECLASS>第2級アマチュア無線技士</LICENSECLASS>\r\n<REGCLUBNUMBER>10-123</REGCLUBNUMBER>\r\n<REGCLUBNAME>TEST CLUB</REGCLUBNAME>\r\n<OATH>確認</OATH>\r\n<DATE>2026年09月17日</DATE>\r\n<SIGNATURE>田中</SIGNATURE>\r\n</SUMMARYSHEET>\r\n<LOGSHEET TYPE="PSLog">\r\nDATE (JST) TIME BAND MODE CALLSIGN SENTNo RCVDNo Mlt Pts\r\n2026-09-12 22:17 1200 SSB JR1UIE/1 59 09009 59 13008 13008 1\r\n</LOGSHEET>\r\n'''.encode('cp932')
        p=parse_jarl(text,RULE,CTX)
        self.assertEqual(p.format,'JARL R1.0')
        self.assertEqual(p.info['callsign'],'JH1HST/0')
        self.assertEqual(p.info['date'],'2026-09-17')
        self.assertTrue(p.info['oath'])
        self.assertEqual(p.rows[0].received,'13008')
        self.assertEqual(p.total_score,'65')

    def test_parse_r21_utc_and_checklog(self):
        text='''<SUMMARYSHEET VERSION=R2.1>\n<CONTESTNAME>TEST</CONTESTNAME>\n<CATEGORYCODE>K1</CATEGORYCODE>\n<CALLSIGN>JH1HST</CALLSIGN>\n<TOTALSCORE>1</TOTALSCORE>\n<ADDRESS>A</ADDRESS>\n<NAME>N</NAME>\n<POWER>1</POWER>\n<OATH>O</OATH>\n<DATE>2026年09月17日</DATE>\n<SIGNATURE>S</SIGNATURE>\n</SUMMARYSHEET>\n<LOGSHEET TYPE="PSLog">\nDATE (UTC) TIME BAND MODE CALLSIGN SENTNo RCVDNo Mlt Pts\nX 2026-09-12 13:17 1200 FM JR1UIE/1 59 09009 59 13008 13008 1\n</LOGSHEET>'''.encode('cp932')
        p=parse_jarl(text,RULE,CTX)
        self.assertEqual(p.zone,'UTC')
        self.assertTrue(p.rows[0].checklog)

    def test_score_compare(self):
        self.assertTrue(scores_equal('65','65.0'))
        self.assertFalse(scores_equal('64',65))

if __name__=='__main__': unittest.main()

class SubmissionMatchTests(unittest.TestCase):
    def test_match_back_to_master_log(self):
        import tempfile
        from pathlib import Path
        from storage import Repository
        from model import QSO
        from contest_submission_import import match_to_pslog
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'logbook').mkdir()
            q=QSO('2026-09-12','22:17','1200','SSB','JR1UIE/1','59','59','Japan','Saitama','13008','')
            path=root/'logbook'/'2026_JH1HST_.txt'
            path.write_bytes(b'\xef\xbb\xbf'+(q.to_ps()+'\r\n').encode('utf-8'))
            repo=Repository(root)
            text='''<SUMMARYSHEET VERSION=R1.0>\n<CONTESTNAME>TEST</CONTESTNAME>\n<CATEGORYCODE>K1</CATEGORYCODE>\n<CALLSIGN>JH1HST/0</CALLSIGN>\n<TOTALSCORE>1</TOTALSCORE>\n<ADDRESS>A</ADDRESS>\n<NAME>N</NAME>\n<POWER>1</POWER>\n<LICENSECLASS>第2級アマチュア無線技士</LICENSECLASS>\n<OATH>O</OATH>\n<DATE>2026年09月17日</DATE>\n<SIGNATURE>S</SIGNATURE>\n</SUMMARYSHEET>\n<LOGSHEET TYPE="PSLog">\nDATE (JST) TIME BAND MODE CALLSIGN SENTNo RCVDNo Mlt Pts\n2026-09-12 22:17 1200 SSB JR1UIE/1 59 09009 59 13008 13008 1\n</LOGSHEET>'''.encode('cp932')
            parsed=parse_jarl(text,RULE,CTX)
            selection,draft=match_to_pslog(repo,parsed,RULE,CTX)
            self.assertEqual(len(selection.rows),1)
            d=draft[(str(path.resolve()),1)]
            self.assertEqual(d['sent'],'09009')
            self.assertEqual(d['received'],'13008')
            self.assertEqual(d['status'],'確認済み')
