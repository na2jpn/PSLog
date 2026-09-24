import unittest
from adif_paper_qsl import import_marks,fields
from adif_import import convert
from exporting import adif
from test_adif_import import adi,BASE


class BureauImportTests(unittest.TestCase):
    def test_both_states_preserved_roundtrip(self):
        source={'QSL_SENT':'Y','QSL_SENT_VIA':'B','QSL_RCVD':'Y','QSL_RCVD_VIA':'B'}
        remarks,notices=import_marks(source,'memo CARD.R')
        self.assertEqual(remarks,'memo CARD.R BURO BURO.R')
        self.assertEqual(fields(remarks,set()),source)
        self.assertEqual(import_marks(source,remarks),(remarks,[]))
        log,_=convert(adi(**(BASE|source)),'adi','JH1HST/1')
        for adx in (False,True):
            data,_=adif([('JH1HST/1',log.records[0][1],None,1)],adx)
            again,_=convert(data,'adx' if adx else 'adi','JH1HST/1')
            self.assertFalse(again.issues)
            self.assertEqual(fields(again.records[0][1].remarks,set()),source)

    def test_receipt_without_sending_warns(self):
        source={'QSL_RCVD':'Y','QSL_RCVD_VIA':'b'}
        remarks,notices=import_marks(source,'LoTW.R')
        self.assertEqual(remarks,'LoTW.R BURO.R')
        self.assertTrue(any('返送' in x for x in notices))
        self.assertNotIn('QSL_SENT',fields(remarks,set()))

    def test_unknown_direct_or_electronic_not_guessed(self):
        for route in ('D','E','M','','?'):
            source={'QSL_RCVD':'Y','QSL_RCVD_VIA':route}
            remarks,notices=import_marks(source,'memo')
            self.assertEqual(remarks,'memo');self.assertTrue(notices)
        source={'QSL_SENT':'Y','QSL_SENT_VIA':'B'}
        self.assertEqual(import_marks(source,'')[0],'BURO')

    def test_conflict_keeps_original_and_evidence(self):
        source=BASE|{'COMMENT':'BURO.R','QSL_RCVD':'N','QSL_RCVD_VIA':'B'}
        log,_=convert(adi(**source),'adi','JH1HST/1')
        self.assertFalse(log.issues)
        self.assertTrue(log.records[0][1].remarks.startswith('BURO.R'))
        self.assertIn('"QSL_RCVD":"N"',log.records[0][1].remarks)
        self.assertTrue(any('矛盾' in n.reason for n in log.notices))
