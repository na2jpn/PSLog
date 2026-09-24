import csv,io,tempfile,unittest,json
from pathlib import Path
from storage import Repository,InvalidLog,StorageError
from importing import prepare,commit
from hamlog_import import convert
BASE=['JA1YYY','26/01/01','00:05J','599','599','7.030','CW','1101','PM95','J','太郎','埼玉県草加市','BURO','memo','']
def csvbytes(rows,encoding='cp932'):
    out=io.StringIO(newline='');csv.writer(out,lineterminator='\r\n').writerows(rows);return out.getvalue().encode(encoding)
class HamlogTests(unittest.TestCase):
    def test_mapping_japanese_op_and_original_columns(self):
        log,meta=convert(csvbytes([BASE]));q=log.records[0][1]
        self.assertEqual((q.date,q.time,q.band,q.code),('2026-01-01','00:05','7','1101'))
        self.assertEqual(q.his_qth,'PM95 Japan');self.assertEqual(q.my_qth,'')
        for text in ['OP:太郎','BURO','memo','QTH:埼玉県草加市','7.030']:self.assertIn(text,q.remarks)
        self.assertEqual(meta['records'][0]['fields'],BASE)
    def test_utc_date_rollover_and_missing_zone(self):
        row=BASE.copy();row[1]='2025/12/31';row[2]='23:59U'
        log,_=convert(csvbytes([row]));self.assertEqual(log.records[0][1].date,'2026-01-01');self.assertEqual(log.records[0][1].time,'08:59')
        row[2]='23:59';log,_=convert(csvbytes([row]));self.assertTrue(log.issues)
        log,_=convert(csvbytes([row]),timezone='UTC');self.assertFalse(log.issues)
        row[1]='99/01/01';log,_=convert(csvbytes([row]),timezone='JST',century=1900);self.assertEqual(log.records[0][1].date,'1999-01-01')
    def test_quotes_newlines_and_bom(self):
        row=BASE.copy();row[12]='memo, "a"\nnext|line'
        log,_=convert(csvbytes([row],'utf-8-sig'));self.assertIn('memo, "a"\\nnext｜line',log.records[0][1].remarks)
        with self.assertRaises(InvalidLog):convert(b'"unterminated')
    def test_numbered_records_not_overwrite(self):
        log,_=convert(csvbytes([['23']+BASE]));self.assertIn('RecordNumber',log.records[0][1].remarks)
        with self.assertRaises(InvalidLog):convert(csvbytes([BASE,['1']+BASE]))
    def test_bad_date_grid_and_unknown_mode(self):
        for index,value in [(1,'26/02/30'),(2,'25:99J'),(5,'nan'),(8,'BAD')]:
            row=BASE.copy();row[index]=value;log,_=convert(csvbytes([row]));self.assertTrue(log.issues)
        row=BASE.copy();row[6]='FUTURE';log,_=convert(csvbytes([row]));self.assertEqual(log.records[0][1].mode,'FUTURE')
    def test_foreign_qth_not_assumed_japan(self):
        row=BASE.copy();row[0]='JH1HST/KH6';log,_=convert(csvbytes([row]));q=log.records[0][1]
        self.assertEqual(q.his_qth,'PM95');self.assertEqual(q.code,'');self.assertIn('Code',q.remarks)
    def test_year_file_duplicates_and_commit(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'hamlog.csv';raw=csvbytes([BASE,BASE]);source.write_bytes(raw);repo=Repository(Path(tmp)/'data')
            p=prepare(repo,source,'JH1HST/1');self.assertEqual(sum(t['skipped'] for t in p.targets.values()),1)
            with self.assertRaises(StorageError):commit(repo,p)
            report,saved=commit(repo,p,conversions_confirmed=True)
            self.assertEqual(len(repo.open(saved[0]).log.records),1);self.assertEqual(source.read_bytes(),raw)
            self.assertEqual(json.loads(report.read_text(encoding='utf-8'))['import_metadata']['format'],'HAMLOG CSV')
