import unittest
import xml.etree.ElementTree as ET
from adif_qsl import import_marks
from adif_import import convert
from test_adif_import import adi,BASE
from exporting import adif
from qsl_marks import tokens


class AdifQslTests(unittest.TestCase):
    def test_confirmed_services_replace_waiting_preserve_notes(self):
        f={'LOTW_QSL_SENT':'Y','LOTW_QSL_RCVD':'Y','EQSL_QSL_SENT':'y','EQSL_QSL_RCVD':'y'}
        remarks,notices=import_marks(f,'LoTW eQSL 1101H CARD.R')
        self.assertEqual(remarks,'LoTW.R eQSL.R 1101H CARD.R')
        self.assertEqual(len(notices),2)
        self.assertEqual(import_marks(f,remarks),(remarks,[]))

    def test_incomplete_and_other_methods_not_confirmed(self):
        for service in ('LOTW','EQSL'):
            for state in ('Y','V','I','N','R','unexpected'):
                with self.subTest(service=service,state=state):
                    remarks,notices=import_marks({service+'_QSL_RCVD':state},'memo')
                    self.assertEqual(remarks,'memo')
                    self.assertTrue(notices)
        self.assertEqual(import_marks({'QSL_RCVD':'Y','QSL_SENT':'Y'},'memo'),('memo',[]))
        self.assertEqual(import_marks({'LOTW_QSL_SENT':'Y'},'memo')[0],'memo')
        self.assertEqual(import_marks({'EQSL_QSL_SENT':'Y'},'memo')[0],'memo eQSL')

    def test_conflicting_handwritten_status_preserved_and_reported(self):
        for service in ('LoTW','eQSL'):
            original=service+'.R memo'
            remarks,notices=import_marks({service.upper()+'_QSL_RCVD':'N'},original)
            self.assertEqual(remarks,original)
            self.assertIn('一致しません',notices[0])

    def test_adi_and_adx_import_preserve_evidence_and_roundtrip(self):
        fields=BASE|{'TIME_ON':'150500','COMMENT':'1101H hQSL.R',
                     'LOTW_QSL_SENT':'Y','LOTW_QSL_RCVD':'Y','LOTW_QSLRDATE':'20260102',
                     'EQSL_QSL_SENT':'Y','EQSL_QSL_RCVD':'N'}
        root=ET.Element('ADX');record=ET.SubElement(ET.SubElement(root,'RECORDS'),'RECORD')
        for k,v in fields.items():ET.SubElement(record,k).text=v
        for kind,data in [('adi',adi(**fields)),('adx',ET.tostring(root))]:
            with self.subTest(kind=kind):
                log,_=convert(data,kind,'JH1HST/1')
                self.assertFalse(log.issues)
                q=log.records[0][1]
                self.assertEqual(tokens(q.remarks),{'hqsl.r','lotw.r','eqsl'})
                self.assertIn('"LOTW_QSLRDATE":"20260102"',q.remarks)
                self.assertIn('"EQSL_QSL_RCVD":"N"',q.remarks)
                exported,_=adif([('JH1HST/1',q,None,1)],adx=kind=='adx')
                reread,_=convert(exported,kind,'JH1HST/1')
                self.assertEqual(tokens(reread.records[0][1].remarks),tokens(q.remarks))
