import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

from storage import VERSION
from time_range import prefix_boundary,range_boundaries
from exporting import boundary
from sota_export import minute_boundary
from contest_confirmations import show_confirmation,filtered_flags
from category_filters import category_compatible
from contest_rules import _migrate_legacy_rule,loads,RuleStore
from bundled_sync import sync_bundled_folder,bundled_status

ROOT=Path(__file__).resolve().parent


class Patch011061Tests(unittest.TestCase):
    def test_version(self):
        self.assertEqual(VERSION,'1.061')

    def test_partial_datetime_boundaries(self):
        self.assertEqual(prefix_boundary('20260915',False),'20260915000000')
        self.assertEqual(prefix_boundary('20260917',True),'20260917235959')
        self.assertEqual(prefix_boundary('202602',True),'20260228235959')
        self.assertEqual(prefix_boundary('202402',True),'20240229235959')
        self.assertEqual(prefix_boundary('',False),'')
        self.assertEqual(range_boundaries('20260915','',14),('20260915000000',''))
        self.assertEqual(range_boundaries('','20260917',14),('', '20260917235959'))
        self.assertEqual(boundary('20260915',False).strftime('%Y%m%d%H%M%S'),'20260915000000')
        self.assertEqual(boundary('20260917',True).strftime('%Y%m%d%H%M%S'),'20260917235959')
        self.assertEqual(minute_boundary('20260917',True),'20260917235959')
        with self.assertRaises(ValueError):prefix_boundary('20260230',False)
        with self.assertRaises(ValueError):range_boundaries('20260918','20260917')

    def test_confirmation_policy(self):
        practical='同一部門内の運用場所を変更していない'
        self.assertTrue(show_confirmation(practical))
        for text in (
            'セルフスポット・クラスターを利用していない',
            'インターネット経由の連絡をしていない',
            'ログソフトの機能を使用していない',
            '大会原典の運用制限と提出数を確認し、未受信番号を事後に補っていない（申告得点・審査前）',
            '国内の規約対象局として、実運用地・使用周波数・免許範囲・完全な番号交換を確認した',
        ):
            self.assertFalse(show_confirmation(text),text)
        self.assertEqual(filtered_flags([practical,practical,'セルフスポットなし']),[practical])

    def test_category_compatibility_uses_entered_station_and_power(self):
        c={'station_types':['individual'],'max_power':50}
        self.assertTrue(category_compatible(c,'individual',50))
        self.assertFalse(category_compatible(c,'club',50))
        self.assertFalse(category_compatible(c,'individual',100))
        self.assertTrue(category_compatible(c,'',0))
        qrp={'max_power':5,'min_power_exclusive':1}
        self.assertFalse(category_compatible(qrp,'',1))
        self.assertTrue(category_compatible(qrp,'',5))

    def test_legacy_opplace_migration_is_narrow_and_safe(self):
        bundled=(ROOT/'config/rules/all_okayama_2026.txt').read_bytes()
        current=loads(bundled.decode('utf-8-sig'))
        old=copy.deepcopy(current);old['event']['submission']['required_fields']=['opplace']
        local=(json.dumps(old,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
        self.assertEqual(_migrate_legacy_rule('all_okayama_2026.txt',local,bundled),bundled)
        edited=copy.deepcopy(old);edited['name']='ユーザー編集'
        local2=(json.dumps(edited,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
        self.assertIsNone(_migrate_legacy_rule('all_okayama_2026.txt',local2,bundled))

    def test_source_tree_same_name_rule_is_user_defined_not_user_modified(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);store=RuleStore(root)
            r=copy.deepcopy(loads((ROOT/'config/rules/shiga_2026.txt').read_text(encoding='utf-8-sig')))
            r['name']='滋賀コンテスト';r['sort_name']='しがコンテスト'
            r['points']['phone']=99
            path,_=store.save(r)
            self.assertEqual(store.origin(path),'user_defined')
            self.assertEqual(store.display_label(r,path),'（ユーザー定義）滋賀コンテスト（2026）')

    def test_bundled_sync_updates_official_and_preserves_user_edits(self):
        old_frozen=getattr(sys,'frozen',None);had_frozen=hasattr(sys,'frozen')
        old_meipass=getattr(sys,'_MEIPASS',None);had_meipass=hasattr(sys,'_MEIPASS')
        try:
            with tempfile.TemporaryDirectory() as td:
                base=Path(td);bundle=base/'bundle';target=base/'data'/'rules';source=bundle/'config'/'rules';source.mkdir(parents=True)
                (source/'a.txt').write_text('v1\n',encoding='utf-8')
                sys.frozen=True;sys._MEIPASS=str(bundle)
                self.assertEqual(sync_bundled_folder(target,'config/rules','*.txt'),1)
                self.assertEqual((target/'a.txt').read_text(),'v1\n')
                self.assertEqual(bundled_status(target,'config/rules','a.txt'),'official')
                (source/'a.txt').write_text('v2\n',encoding='utf-8')
                self.assertEqual(sync_bundled_folder(target,'config/rules','*.txt'),1)
                self.assertEqual((target/'a.txt').read_text(),'v2\n')
                (target/'a.txt').write_text('my edit\n',encoding='utf-8')
                (source/'a.txt').write_text('v3\n',encoding='utf-8')
                self.assertEqual(sync_bundled_folder(target,'config/rules','*.txt'),0)
                self.assertEqual((target/'a.txt').read_text(),'my edit\n')
                self.assertEqual(bundled_status(target,'config/rules','a.txt'),'user_modified')
                (target/'mine.txt').write_text('mine\n',encoding='utf-8')
                self.assertEqual(bundled_status(target,'config/rules','mine.txt'),'user_defined')
        finally:
            if had_frozen:sys.frozen=old_frozen
            elif hasattr(sys,'frozen'):del sys.frozen
            if had_meipass:sys._MEIPASS=old_meipass
            elif hasattr(sys,'_MEIPASS'):del sys._MEIPASS

    def test_rulestore_migrates_exact_legacy_opplace_on_first_frozen_start(self):
        old_frozen=getattr(sys,'frozen',None);had_frozen=hasattr(sys,'frozen')
        old_meipass=getattr(sys,'_MEIPASS',None);had_meipass=hasattr(sys,'_MEIPASS')
        try:
            with tempfile.TemporaryDirectory() as td:
                base=Path(td);bundle=base/'bundle';root=base/'portable';src=bundle/'config'/'rules';src.mkdir(parents=True)
                bundled=(ROOT/'config/rules/all_okayama_2026.txt').read_bytes();(src/'all_okayama_2026.txt').write_bytes(bundled)
                current=loads(bundled.decode('utf-8-sig'));old=copy.deepcopy(current);old['event']['submission']['required_fields']=['opplace']
                dst=root/'config'/'rules';dst.mkdir(parents=True);(dst/'all_okayama_2026.txt').write_text(json.dumps(old,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
                sys.frozen=True;sys._MEIPASS=str(bundle)
                store=RuleStore(root)
                migrated,_=store.read(dst/'all_okayama_2026.txt')
                self.assertNotIn('opplace',migrated['event']['submission']['required_fields'])
                self.assertEqual(store.origin(dst/'all_okayama_2026.txt'),'official')
        finally:
            if had_frozen:sys.frozen=old_frozen
            elif hasattr(sys,'frozen'):del sys.frozen
            if had_meipass:sys._MEIPASS=old_meipass
            elif hasattr(sys,'_MEIPASS'):del sys._MEIPASS

    def test_only_four_current_contests_require_opplace(self):
        got=[]
        for p in (ROOT/'config/rules').glob('*.txt'):
            try:r=loads(p.read_text(encoding='utf-8-sig'))
            except ValueError:continue
            if 'opplace' in r.get('event',{}).get('submission',{}).get('required_fields',[]):got.append(r['id'])
        self.assertEqual(sorted(got),sorted(['all_chiba','all_hyogo','kcj','kcj-topband']))
        import re
        occurrences=[]
        for p in (ROOT/'devtools').glob('*.py'):
            if any(re.search(r'required_fields.*opplace',line) for line in p.read_text(encoding='utf-8').splitlines()):occurrences.append(p.name)
        self.assertEqual(sorted(occurrences),sorted(['build_all_chiba_2026.py','build_final9.py','build_remaining28.py']))


if __name__=='__main__':unittest.main()
