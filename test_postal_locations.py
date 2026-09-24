import unittest,json
from pathlib import Path
from tools.add_postal_locations import spelling
from locations import candidates,confirmed

class PostalLocationTests(unittest.TestCase):
    def test_structures_and_gun(self):
        self.assertEqual(spelling('TOKYO TO','ADACHI KU'),'Adachi Tokyo Japan')
        self.assertEqual(spelling('TOKUSHIMA KEN','ITANO GUN KAMIITA CHO'),'Kamiita Itano gun Tokushima Japan')
        self.assertEqual(spelling('HOKKAIDO','SAPPORO SHI CHUO KU'),'Chuo Sapporo Hokkaido Japan')
        self.assertIsNone(spelling('TOKYO TO','UNRECOGNIZED'))
    def test_candidates_do_not_become_verified_or_change_existing(self):
        db=json.loads((Path(__file__).parent/'config/db/locations.json').read_text('utf-8'))
        row=next(r for r in db['rows'] if r.get('reference_qth') and not r['verified_qth'])
        self.assertIn(row['reference_qth'],[v for v,s in candidates(db,row)])
        self.assertIsNone(confirmed(db,row['name'],row['source_code']))
        self.assertEqual(sum(bool(r['verified_qth']) for r in db['rows']),3)
        self.assertEqual(sum(bool(r.get('reference_qth')) for r in db['rows']),1899)

    def test_explicit_equivalences_and_unresolved_stay_distinct(self):
        from locations import find
        db=json.loads((Path(__file__).parent/'config/db/locations.json').read_text('utf-8'))
        rows={r['name']:r for r in db['rows']}
        self.assertEqual(rows['千葉県袖ヶ浦市']['reference_qth'],'Sodegaura Chiba Japan')
        self.assertEqual(rows['埼玉県さいたま市']['reference_qth'],'Saitama Saitama Japan')
        self.assertEqual(rows['東京都小笠原支庁小笠原村']['reference_qth'],'Ogasawara Tokyo Japan')
        self.assertEqual(rows['山梨県西八代郡市川三郷町']['reference_qth'],'Ichikawamisato Nishiyatsushiro gun Yamanashi Japan')
        self.assertTrue(find(db,'Sodegaura'))
        self.assertEqual(rows['奈良県吉野郡天川村']['reference_qth'],'Tenkawa Yoshino gun Nara Japan')
        self.assertEqual(rows['静岡県浜松市中区']['reference_qth'],'Naka Hamamatsu Shizuoka Japan')
        self.assertEqual(rows['福岡県筑紫郡那珂川町']['reference_qth'],'Nakagawa Chikushi gun Fukuoka Japan')
        self.assertEqual(len(db['postal_reference']['unresolved']),0)
        self.assertEqual(db['postal_reference']['matched'],1891)
        self.assertEqual(db['postal_reference']['historical_candidates'],8)
        for row in db['rows']:
            value=row.get('reference_qth','')
            if value:
                self.assertTrue(value.isascii());self.assertTrue(value.endswith(' Japan'))
                self.assertFalse(any(c in value for c in '|\t\n'))
                if row['kind']=='JCG' and '郡' in row['name']:self.assertIn(' gun ',value)

    def test_php_master_preserved_except_authorized_tenkawa_correction(self):
        import re
        root=Path(__file__).parent
        db=json.loads((root/'config/db/locations.json').read_text('utf-8'))
        expected=[]
        for kind,filename in (('JCC','jcc_np.php'),('JCG','jcg_np.php')):
            for name,code in re.findall(r'"([^"\n]+)"\s*=>\s*"([0-9]+[A-Z]?)"',(root/'tools/reference'/filename).read_text(encoding='utf-8')):
                if kind=='JCG' and code=='24010H':
                    self.assertEqual(name,'奈良県吉野郡');name+='天川村'
                expected.append((kind,code,name))
        self.assertCountEqual(expected,[(r['kind'],r['source_code'],r['name']) for r in db['rows']])
        from tools.add_postal_locations import build
        rebuilt=build(json.loads(json.dumps(db)),(root/'tools/reference/JapanPost_202506_roman.zip').read_bytes())
        self.assertEqual(rebuilt,db)
