import unittest
from radio_control import band_for_frequency_hz,frequency_text,append_frequency,preferred_virtual_com,parse_civ_frequency

class RadioControlTests(unittest.TestCase):
    def test_frequency_display_and_band(self):
        self.assertEqual(frequency_text(7012000),'7.012')
        self.assertEqual(band_for_frequency_hz(7012000),'7')
        self.assertEqual(band_for_frequency_hz(14074000),'14')
        self.assertEqual(band_for_frequency_hz(1295000000),'1200')
    def test_rmks_append_has_trailing_space_and_no_duplicate(self):
        self.assertEqual(append_frequency('',7012000),'7.012 ')
        self.assertEqual(append_frequency('POTA',7012000),'POTA 7.012 ')
        self.assertEqual(append_frequency('POTA 7.012 ',7012000),'POTA 7.012 ')
    def test_virtual_number_plus_100_on_conflict(self):
        self.assertEqual(preferred_virtual_com('COM8',set()),208)
        self.assertEqual(preferred_virtual_com('COM8',{208}),308)
        self.assertEqual(preferred_virtual_com('COM8',{208,308}),408)
    def test_civ_frequency(self):
        # 7,012,000 Hz -> little-endian BCD 00 20 01 07 00
        frame=bytes.fromhex('FE FE E1 94 03 00 20 01 07 00 FD')
        self.assertEqual(parse_civ_frequency(frame),7012000.0)

if __name__=='__main__':unittest.main()
