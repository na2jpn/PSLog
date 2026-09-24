import unittest,csv,io
from pathlib import Path
from model import QSO
from exporting import hamlog
from hamlog_import import convert
from hamlog_export_fields import name_from_remarks,qsl_from_remarks


class HamlogExportFieldTests(unittest.TestCase):
    def test_names_and_ambiguous_notes(self):
        for note,expected in [('OP:Taro','Taro'),('memo OP:Taro BURO.R','Taro'),('OP:"山田 太郎" メモ','山田 太郎'),('OP:Taro 山登り',''),('OP:A OP:B',''),('OP:"Broken',''),('ADIF_EXTRA:{"NAME":"OP:wrong"}','')]:
            with self.subTest(note=note):self.assertEqual(name_from_remarks(note,set()),expected)

    def test_qsl_positions_are_not_collapsed(self):
        for note,expected in [('BURO','B* '),('BURO.R','B *'),('BURO BURO.R','B**'),('CARD.R','  *'),('CARD',' * '),('Direct.R','D *'),('Direct',''),('LoTW.R eQSL.R hQSL.R',''),('BURO Direct.R',' **')]:
            with self.subTest(note=note):self.assertEqual(qsl_from_remarks(note,set()),expected)

    def test_csv_encoding_notes_and_reimport(self):
        q=QSO('2026-09-12','12:00','7','SSB','JA1YYY','59','59','Japan','Soka Saitama Japan','OP:"山田 太郎" CARD.R','')
        data,warnings=hamlog([('JH1HST',q,Path('sample.txt'),1)])
        row=next(csv.reader(io.StringIO(data.decode('cp932'))))
        self.assertEqual(len(row),15)
        self.assertEqual(row[9],'  *');self.assertEqual(row[10],'山田 太郎')
        self.assertEqual(row[12],q.remarks);self.assertIn(q.my_qth,row[13])
        log,_=convert(data)
        self.assertFalse(log.issues)
        self.assertEqual(log.records[0][1].remarks.count('OP:'),1)
        self.assertIn('"QSL":"  *"',log.records[0][1].remarks)
