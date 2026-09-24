import unittest
from pathlib import Path
from storage import VERSION
from qsl_marks import change


class Patch09Tests(unittest.TestCase):
    def test_version_and_qsl_quick_add_normalization(self):
        self.assertEqual(VERSION,'1.14')
        self.assertEqual(change('33','hQSL.R')[0],'33 hQSL.R')
        self.assertEqual(change('33 hQSL.R','hQSL.R')[0],'33 hQSL.R')
        self.assertEqual(change('33 BURO','BURO.R')[0],'33 BURO.R')
        self.assertEqual(change('','LoTW.R')[0],'LoTW.R')

    def test_file_menu_labels_and_order_are_defined(self):
        source=Path('main.py').read_text(encoding='utf-8')
        expected=[
            '本体の場所を開く','ログを再読込',
            'ログファイルの場所を開く','出力ファイルの場所を開く','レポートの場所を開く',
            'PSLog再起動','PSLog終了',
        ]
        positions=[source.index("'"+label+"'") for label in expected]
        self.assertEqual(positions,sorted(positions))
        self.assertIn("'本体の場所を開く','ログを再読込',None",source)
        self.assertIn("'レポートの場所を開く',None,",source)


if __name__=='__main__':unittest.main()
