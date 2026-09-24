import unittest,tempfile,csv,io
from pathlib import Path
from countries import load,Countries
from hamlog_import import convert
from storage import StorageError

class CountryTests(unittest.TestCase):
    def test_reference_countries_and_uncertain_portable(self):
        data=load(Path(__file__).parent)
        for call,name in [('JH1HST','Japan'),('JH1HST/1','Japan'),('DL5TI','Fed. Rep. of Germany'),('HL4ZHE','Republic of Korea')]:
            self.assertEqual(data.lookup(call)['country'],name)
        for call in ('JH1HST/JD1','JD1ABC','JH1HST/HL','K1AAA/MM','K1AAA/AM','K1AAA/7','VERSION','QQ0ZZZ'):
            self.assertIsNone(data.lookup(call),call)
    def test_exact_longest_prefix_and_continent_override(self):
        text='One: 1: 1: EU: 0: 0: 0: A:\n A,AB{AS},=AB1ZZ{AF};'
        db=Countries(text)
        self.assertEqual(db.lookup('AB2ZZ')['continent'],'AS')
        self.assertEqual(db.lookup('AB1ZZ')['continent'],'AF')
        self.assertEqual(db.lookup('AB1ZZZ')['continent'],'AS')
    def test_hamlog_unknown_japanese_qth_country_hint_preserves_note(self):
        data=load(Path(__file__).parent);out=io.StringIO();csv.writer(out).writerow(['DL5TI','2026/09/11','12:00J','599','599','7','CW','','','','Op','日本語所在地','','',''])
        log,_=convert(out.getvalue().encode('cp932'),country_data=data)
        self.assertFalse(log.issues);q=log.records[0][1]
        self.assertEqual(q.his_qth,'Fed. Rep. of Germany');self.assertIn('QTH:日本語所在地',q.remarks)
        log,_=convert(out.getvalue().encode('cp932'));self.assertEqual(log.records[0][1].his_qth,'')
    def test_corrupt_local_database_does_not_fallback(self):
        with tempfile.TemporaryDirectory() as root:
            p=Path(root)/'config/db/cty.dat';p.parent.mkdir(parents=True);p.write_text('broken')
            with self.assertRaises(StorageError):load(root)
