import tempfile,unittest,csv,io
from pathlib import Path
from dataclasses import replace
from datetime import datetime
from unittest.mock import patch
import xml.etree.ElementTree as ET
from model import QSO
from storage import Repository,ExternalChange
from exporting import prepare,save,adif_fields,adif

class ExportTests(unittest.TestCase):
    def test_service_qsl_states_and_unknowns(self):
        cases={
            'LoTW':{},
            'LoTW.R':{'LOTW_QSL_SENT':'Y','LOTW_QSL_RCVD':'Y'},
            'eQSL':{'EQSL_QSL_SENT':'Y'},
            'eQSL.R':{'EQSL_QSL_SENT':'Y','EQSL_QSL_RCVD':'Y'},
            'hQSL.R QRZ.R Other.R':{},
            'XLoTW.R eQSL.Rsuffix memo/LoTW.R':{},
            '(lotw.r), EQSL':{'LOTW_QSL_SENT':'Y','LOTW_QSL_RCVD':'Y','EQSL_QSL_SENT':'Y'},
        }
        for remarks,expected in cases.items():
            with self.subTest(remarks=remarks):
                fields=adif_fields('JH1HST',replace(self.q,remarks=remarks),set())
                actual={k:v for k,v in fields.items() if 'QSL' in k}
                self.assertEqual(actual,expected)
                self.assertEqual(fields['COMMENT'],remarks)
    def test_qsl_adi_adx_and_original_unchanged(self):
        q=replace(self.q,remarks='LoTW.R eQSL.R CARD.R')
        self.repo.open(self.path).edit(1,q);raw=self.path.read_bytes()
        for fmt in ('adi','adx'):
            plan=prepare(self.repo,[self.path],fmt)
            if fmt=='adi':
                self.assertIn(b'<LOTW_QSL_RCVD:1>Y',plan.data)
                self.assertIn(b'<EQSL_QSL_SENT:1>Y',plan.data)
            else:
                record=ET.fromstring(plan.data).find('.//RECORD')
                self.assertEqual(record.findtext('LOTW_QSL_RCVD'),'Y')
                self.assertEqual(record.findtext('EQSL_QSL_SENT'),'Y')
                self.assertEqual(record.findtext('COMMENT'),q.remarks)
            self.assertEqual(self.path.read_bytes(),raw)
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.repo=Repository(self.tmp.name);self.q=QSO('2026-01-01','00:05','7','FT4','JA1YYY','-01','+00','PM95','Soka Saitama Japan','BURO','1101')
        self.path=self.repo.path_for('JH1HST/1','',self.q.date)
        self.repo.open(self.path).append(self.q)
    def test_utc_rollover_and_mode_and_no_invented_freq(self):
        raw=self.path.read_bytes();p=prepare(self.repo,[self.path]);s=p.data.decode()
        self.assertIn('<QSO_DATE:8>20251231',s);self.assertIn('<TIME_ON:6>150500',s)
        self.assertIn('<MODE:4>MFSK',s);self.assertIn('<SUBMODE:3>FT4',s);self.assertNotIn('<FREQ:',s)
        self.assertIn('<STATION_CALLSIGN:8>JH1HST/1',s);self.assertEqual(raw,self.path.read_bytes())
    def test_second_boundary_latest_and_ties(self):
        self.repo.open(self.path).append(replace(self.q,time='00:06',call='JA2YYY'))
        self.repo.open(self.path).append(replace(self.q,time='00:06',call='JA3YYY'))
        p=prepare(self.repo,[self.path],start='20260101000501',end='20260101000600',latest=1)
        self.assertEqual(p.rows[0][1].call,'JA3YYY')
        with self.assertRaises(ValueError):prepare(self.repo,[self.path],start='20260230000000')
    def test_adx_unicode_and_xml_escape(self):
        self.repo.open(self.path).edit(1,replace(self.q,remarks='日本語 < & >',my_qth='草加'))
        with self.assertRaises(ValueError):prepare(self.repo,[self.path],'adi')
        p=prepare(self.repo,[self.path],'adx');root=ET.fromstring(p.data)
        self.assertEqual(root.find('.//COMMENT_INTL').text,'日本語 < & >')
        self.assertEqual(root.find('.//APP[@FIELDNAME="MY_QTH"]').text,'草加')
    def test_csv_quoting_width_and_encoding(self):
        q=replace(self.q,remarks='BURO, "memo"');self.repo.open(self.path).edit(1,q)
        p=prepare(self.repo,[self.path],'csv');rows=list(csv.reader(io.StringIO(p.data.decode('cp932'))))
        self.assertEqual(len(rows[0]),15);self.assertEqual(rows[0][12],q.remarks);self.assertEqual(rows[0][2],'00:05J')
        self.assertIn(q.my_qth,rows[0][13]);self.assertEqual(rows[0][9],'B* ')
        self.repo.open(self.path).edit(1,replace(q,remarks='x'*255))
        with self.assertRaises(ValueError):prepare(self.repo,[self.path],'csv')
    def test_new_name_and_stale_source(self):
        p=prepare(self.repo,[self.path])
        with patch('exporting.datetime') as clock:
            clock.now.return_value=datetime(2026,9,11,12,0)
            a=save(p,self.tmp.name);b=save(p,self.tmp.name)
        self.assertNotEqual(a,b);self.assertEqual(a.read_bytes(),p.data);self.assertEqual(b.read_bytes(),p.data)
        self.path.write_bytes(self.path.read_bytes()+b'\n')
        with self.assertRaises(ExternalChange):save(p,self.tmp.name)
    def test_unknown_mode_export_does_not_change_source(self):
        self.repo.open(self.path).edit(1,replace(self.q,mode='FUTUREMODE'));raw=self.path.read_bytes()
        with self.assertRaises(ValueError):prepare(self.repo,[self.path])
        self.assertEqual(self.path.read_bytes(),raw)
