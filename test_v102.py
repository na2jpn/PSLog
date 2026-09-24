import json
import unittest
from pathlib import Path

from contest_rules import loads
from storage import VERSION


ROOT = Path(__file__).resolve().parent
AUDIT = ROOT / 'docs' / 'contest-research' / 'PSLOG101_CURRENT_AUDIT.json'
STATUS = ROOT / 'docs' / 'IMPLEMENTATION_STATUS.md'
START = '<!-- CURRENT_IMPLEMENTATION_STATUS_START -->'
END = '<!-- CURRENT_IMPLEMENTATION_STATUS_END -->'


class V103DocumentationStatusTests(unittest.TestCase):
    def setUp(self):
        self.audit = json.loads(AUDIT.read_text(encoding='utf-8'))

    def runtime_paths(self, item):
        values = item.get('runtime_definitions')
        if values:
            return [ROOT / value for value in values]
        value = item.get('runtime_definition', '').split('：', 1)[0].strip()
        return [ROOT / value] if value else []

    def test_version_is_103(self):
        self.assertEqual(VERSION, '1.14')

    def test_final_audit_is_complete(self):
        self.assertEqual(self.audit['defined'], 87)
        self.assertEqual(self.audit['undefined'], 0)
        self.assertEqual(len(self.audit['contests']), 87)
        self.assertEqual(len({c['id'] for c in self.audit['contests']}), 87)

    def test_all_audit_runtime_definitions_exist_and_parse(self):
        seen = set()
        for item in self.audit['contests']:
            paths = self.runtime_paths(item)
            self.assertTrue(paths, item['id'])
            for path in paths:
                self.assertTrue(path.is_file(), f"{item['id']}: {path}")
                rule = loads(path.read_text(encoding='utf-8-sig'))
                seen.add((rule['id'], rule['year']))
        # Shared/alias audit items are intentional; every referenced file must
        # still parse as a valid current rule.
        self.assertGreaterEqual(len(seen), 84)

    def test_every_current_research_note_has_one_current_status_banner(self):
        notes = {}
        for item in self.audit['contests']:
            notes.setdefault(item['implementation_note'], []).append(item['id'])
        self.assertEqual(len(notes), 78)
        for rel, ids in notes.items():
            text = (ROOT / rel).read_text(encoding='utf-8')
            self.assertEqual(text.count(START), 1, rel)
            self.assertEqual(text.count(END), 1, rel)
            self.assertIn('現在の実装状態', text, rel)
            self.assertIn('実装済み', text, rel)
            for ident in ids:
                self.assertIn(f'`{ident}`', text, rel)

    def test_current_status_document_covers_all_audit_items(self):
        text = STATUS.read_text(encoding='utf-8')
        self.assertIn('87 / 87 実装定義済み', text)
        for item in self.audit['contests']:
            self.assertIn(f"`{item['id']}`", text)

    def test_obsolete_tracker_is_not_referenced_by_current_status_docs(self):
        targets = [STATUS, ROOT / 'docs' / 'CONTEST_RESEARCH_ALL.md']
        targets.extend(ROOT / item['implementation_note'] for item in self.audit['contests'])
        for path in set(targets):
            self.assertNotIn('CONTEST_IMPLEMENTATION_TRACKER.json', path.read_text(encoding='utf-8'), str(path))


if __name__ == '__main__':
    unittest.main()
