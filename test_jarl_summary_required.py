import unittest
from contest_export import check_jarl_official_required


class JarlOfficialRequiredTests(unittest.TestCase):
    def base(self):
        return dict(
            contest='テストコンテスト', category='X', callsign='JH1HST/0',
            address='埼玉県草加市', name='試験 太郎', power='5', email='test@example.com',
            date='2026-09-17', signature='試験 太郎', oath=True,
        )

    def test_r10_requires_license_and_power_type(self):
        info=self.base()
        with self.assertRaisesRegex(ValueError,'従事者資格'):
            check_jarl_official_required('JARL R1.0',info)
        info['licenseclass']='第2級アマチュア無線技士'
        with self.assertRaisesRegex(ValueError,'出力の記載区分'):
            check_jarl_official_required('JARL R1.0',info)
        info['powertype']='定格出力'
        check_jarl_official_required('JARL R1.0',info)
        info['powertype']='その他'
        with self.assertRaisesRegex(ValueError,'定格出力.*実測出力'):
            check_jarl_official_required('JARL R1.0',info)

    def test_r21_does_not_require_r10_only_fields(self):
        check_jarl_official_required('JARL R2.1',self.base())

    def test_r21_field_day_requires_power_supply(self):
        info=self.base();info['fd']=True
        with self.assertRaisesRegex(ValueError,'使用電源'):
            check_jarl_official_required('JARL R2.1',info)
        info['powersupply']='商用電源'
        check_jarl_official_required('JARL R2.1',info)

    def test_common_required_fields_are_checked(self):
        for field,label in [('contest','コンテスト名'),('category','部門コード'),('callsign','提出コールサイン'),('address','連絡先住所'),('name','氏名・クラブ局名称'),('power','最大空中線電力'),('email','メールアドレス'),('date','宣誓日'),('signature','署名')]:
            with self.subTest(field=field):
                info=self.base();info[field]=''
                with self.assertRaisesRegex(ValueError,label):
                    check_jarl_official_required('JARL R2.1',info)
        info=self.base();info['oath']=False
        with self.assertRaisesRegex(ValueError,'宣誓'):
            check_jarl_official_required('JARL R2.1',info)


if __name__=='__main__':
    unittest.main()
