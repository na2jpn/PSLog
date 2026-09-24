import unittest
from adif_paper_qsl import fields
from exporting import adif
from model import QSO
import xml.etree.ElementTree as ET


class PaperQslTests(unittest.TestCase):
    def test_receipt_does_not_prove_sent(self):
        for mark,via in [('BURO.R','B'),('CARD.R',''),('1way.R',''),('Direct.R','D')]:
            with self.subTest(mark=mark):
                expected={'QSL_RCVD':'Y'}
                if via:expected['QSL_RCVD_VIA']=via
                self.assertEqual(fields(mark,set()),expected)

    def test_sent_and_requests_are_distinct(self):
        for mark in ('CARD','my1way','MY1WAY'):
            self.assertEqual(fields(mark,set()),{'QSL_SENT':'Y'})
        self.assertEqual(fields('BURO',set()),{'QSL_SENT':'Y','QSL_SENT_VIA':'B'})
        for mark in ('Direct','1way','LoTW.R eQSL.R hQSL.R QRZ.R','XBURO.R','my1way.R'):
            self.assertEqual(fields(mark,set()),{})

    def test_multiple_routes_and_supplemental_card(self):
        warnings=set()
        f=fields('BURO.R Direct.R CARD.R',warnings)
        self.assertEqual(f,{'QSL_RCVD':'Y'});self.assertTrue(warnings)
        self.assertEqual(fields('Direct.R CARD.R',set()),{'QSL_RCVD':'Y','QSL_RCVD_VIA':'D'})
        self.assertEqual(fields('CARD CARD.R',set()),{'QSL_SENT':'Y','QSL_RCVD':'Y'})

    def test_adi_adx_keep_comment_and_service_separation(self):
        q=QSO('2026-09-11','12:00','7','SSB','JA1YYY','59','59','Japan','Japan','BURO.R LoTW.R','')
        rows=[('JH1HST',q,None,1)]
        data,_=adif(rows)
        self.assertIn(b'<QSL_RCVD:1>Y',data)
        self.assertNotIn(b'<QSL_SENT:',data)
        data,_=adif(rows,True);r=ET.fromstring(data).find('.//RECORD')
        self.assertEqual(r.findtext('COMMENT'),q.remarks)
        self.assertEqual(r.findtext('LOTW_QSL_SENT'),'Y')
        self.assertEqual(r.findtext('QSL_RCVD_VIA'),'B')
        self.assertIsNone(r.find('QSL_SENT'))
