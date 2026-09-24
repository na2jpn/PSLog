import shutil
import tempfile
import unittest
from pathlib import Path

from jccjcg_batch import qth_from_code, collect, MODE_CODE_TO_QTH, MODE_RMKS_TO_BOTH
from model import QSO
from storage import Repository, VERSION

ROOT = Path(__file__).resolve().parent


class Patch031073Tests(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.root = Path(self.t.name)
        (self.root / 'config/db').mkdir(parents=True)
        (self.root / 'logbook').mkdir()
        (self.root / 'bak').mkdir()
        for name in ('locations.json', 'cty.dat', 'cty_meta.json'):
            shutil.copy2(ROOT / 'config/db' / name, self.root / 'config/db' / name)
        self.repo = Repository(self.root)
        self.path = self.root / 'logbook/2026_JH1HST_.txt'

    def write(self, qsos):
        body = '\r\n'.join(q.to_ps() for q in qsos) + '\r\n'
        self.path.write_bytes(b'\xef\xbb\xbf' + body.encode('utf-8'))

    @staticmethod
    def q(code='', remarks='', his='Japan'):
        return QSO('2026-09-24', '06:30', '7', 'CW', 'JA1AAA', '599', '599',
                   his, 'Soka Saitama Japan', remarks, code)

    def test_version(self):
        self.assertEqual(VERSION, '1.14')

    def test_bare_jcg_fills_county_only(self):
        # 11002 has several towns in Ashigarakami-gun.  A bare JCG must not
        # pick one of them; county-level QTH is the intended valid result.
        self.assertEqual(qth_from_code(self.root, '11002'),
                         'Ashigarakamigun Kanagawa Japan')
        self.assertNotIn('Oi ', qth_from_code(self.root, '11002'))
        self.assertNotIn('Kaisei ', qth_from_code(self.root, '11002'))

    def test_bare_jcg_and_specific_suffix_are_distinct(self):
        self.assertEqual(qth_from_code(self.root, '16001'),
                         'Agatsumagun Gumma Japan')
        self.assertEqual(qth_from_code(self.root, '16001H'),
                         'Nakanojo Agatsumagun Gumma Japan')

    def test_batch_code_to_qth_accepts_bare_jcg_as_county(self):
        self.write([self.q(code='16001')])
        rows = collect(self.repo, [self.path], 'JH1HST', MODE_CODE_TO_QTH)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].proposal().his_qth, 'Agatsumagun Gumma Japan')
        self.assertEqual(rows[0].proposal().code, '16001')

    def test_batch_rmks_bare_jcg_sets_generic_code_and_county(self):
        self.write([self.q(remarks='16001 7.030 hQSL.R')])
        rows = collect(self.repo, [self.path], 'JH1HST', MODE_RMKS_TO_BOTH)
        self.assertEqual(len(rows), 1)
        after = rows[0].proposal()
        self.assertEqual(after.code, '16001')
        self.assertEqual(after.his_qth, 'Agatsumagun Gumma Japan')

    def test_non_gun_jcg_exception_is_not_guessed(self):
        # Tokyo island branch-office JCGs have no stable "... gun ..." form in
        # the current master.  PATCH03 must not choose a municipality instead.
        with self.assertRaisesRegex(ValueError, '確定|詳細'):
            qth_from_code(self.root, '10004')


if __name__ == '__main__':
    unittest.main()
