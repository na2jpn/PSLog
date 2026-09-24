import tempfile, unittest
from dataclasses import replace
from pathlib import Path

from model import QSO
from storage import Repository, VERSION, parse
from qsl_batch import prepare, commit, report_paths


class Patch07V1067Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.repo=Repository(self.root/'data')
        self.source=self.root/'receive.txt';self.out=self.root/'results'
        self.q=QSO('2026-09-13','06:29','7','CW','JH7VTE','599','599','Japan','Soka Saitama Japan','hQSL','04007B')

    def add(self,q=None):
        q=q or self.q
        p=self.repo.path_for('JH1HST','',q.date);self.repo.open(p).append(q);return p

    def test_version(self):
        self.assertEqual(VERSION,'1.14')

    def test_result_report_ends_with_actual_updated_pslog_source_line(self):
        p=self.add();self.source.write_text('2026-09-13 06:29 JH7VTE\n',encoding='utf-8')
        plan=prepare(self.repo,self.source,'JH1HST','JST','hQSL.R')
        _,journal,_=commit(self.repo,plan,self.out)
        result,_=report_paths(journal);text=result.read_text(encoding='utf-8-sig')
        marker='===== QSL対象となったPSLog原本行 ====='
        self.assertIn(marker,text)
        actual=parse(p.read_bytes()).lines[0].raw.rstrip('\r\n')
        tail=text.split(marker,1)[1]
        self.assertIn(actual,tail)
        self.assertIn('hQSL.R',actual)
        self.assertNotIn('hQSL hQSL.R',actual)

    def test_result_report_has_no_fake_source_line_when_nothing_changed(self):
        self.add(replace(self.q,remarks='hQSL.R'))
        self.source.write_text('2026-09-13 06:29 JH7VTE\n',encoding='utf-8')
        plan=prepare(self.repo,self.source,'JH1HST','JST','hQSL.R')
        _,journal,_=commit(self.repo,plan,self.out)
        result,_=report_paths(journal);text=result.read_text(encoding='utf-8-sig')
        self.assertIn('===== QSL対象となったPSLog原本行 =====',text)
        self.assertIn('（今回、PSLog原本を書き換えたQSOはありません）',text)

    def test_ui_source_declares_rich_colours_and_dynamic_receipt_button(self):
        src=Path('qsl_ui.py').read_text(encoding='utf-8')
        self.assertIn("DETAIL_YELLOW='#fff6cc'",src)
        self.assertIn("DETAIL_PINK='#ffe2ea'",src)
        self.assertIn("self.detail.setHtml",src)
        self.assertIn("チェック済を受領［{self.plan.method}］にする",src)
        self.assertIn("if call_difference(entry.call,candidate.qso.call)=='同一コール':continue",src)


if __name__=='__main__':unittest.main()
