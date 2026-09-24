import unittest
import xml.etree.ElementTree as ET
from adif_import import convert
from test_adif_import import adi,BASE


class AdifNameTests(unittest.TestCase):
    def test_name_is_contacted_name_not_our_operator(self):
        f=BASE|{'NAME':'Taro','OPERATOR':'JA9ZZZ','MY_NAME':'My name','CONTACTED_OP':'JA2YYY','COMMENT':'1101H BURO'}
        log,_=convert(adi(**f),'adi','JH1HST/1')
        self.assertFalse(log.issues)
        remarks=log.records[0][1].remarks
        self.assertTrue(remarks.startswith('1101H BURO OP:Taro '))
        self.assertNotIn('OP:JA9ZZZ',remarks)
        self.assertIn('"NAME":"Taro"',remarks)
        self.assertIn('"CONTACTED_OP":"JA2YYY"',remarks)

    def test_existing_op_preserved(self):
        for comment in ('OP:Hanako memo','op:Taro'):
            log,_=convert(adi(**(BASE|{'NAME':'Taro','COMMENT':comment})),'adi','JH1HST/1')
            remarks=log.records[0][1].remarks
            self.assertTrue(remarks.startswith(comment))
            self.assertEqual(remarks.lower().count('op:'),1)
            self.assertTrue(any('RMKSにOP:' in n.reason for n in log.notices))

    def test_intl_name_priority_and_structural_cleanup(self):
        root=ET.Element('ADX');record=ET.SubElement(ET.SubElement(root,'RECORDS'),'RECORD')
        for k,v in (BASE|{'NAME':'Taro','NAME_INTL':'太郎|山田','COMMENT_INTL':'メモ'}).items():
            ET.SubElement(record,k).text=v
        log,_=convert(ET.tostring(root),'adx','JH1HST/1')
        self.assertFalse(log.issues)
        self.assertTrue(log.records[0][1].remarks.startswith('メモ OP:太郎｜山田 '))

    def test_operator_fallback_checks_own_callsign(self):
        f=BASE.copy();del f['STATION_CALLSIGN'];f['OPERATOR']='JA9ZZZ'
        log,_=convert(adi(**f),'adi','JH1HST/1')
        self.assertEqual(len(log.issues),1)
        log,_=convert(adi(**f),'adi','JH1HST/1',True)
        self.assertFalse(log.issues)
        self.assertIn('"OPERATOR":"JA9ZZZ"',log.records[0][1].remarks)
        f['OPERATOR']='JH1HST/1'
        log,_=convert(adi(**f),'adi','JH1HST/1')
        self.assertFalse(log.issues)
