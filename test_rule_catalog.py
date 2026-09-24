import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from contest_rules import RuleStore,default_rule

class CatalogTests(unittest.TestCase):
    def test_save_update_copy_year_and_manual_notes(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=RuleStore(tmp);r=default_rule();p,s=store.save(r)
            catalog=store.folder/'CATALOG.md'
            catalog.write_text('手動メモ\n'+catalog.read_text(encoding='utf-8'),encoding='utf-8')
            r['name']='変更名';p,s=store.save(r,p,s)
            self.assertIn('変更名',catalog.read_text(encoding='utf-8'));self.assertNotIn('新しいルール',catalog.read_text(encoding='utf-8'))
            r['year']+=1;store.save(r);r['id']='another';store.save(r)
            text=catalog.read_text(encoding='utf-8');self.assertTrue(text.startswith('手動メモ'));self.assertIn('3件',text)
            p.unlink();store.sync_catalog();self.assertIn('2件',catalog.read_text(encoding='utf-8'))
    def test_catalog_failure_preserves_rule_and_retries(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=RuleStore(tmp)
            with patch('rule_catalog.sync',side_effect=OSError('disk error')):p,_=store.save(default_rule())
            self.assertTrue(p.exists());self.assertIn('保存済み',store.catalog_warning)
            store.sync_catalog();self.assertIn('1件',(store.folder/'CATALOG.md').read_text(encoding='utf-8'))
    def test_invalid_files_are_reported_and_manual_marker_damage_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=RuleStore(tmp);store.save(default_rule());bad=store.folder/'bad.txt';bad.write_text('invalid')
            store.sync_catalog();catalog=store.folder/'CATALOG.md';self.assertIn('bad.txt',catalog.read_text(encoding='utf-8'))
            catalog.write_text('<!-- PSLOG GENERATED RULES BEGIN --> 手動メモ',encoding='utf-8')
            before=catalog.read_bytes()
            with self.assertRaises(ValueError):store.sync_catalog()
            self.assertEqual(before,catalog.read_bytes())
