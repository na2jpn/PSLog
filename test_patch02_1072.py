import tempfile
import unittest
from pathlib import Path

from jccjcg_batch import code_from_rmks, prefecture_qth_from_rmks
from locations import load as load_locations
from qsl_batch import read_entries, prepare, commit
from model import QSO
from storage import VERSION, Repository

ROOT = Path(__file__).resolve().parent


class Patch021072Tests(unittest.TestCase):
    def test_version(self):
        self.assertEqual(VERSION, '1.14')

    def test_jcc_batch_ignores_known_qsl_tokens_with_or_without_received_suffix(self):
        for token in ('BURO','BURO.R','CARD','CARD.R','1way','1way.R','Direct','Direct.R',
                      'LoTW','LoTW.R','eQSL','eQSL.R','hQSL','hQSL.R','QRZ','QRZ.R','Other','Other.R'):
            with self.subTest(token=token):
                self.assertEqual(code_from_rmks(f'1321 {token}'), '1321')

    def test_jcc_batch_ignores_decimal_frequency_memos_but_not_other_notes(self):
        self.assertEqual(code_from_rmks('1321 433.16 hQSL.R'), '1321')
        self.assertEqual(code_from_rmks('16001H (7.030) BURO'), '16001H')
        self.assertEqual(code_from_rmks('1321 移動 hQSL.R'), '')
        self.assertEqual(code_from_rmks('1321 7MHz hQSL.R'), '')

    def test_jcc_batch_uses_rmks1_only(self):
        self.assertEqual(code_from_rmks('1321 <<RMKS2>> 433.16 hQSL.R'), '1321')
        self.assertEqual(code_from_rmks('移動 <<RMKS2>> 1321'), '')

    def test_prefecture_mode_accepts_area_plus_qsl_and_frequency(self):
        data=load_locations(ROOT)
        self.assertEqual(prefecture_qth_from_rmks(data,'35 7.030 hQSL.R'),'Hiroshima Japan')

    def test_qsl_txt_accepts_optional_jccjcg_in_any_order(self):
        lines='\n'.join([
            'JA1AAA 2026/9/10 5:10',
            'JA1AAA 2026/9/10 5:10 1321',
            '1321 5:10 JA1AAA 2026/9/10',
            '2026/9/10 16001H JA1AAA 5:10',
        ])
        rows=read_entries(lines.encode('utf-8-sig'),'JST','utf-8-sig')
        self.assertEqual([(r.call,r.code,r.reason) for r in rows],[
            ('JA1AAA','',''),('JA1AAA','1321',''),('JA1AAA','1321',''),('JA1AAA','16001H','')])

    def test_qsl_txt_still_requires_colon_in_time(self):
        rows=read_entries('2026/9/10 0510 JA1AAA 1321'.encode('utf-8-sig'),'JST','utf-8-sig')
        self.assertIsNone(rows[0].stamp)
        self.assertIn('3項目、またはJCC/JCGを加えた4項目',rows[0].reason)

    def test_qsl_txt_input_code_does_not_overwrite_log_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); repo=Repository(root/'data')
            q=QSO('2026-09-10','05:10','7','CW','JA1AAA','599','599','Japan','Soka Saitama Japan','','1001')
            path=repo.path_for('JH1HST','',q.date); repo.open(path).append(q)
            source=root/'receive.txt'; source.write_text('2026/9/10 5:10 JA1AAA 1321',encoding='utf-8')
            plan=prepare(repo,source,'JH1HST','JST','hQSL.R')
            self.assertEqual(plan.entries[0].code,'1321')
            commit(repo,plan,root/'reports')
            after=repo.open(path).log.records[0][1]
            self.assertEqual(after.code,'1001')
            self.assertIn('hQSL.R',after.remarks)

    def test_qsl_ui_explains_optional_code_and_colon(self):
        source=(ROOT/'qsl_ui.py').read_text(encoding='utf-8')
        self.assertIn('JCC/JCGが分かる場合はコードを1項目追加できます',source)
        self.assertIn('時刻は 5:10 のように : が必要です',source)
        self.assertIn('海外局などJCC/JCGがない場合は従来どおり3項目',source)


if __name__ == '__main__':
    unittest.main()
