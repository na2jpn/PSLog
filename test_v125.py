import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication, QLabel

import contest_number as numbers
from contest_guidance import instructions
from contest_overview import overview_rows
from main import Window
from remarks_sections import split_for_ui
from session_state import contest_session, restore, serializable, recent_snapshot, reopen_snapshot
from storage import save_settings, StorageError

ROOT = Path(__file__).resolve().parent


class NumberTests(unittest.TestCase):
    def test_examples_preserve_prefix_and_width_and_allow_overflow(self):
        examples = {'ST001':'ST002', '13001':'13002', '01':'02', 'ST01':'ST02',
                    '001':'002', '99':'100', 'ST99':'ST100', '1399':'1400',
                    'ST999':'ST1000', '13099':'13100', '':'', 'ST':'ST'}
        for before, after in examples.items():
            with self.subTest(before=before):
                self.assertEqual(numbers.increment(before), after)

    def test_restoration_and_closed_tab_roundtrip_keep_independent_maps(self):
        session = contest_session('KT', '202612', 'JX1XXX')
        numbers.configure(session, '7', 'ST001', True, True)
        for _ in range(5):
            numbers.recorded(session, '7', session['own_exchange'])
        self.assertEqual(numbers.change_band(session, '7', '3.5', session['own_exchange']), 'ST001')
        numbers.recorded(session, '3.5', 'ST002')
        session['band'] = '3.5'
        snapshot = json.loads(json.dumps(serializable(session)))
        restored = restore({'workspace_sessions':[snapshot]})[0][0]
        self.assertEqual(restored['number_initial'], 'ST001')
        self.assertEqual(numbers.change_band(restored, '3.5', '7.0', 'ST003'), 'ST006')
        restored['number_by_band']['7'] = 'ST100'
        self.assertEqual(session['number_by_band']['7'], 'ST006')
        closed = reopen_snapshot(recent_snapshot(session))
        self.assertEqual(closed['number_by_band'], session['number_by_band'])

    def test_old_settings_and_malformed_optional_state(self):
        old = {'type':'contest', 'contest_name':'KT', 'event_ym':'202612', 'own_exchange':'ST001'}
        restored = restore({'workspace_sessions':[old]})[0][0]
        self.assertFalse(restored['number_increment'])
        self.assertFalse(restored['number_per_band'])
        self.assertEqual(restored['own_exchange'], 'ST001')
        self.assertEqual(numbers.normal_state({'number_by_band':[], 'number_initial':None})['number_by_band'], {})


class ContestGuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        session = contest_session('KT', '202612', 'JX1XXX', '7', 'CW', 'Soka Saitama Japan')
        save_settings(self.tmp.name, {'own':'JX1XXX', 'confirm_record':False,
                      'workspace_sessions':[session], 'active_workspace_id':session['id']})
        self.windows = []
        self.w = self.window()
        self.count = 0

    def window(self):
        window = Window(self.tmp.name)
        self.windows.append(window)
        return window

    def tearDown(self):
        for window in self.windows:
            window.close()
            window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.app.processEvents()
        self.tmp.cleanup()

    def enable(self, value='ST001', per_band=True):
        self.w.c_number_increment.setChecked(True)
        self.w.c_number_per_band.setChecked(per_band)
        self.w.c_own_exchange.setText(value)
        self.w._save_contest_own_exchange()

    def record(self):
        self.count += 1
        w = self.w
        w.c_call.setText(f'JX2X{self.count}')
        w.contest_start_qso()
        w.c_exchange.setText('TK001')
        with patch.object(w, '_confirm_record_time', return_value='normal'):
            w.c_exchange.returnPressed.emit()

    def test_exact_band_roundtrip_and_saved_sent_values(self):
        self.enable()
        for _ in range(5):
            self.record()
        self.assertEqual(self.w.c_own_exchange.text(), 'ST006')
        self.w.c_band.setCurrentText('3.5')
        self.assertEqual(self.w.c_own_exchange.text(), 'ST001')
        for _ in range(2):
            self.record()
        self.assertEqual(self.w.c_own_exchange.text(), 'ST003')
        self.w.c_band.setCurrentText('7')
        self.assertEqual(self.w.c_own_exchange.text(), 'ST006')
        rows = [q for _, q in self.w.rows]
        self.assertEqual([split_for_ui(q.remarks)[1] for q in rows],
                         ['ST001','ST002','ST003','ST004','ST005','ST001','ST002'])
        self.assertEqual([q.band for q in rows], ['7']*5+['3.5']*2)

    def test_numeric_initial_13001_is_reused_on_new_band(self):
        self.enable('13001')
        for _ in range(5):
            self.record()
        self.w.c_band.setCurrentText('3.5')
        self.assertEqual(self.w.c_own_exchange.text(), '13001')
        self.w.c_band.setCurrentText('7.0')
        self.assertEqual(self.w.c_own_exchange.text(), '13006')

    def test_global_sequence_keeps_number_when_band_changes(self):
        self.enable(per_band=False)
        for _ in range(5):
            self.record()
        self.w.c_band.setCurrentText('3.5')
        self.assertEqual(self.w.c_own_exchange.text(), 'ST006')
        for _ in range(2):
            self.record()
        self.w.c_band.setCurrentText('7')
        self.assertEqual(self.w.c_own_exchange.text(), 'ST008')

    def test_default_off_and_disabled_per_band_do_not_increment(self):
        self.assertFalse(self.w.c_number_increment.isChecked())
        self.assertFalse(self.w.c_number_per_band.isEnabled())
        self.w.c_own_exchange.setText('ST001')
        self.record()
        self.w.c_band.setCurrentText('3.5')
        self.assertEqual(self.w.c_own_exchange.text(), 'ST001')

    def test_manual_correction_applies_to_current_band_and_keeps_initial(self):
        self.enable('1399')
        self.record()
        self.assertEqual(self.w.c_own_exchange.text(), '1400')
        self.w.c_own_exchange.setText('13100')
        self.w._save_contest_own_exchange()
        self.w.c_band.setCurrentText('3.5')
        self.assertEqual(self.w.c_own_exchange.text(), '1399')
        self.w.c_band.setCurrentText('7')
        self.assertEqual(self.w.c_own_exchange.text(), '13100')
        self.record()
        self.assertEqual(self.w.c_own_exchange.text(), '13101')

    def test_restart_and_other_tab_keep_next_values_and_options(self):
        self.enable()
        self.record()
        self.w.c_band.setCurrentText('3.5')
        self.record()
        original = self.w._active_workspace()
        other = contest_session('OTHER', '202612', 'JX1XXX')
        self.w.workspace_sessions.append(other)
        self.w._rebuild_session_tabs()
        self.w._on_workspace_changed(1)
        self.assertFalse(self.w.c_number_increment.isChecked())
        self.w.c_own_exchange.setText('OTHER001')
        self.w._on_workspace_changed(0)
        self.assertEqual(self.w.c_own_exchange.text(), 'ST002')
        self.w.persist_settings()
        self.w.close()
        self.windows.remove(self.w)
        self.w.deleteLater()
        self.w = self.window()
        self.assertEqual(self.w._active_workspace()['id'], original['id'])
        self.assertTrue(self.w.c_number_increment.isChecked())
        self.assertTrue(self.w.c_number_per_band.isChecked())
        self.w.c_band.setCurrentText('7')
        self.assertEqual(self.w.c_own_exchange.text(), 'ST002')
        self.w.c_band.setCurrentText('14')
        self.assertEqual(self.w.c_own_exchange.text(), 'ST001')

    def test_record_cancel_or_write_failure_does_not_advance(self):
        self.enable()
        w = self.w
        w.c_call.setText('JX2XXX');w.contest_start_qso();w.c_exchange.setText('TK001')
        with patch.object(w, '_confirm_record_time', return_value='cancel'):
            w.contest_record()
        self.assertEqual(w.c_own_exchange.text(), 'ST001')
        with patch.object(w, '_confirm_record_time', return_value='normal'), patch.object(w, '_append_record_safely', return_value=False):
            w.contest_record()
        self.assertEqual(w.c_own_exchange.text(), 'ST001')
        with patch.object(w, '_confirm_record_time', return_value='normal'), patch.object(w, '_append_record_safely', side_effect=StorageError('test')), patch('main.QMessageBox.warning'):
            w.contest_record()
        self.assertEqual(w.c_own_exchange.text(), 'ST001')
        w.c_date.setText('bad')
        with patch('main.QMessageBox.warning'):
            w.contest_record()
        self.assertEqual(w.c_own_exchange.text(), 'ST001')
        self.assertFalse(w._active_workspace()['number_started'])

    def test_frequency_suffix_is_saved_without_becoming_part_of_counter(self):
        self.enable()
        w = self.w
        w.c_call.setText('JX2XXX');w.contest_start_qso();w.c_exchange.setText('TK001')
        w._contest_radio_rmks2 = '7.012MHz'
        with patch.object(w, '_confirm_record_time', return_value='normal'):
            w.contest_record()
        self.assertEqual(w.c_own_exchange.text(), 'ST002')
        self.assertEqual(split_for_ui(w.rows[0][1].remarks)[1], 'ST001 7.012MHz')

    def test_switching_options_does_not_advance_and_resume_keeps_band_values(self):
        self.enable()
        self.record()
        self.w.c_number_per_band.setChecked(False)
        self.w.c_band.setCurrentText('3.5')
        self.assertEqual(self.w.c_own_exchange.text(), 'ST002')
        self.record()
        self.w.c_number_per_band.setChecked(True)
        self.w.c_band.setCurrentText('7')
        self.assertEqual(self.w.c_own_exchange.text(), 'ST002')
        self.w.c_number_increment.setChecked(False)
        self.assertFalse(self.w.c_number_per_band.isEnabled())
        self.w.c_band.setCurrentText('3.5')
        self.assertEqual(self.w.c_own_exchange.text(), 'ST002')

    def test_date_year_explanation_on_standard_and_contest_pages(self):
        for page in (self.w.standard_scroll, self.w.contest_scroll):
            self.assertTrue(any('Dateで指定した年のファイルになります' in label.text()
                                for label in page.findChildren(QLabel)))


class GuidanceTests(unittest.TestCase):
    def test_bundled_notes_keep_rules_addresses_deadlines_and_drop_old_footer(self):
        for path in (ROOT/'config/rules').glob('*.txt'):
            rule = json.loads(path.read_text(encoding='utf-8-sig'))
            raw = rule.get('event', {}).get('submission', {}).get('instructions', '')
            notes = dict((label,text) for label,text,_ in overview_rows(rule))['特記事項']
            with self.subTest(path=path.name):
                self.assertNotIn('未検証', notes)
                self.assertNotIn('受領審査は未確認', notes)
                self.assertNotIn('自動提出しません', notes)
                self.assertNotIn('自動送信しません', notes)
                self.assertNotIn('原案・原典はdocs/', notes)
                import re
                for address in re.findall(r'[A-Za-z0-9_.+-]+@[A-Za-z0-9.-]+', raw):
                    self.assertIn(address, notes)
                for stamp in re.findall(r'\d{4}-\d{2}-\d{2}', raw):
                    self.assertIn(stamp, notes)

    def test_old_rule_pack_text_cleaned_without_changing_original(self):
        raw = '1種目。R1.0本文、添付不可、test@example.org、12月1日。 原案・原典はdocs/contest-researchに保存。2026参考版であり2027へ自動更新しません。主催受付・Windows実機は未検証。自動提出しません。'
        self.assertEqual(instructions(raw), '1種目。R1.0本文、添付不可、test@example.org、12月1日。')
        self.assertIn('未検証', raw)
        self.assertEqual(instructions('郵便番号未収録は県内地名と確認根拠を入力。'),
                         '郵便番号未収録は県内地名と確認根拠を入力。')


if __name__ == '__main__':
    unittest.main()
