import unittest
from pathlib import Path

from input_normalization import amateur_callsign_entry
from band_stats import color_for_band,band_badge,total_badge
from storage import VERSION

class Patch08Ver1058Tests(unittest.TestCase):
    def test_version(self):
        self.assertEqual(VERSION,'1.14')

    def test_amateur_callsign_entry_filters_and_normalizes(self):
        self.assertEqual(amateur_callsign_entry('ｊｈ１ｈｓｔ／１'),'JH1HST/1')
        self.assertEqual(amateur_callsign_entry('ja4msm あいう-#'),'JA4MSM')
        self.assertEqual(amateur_callsign_entry('ＪＱ７ＦＩＵ/P'),'JQ7FIU/P')

    def test_band_colors(self):
        self.assertEqual(color_for_band('0.475'),'#D9C6A8')
        self.assertEqual(color_for_band('1.8'),'#D9B8CF')
        self.assertEqual(color_for_band('1.9'),'#D9B8CF')
        self.assertEqual(color_for_band('3.5'),'#E6B3B3')
        self.assertEqual(color_for_band('7'),'#F2C7D5')
        self.assertEqual(color_for_band('1200'),'#DDD2E8')
        self.assertEqual(color_for_band('2400'),'#D2C9E8')
        self.assertEqual(color_for_band('10000'),'#D2C9E8')

    def test_badge_html(self):
        text=band_badge('7',10)
        self.assertIn('#F2C7D5',text);self.assertIn('7 MHz 10',text)
        self.assertIn('合計 13',total_badge(13))

    def test_gui_source_has_patch08_labels_and_no_active_underline(self):
        source=Path('main.py').read_text(encoding='utf-8')
        self.assertIn('コンテストナンバー（RMKS）',source)
        self.assertIn("QColor('#E3F1E6')",source)
        tab=source[source.index('class SessionTabBar'):source.index('class Window')]
        self.assertIn('painter.drawLine(rect.topLeft(),rect.topRight())',tab)
        self.assertNotIn('painter.drawLine(rect.bottomLeft(),rect.bottomRight())',tab)
        self.assertIn('_filter_amateur_callsign_editor',source)

if __name__=='__main__':
    unittest.main()
