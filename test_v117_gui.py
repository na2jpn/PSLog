"""End-to-end contest state, portable searches and unsaved external-edit recovery."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from PySide6.QtWidgets import QApplication, QMessageBox
from main import Window
from model import QSO, now_jst
from remarks_sections import split_for_ui
from search_ui import SearchDialog
from session_state import contest_session
from storage import Repository, save_settings


class UI117Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        save_settings(self.tmp.name,{'own':'JH1HST','confirm_record':False})
        self.w=Window(self.tmp.name);self.addCleanup(self.w.close)
        self.time_patch=patch.object(self.w,'_confirm_record_time',return_value='normal');self.time_patch.start();self.addCleanup(self.time_patch.stop)
        n=now_jst();self.date=n.strftime('%Y-%m-%d');self.ym=n.strftime('%Y%m')
        self.q=QSO(self.date,n.strftime('%H:%M'),'7','CW','JA1AAA','599','599','Japan','Chiba','1201')

    def contest(self,name='CHIBA',call='JH1HST/1'):
        self.w._save_active_workspace_state()
        self.w.workspace_sessions.append(contest_session(name,self.ym,call,'7','CW','Chiba'))
        i=len(self.w.workspace_sessions)-1;self.w._rebuild_session_tabs();self.switch(i)
        return i

    def switch(self,i):
        self.w._save_active_workspace_state();self.w._load_workspace(i)

    def enter(self,call='JA1AAA',exchange='1201'):
        self.w.c_call.setText(call);self.w.contest_start_qso();self.w.c_exchange.setText(exchange)

    def path(self):return self.w.repo.path_for(*self.w.station,self.date)

    def test_own_number_kept_after_record_and_per_tab_restart(self):
        a=self.contest();self.w.c_own_exchange.setText('１２０１Ｌ')
        self.enter();self.w.contest_record();p=self.path()
        self.assertEqual(self.w.c_own_exchange.text(),'1201L')
        self.assertEqual(split_for_ui(self.w.repo.open(p).log.records[0][1].remarks)[:2],('1201','1201L'))
        self.enter('JA1BBB','1301');self.w.contest_record()
        self.assertEqual([split_for_ui(q.remarks)[1] for _,q in self.w.repo.open(p).log.records],['1201L','1201L'])
        b=self.contest('TOKYO');self.assertEqual(self.w.c_own_exchange.text(),'')
        self.w.c_own_exchange.setText('1001L');self.switch(a)
        self.assertEqual(self.w.c_own_exchange.text(),'1201L');self.switch(b)
        self.assertEqual(self.w.c_own_exchange.text(),'1001L')
        self.w.persist_settings();self.w.close()
        reopened=Window(self.tmp.name);self.addCleanup(reopened.close)
        reopened._load_workspace(a);self.assertEqual(reopened.c_own_exchange.text(),'1201L')
        reopened._load_workspace(b);self.assertEqual(reopened.c_own_exchange.text(),'1001L')

    def test_radio_frequency_preserves_own_number_without_leaking_between_tabs(self):
        a=self.contest();self.w.c_own_exchange.setText('1201L');self.w.radio_rmks2.setChecked(True)
        state=SimpleNamespace(connected=True,frequency_hz=7012000)
        with patch.object(self.w.radio_manager,'state',return_value=state):self.enter()
        self.w.contest_record()
        rmks2=split_for_ui(self.w.repo.open(self.path()).log.records[0][1].remarks)[1]
        self.assertEqual(rmks2,'1201L 7.012');self.assertEqual(self.w.c_own_exchange.text(),'1201L')
        self.w._contest_radio_rmks2='7.099 ';self.contest('TOKYO')
        self.assertEqual(self.w._contest_radio_rmks2,'');self.assertEqual(self.w.c_own_exchange.text(),'')
        self.switch(a);self.assertEqual(self.w.c_own_exchange.text(),'1201L')

    def test_portable_current_log_selects_base_and_keeps_exact_file_filter(self):
        self.contest();self.enter();self.w.contest_record();path=self.path()
        d=SearchDialog(self.w.repo,'JH1HST/1',filename=path.name);self.addCleanup(d.close)
        self.assertEqual(d.filters['own'].currentText(),'JH1HST');d.run_search()
        self.assertEqual(len(d.result_hits),1)
        self.assertEqual(d.result_hits[0].path,path)
        d.portable.setChecked(False);d.run_search();self.assertEqual(len(d.result_hits),0)

    def test_search_dialog_discovers_new_calls_and_files_while_open(self):
        d=SearchDialog(self.w.repo,'JH1HST');self.addCleanup(d.close);d.run_search()
        path=self.w.repo.path_for('JH1HST','',self.date);self.w.repo.open(path).append(self.q)
        other=self.w.repo.path_for('JQ7FIU','',self.date);self.w.repo.open(other).append(self.q)
        d.run_search();self.assertEqual(len(d.result_hits),1)
        self.assertGreaterEqual(d.filters['own'].findText('JQ7FIU'),0)
        d.filters['own'].setCurrentText('JQ7FIU');d.run_search();self.assertEqual(len(d.result_hits),1)
        self.assertEqual(d.result_hits[0].path,other)

    def test_actual_manual_merge_flow_preserves_input_and_all_five_records(self):
        self.contest(call='JH1HST');self.enter();self.w.contest_record();old=self.path()
        self.w.c_own.setText('JH1HST/1');self.w.set_contest_station()
        self.enter('JA1BBB');self.w.contest_record();path=self.path()
        path.write_bytes(path.read_bytes()+old.read_bytes().removeprefix(b'\xef\xbb\xbf'))
        merged=path.read_bytes();old.unlink()
        self.enter('JA1CCC');self.w.c_own_exchange.setText('1201L')
        self.assertIn('JA1AAA',[q.call for _,q in self.w.rows])
        with patch('main.QMessageBox.question',return_value=QMessageBox.StandardButton.Yes) as ask:
            self.w.contest_record()
        ask.assert_called_once();self.assertEqual(path.read_bytes(),merged)
        self.assertEqual(self.w.c_call.text(),'JA1CCC');self.assertEqual(self.w.c_exchange.text(),'1201')
        self.assertEqual(self.w.c_own_exchange.text(),'1201L');self.assertIn('未記録',self.w.c_status.text())
        for call in ('JA1CCC','JA1DDD','JA1EEE'):
            if call!='JA1CCC':self.enter(call)
            self.w.contest_record()
        self.assertEqual({q.call for _,q in self.w.repo.open(path).log.records},{'JA1AAA','JA1BBB','JA1CCC','JA1DDD','JA1EEE'})
        self.assertIn(merged,[p.read_bytes() for p in self.w.repo.backups(path)])
        self.assertFalse(old.exists())

    def test_cancel_external_reload_keeps_original_input_and_file(self):
        self.contest();self.enter();self.w.contest_record();path=self.path()
        external=path.read_bytes()+replace(self.q,call='JA1ZZZ').to_ps().encode()+b'\r\n';path.write_bytes(external)
        self.enter('JA1BBB')
        with patch('main.QMessageBox.question',return_value=QMessageBox.StandardButton.No):self.w.contest_record()
        self.assertEqual(path.read_bytes(),external);self.assertEqual(self.w.c_call.text(),'JA1BBB')
        self.assertEqual(self.w.c_exchange.text(),'1201')

    def test_invalid_external_file_cannot_clear_input_or_be_overwritten(self):
        self.contest();self.enter();self.w.contest_record();path=self.path()
        external=path.read_bytes()+b'bad external row\r\n';path.write_bytes(external);self.enter('JA1BBB')
        with patch('main.QMessageBox.question',return_value=QMessageBox.StandardButton.Yes),patch('main.QMessageBox.warning') as warning:
            self.w.contest_record()
        warning.assert_called_once();self.assertEqual(path.read_bytes(),external)
        self.assertEqual(self.w.c_call.text(),'JA1BBB');self.assertEqual(self.w.c_exchange.text(),'1201')

    def test_deleted_log_requires_reload_and_does_not_revive_old_qsos(self):
        self.contest();self.enter();self.w.contest_record();path=self.path();path.unlink();self.enter('JA1BBB')
        with patch('main.QMessageBox.question',return_value=QMessageBox.StandardButton.Yes):self.w.contest_record()
        self.assertFalse(path.exists());self.assertEqual(self.w.rows,[])
        self.w.contest_record()
        self.assertEqual([q.call for _,q in self.w.repo.open(path).log.records],['JA1BBB'])

    def test_set_and_tab_switch_read_external_file_without_writing_it(self):
        a=self.contest();self.enter();self.w.contest_record();path=self.path()
        external=path.read_bytes()+replace(self.q,call='JA1ZZZ').to_ps().encode()+b'\r\n';path.write_bytes(external)
        self.w.set_contest_station();self.assertEqual(path.read_bytes(),external)
        self.assertIn('JA1ZZZ',[q.call for _,q in self.w.rows])
        b=self.contest('TOKYO');self.switch(a)
        self.assertEqual(path.read_bytes(),external);self.assertIn('JA1ZZZ',[q.call for _,q in self.w.rows])
        self.switch(b);self.assertEqual(path.read_bytes(),external)

    def test_standard_and_easy_histories_discover_external_additions(self):
        path=self.w.repo.path_for('JH1HST','',self.date);path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(('\ufeff'+self.q.to_ps()+'\r\n').encode())
        self.w.call.setText(self.q.call);self.w.search()
        self.assertEqual(len(self.w._standard_history_visible),1)
        self.w._add_easy_workspace();self.w.e_call.setText(self.q.call);self.w.easy_search()
        self.assertEqual(len(self.w._easy_history_visible),1)
        path.unlink();self.w.easy_search();self.assertEqual(self.w._easy_history_visible,[])


if __name__=='__main__':unittest.main()
