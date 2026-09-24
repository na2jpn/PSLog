import unittest,tempfile,json
from pathlib import Path
from storage import Repository,InvalidLog,StorageError
from importing import prepare,commit
from adif_import import read_adi,read_adx,convert
from exporting import prepare as export

def adi(**fields):return (''.join(f'<{k}:{len(v)}>{v}' for k,v in fields.items())+'<EOR>').encode()
BASE=dict(QSO_DATE='20251231',TIME_ON='150512',CALL='JA1YYY',BAND='40m',MODE='MFSK',SUBMODE='FT4',RST_SENT='00',RST_RCVD='-01',STATION_CALLSIGN='JH1HST/1')
class AdifTests(unittest.TestCase):
    def test_utc_year_seconds_and_zero(self):
        log,_=convert(adi(**BASE),'adi','JH1HST/1');q=log.records[0][1]
        self.assertEqual((q.date,q.time,q.mode,q.sent),('2026-01-01','00:05','FT4','+00'))
        self.assertIn('150512UTC',q.remarks)
    def test_header_lengths_and_embedded_eor(self):
        data=b'Generated\n<ADIF_VER:5>3.1.4<EOH>'+adi(**(BASE|{'COMMENT':'abc <EOR> z'}))
        self.assertEqual(read_adi(data)[0]['COMMENT'],'abc <EOR> z')
        for malformed in (data[:-5],b'<CALL:999>abc',b'<CALL:1>A<CALL:1>B<EOR>'):
            with self.assertRaises(InvalidLog):read_adi(malformed)
    def test_adx_unicode_app_and_entities(self):
        data=b'<ADX><RECORDS><RECORD><CALL>JA1YYY</CALL><COMMENT_INTL>A &amp; B</COMMENT_INTL><APP PROGRAMID="PSLOG" FIELDNAME="MY_QTH" TYPE="I">Japan</APP></RECORD></RECORDS></ADX>'
        f=read_adx(data)[0];self.assertEqual(f['COMMENT_INTL'],'A & B');self.assertEqual(f['APP_PSLOG_MY_QTH'],'Japan')
        with self.assertRaises(InvalidLog):read_adx(b'<!DOCTYPE ADX [<!ENTITY x "abc">]>'+data)
    def test_mismatch_override_and_unknown_mode(self):
        log,_=convert(adi(**BASE),'adi','JH1HST');self.assertEqual(len(log.issues),1)
        log,_=convert(adi(**(BASE|{'MODE':'FUTURE','SUBMODE':''})),'adi','JH1HST',True)
        self.assertEqual(log.records[0][1].mode,'FUTURE');self.assertIn('JH1HST/1',log.records[0][1].remarks)
    def test_freq_and_unmapped_fields_preserved(self):
        f=BASE|{'BAND':'','FREQ':'7.074','NAME':'Taro','LOTW_QSL_RCVD':'Y'}
        log,_=convert(adi(**f),'adi','JH1HST/1');q=log.records[0][1]
        self.assertEqual(q.band,'7');self.assertIn('7.074',q.remarks);self.assertIn('LOTW_QSL_RCVD',q.remarks)
    def test_missing_date_invalid_clock_and_structural_cleanup(self):
        for f in (BASE|{'TIME_ON':'246000'},BASE|{'QSO_DATE':'20250230'},BASE|{'CALL':''}):
            log,_=convert(adi(**f),'adi','JH1HST/1');self.assertEqual(len(log.issues),1)
        log,_=convert(adi(**(BASE|{'COMMENT':'a|b\nc'})),'adi','JH1HST/1')
        self.assertEqual(log.records[0][1].remarks.split(' ADIF_TIME')[0],'a｜b\\nc')
    def test_import_commit_and_roundtrip_adx(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'data.adi';source.write_bytes(adi(**BASE));raw=source.read_bytes();repo=Repository(root/'app')
            p=prepare(repo,source,'JH1HST/1')
            with self.assertRaises(StorageError):commit(repo,p)
            report,saved=commit(repo,p,conversions_confirmed=True)
            self.assertEqual(source.read_bytes(),raw);self.assertEqual(saved[0].name,'2026_JH1HST-1_.txt')
            self.assertEqual(json.loads(report.read_text(encoding='utf-8'))['import_metadata']['records'][0]['TIME_ON'],'150512')
            exported=export(repo,saved,'adx');target=root/'out.adx';target.write_bytes(exported.data)
            p=prepare(Repository(root/'second'),target,'JH1HST/1');self.assertEqual(len(p.log.records),1)
            self.assertEqual(p.log.records[0][1].date,'2026-01-01')
