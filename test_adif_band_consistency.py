import unittest
import xml.etree.ElementTree as ET
from adif_import import convert
from test_adif_import import adi,BASE


class AdifBandConsistencyTests(unittest.TestCase):
    def test_matching_actual_frequency_preserved(self):
        for band,freq,expected in [('40m','7.074','7'),('70cm','433.0','430'),('160m','1.910','1.8')]:
            log,_=convert(adi(**(BASE|{'BAND':band,'FREQ':freq})),'adi','JH1HST/1')
            self.assertFalse(log.issues)
            q=log.records[0][1]
            self.assertEqual(q.band,expected)
            self.assertIn('"FREQ":"'+freq+'"',q.remarks)

    def test_conflicting_band_is_not_silently_preferred(self):
        fields=BASE|{'FREQ':'14.074'}
        root=ET.Element('ADX');record=ET.SubElement(ET.SubElement(root,'RECORDS'),'RECORD')
        for k,v in fields.items():ET.SubElement(record,k).text=v
        for kind,data in [('adi',adi(**fields)),('adx',ET.tostring(root))]:
            log,_=convert(data,kind,'JH1HST/1')
            self.assertEqual(len(log.issues),1)
            self.assertFalse(log.records)
            self.assertIn('BANDとFREQが一致しません',log.issues[0].reason)

    def test_invalid_frequency_is_checked_even_with_band(self):
        for freq in ('bad','NaN','Infinity','-7','0','999999'):
            with self.subTest(freq=freq):
                log,_=convert(adi(**(BASE|{'FREQ':freq})),'adi','JH1HST/1')
                self.assertEqual(len(log.issues),1)
                self.assertFalse(log.records)

    def test_band_only_and_frequency_only_still_work(self):
        for fields in (BASE,BASE|{'BAND':'','FREQ':'7.074'}):
            log,_=convert(adi(**fields),'adi','JH1HST/1')
            self.assertFalse(log.issues)
            self.assertEqual(log.records[0][1].band,'7')
