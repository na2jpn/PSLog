import unittest

from input_normalization import callsign, date_text, machine_text, time_text
from model import QSO, validate_station


class InputNormalizationTests(unittest.TestCase):
    def test_date_variants(self):
        for source in ('20260909','2026/09/09','2026/9/9','2026-9-9','2026年9月9日','２０２６／９／９'):
            with self.subTest(source=source):
                self.assertEqual(date_text(source),'2026-09-09')

    def test_invalid_date_is_not_guessed(self):
        for source in ('2026/2/30','202609','09/09'):
            with self.subTest(source=source):
                with self.assertRaises(ValueError):date_text(source)

    def test_time_variants(self):
        cases={'1515':'15:15','915':'09:15','15:15':'15:15','1:1':'01:01','１：１':'01:01','15時15分':'15:15','１５時１５分':'15:15','9:5':'09:05'}
        for source,expected in cases.items():
            with self.subTest(source=source):self.assertEqual(time_text(source),expected)

    def test_two_digit_time_is_deliberately_ambiguous(self):
        with self.assertRaises(ValueError):time_text('15')

    def test_machine_fields_convert_fullwidth_ascii_but_keep_japanese(self):
        self.assertEqual(callsign('ｊｈ１ｈｓｔ／１'),'JH1HST/1')
        self.assertEqual(machine_text('ＦＴ８',upper=True),'FT8')
        self.assertEqual(machine_text('－０１'),'-01')
        self.assertEqual(machine_text('Ａ１２東京',upper=True),'A12東京')


    def test_station_and_qso_machine_fields_normalize_on_validation(self):
        self.assertEqual(validate_station('ＪＨ１ＨＳＴ／Ｐ','日本語付与文字'),'JH1HST/P')
        q=QSO('２０２６／９／９','９１５','７','ｆｔ８','ｊｈ１ａｂｃ','－０１','－１２','Japan','Japan','メモ','１１０１０１')
        q.validate()
        self.assertEqual((q.date,q.time,q.band,q.mode,q.call,q.sent,q.received,q.code),
                         ('2026-09-09','09:15','7','FT8','JH1ABC','-01','-12','110101'))
        self.assertEqual(q.remarks,'メモ')

if __name__=='__main__':unittest.main()
