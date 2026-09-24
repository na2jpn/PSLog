import csv,io,tempfile,unittest
from pathlib import Path
from dataclasses import replace
from unittest.mock import patch
from model import QSO
from storage import Repository,ExternalChange,save_settings
from sota_export import select,prepare,save,key,summit,mode
from sota_ui import SotaDialog,SummitDialog
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from main import Window

class SotaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.repo=Repository(self.tmp.name)
        self.q=QSO('2026-01-01','08:59','430','FM','JA1YYY','59','59','Japan','Japan','SOTA 日本語','')
        self.path=self.repo.path_for('JH1HST/1','',self.q.date);self.repo.open(self.path).append(self.q)
    def selection(self,**kw):return select(self.repo,[self.path],'JH1HST/1',**kw)
    def rows(self,data):return list(csv.reader(io.StringIO(data.decode('ascii'))))
    def test_v2_fields_utc_boundary_and_no_original_changes(self):
        self.repo.open(self.path).append(replace(self.q,time='09:00'));raw=self.path.read_bytes();p=prepare(self.selection(),'activator','JA/ST-001');self.assertEqual(len(p.files),2)
        rows=[self.rows(v)[0] for v in p.files.values()];self.assertEqual(rows[0],['V2','JH1HST/1','JA/ST-001','31/12/25','2359','433MHz','FM','JA1YYY','','']);self.assertEqual(rows[1][3:5],['01/01/26','0000'])
        self.assertTrue(all(len(r)==10 for r in rows));self.assertEqual(raw,self.path.read_bytes())
    def test_chaser_s2s_required_and_same_summit(self):
        s=self.selection();refs={key(s.rows[0]):'JA/NN-001'}
        with self.assertRaises(ValueError):prepare(s,'chaser')
        p=prepare(s,'chaser',refs=refs);row=self.rows(next(iter(p.files.values())))[0];self.assertEqual(row[2],'');self.assertEqual(row[8],'JA/NN-001')
        with self.assertRaises(ValueError):prepare(s,'s2s','JA/NN-001',refs)
        self.assertTrue(prepare(s,'s2s','JA/ST-001',refs).files)
    def test_filters_mappings_and_comment(self):
        s=self.selection(start='202601010859',end='202601010859',remarks='sota');self.assertEqual(len(s.rows),1)
        with self.assertRaises(ValueError):self.selection(start='202601010900')
        self.assertEqual(mode('FT8 AS'),'Data');self.assertEqual(mode('FreeDV'),'DV')
        with self.assertRaises(ValueError):mode('FUTURE')
        self.assertEqual(summit('ｊａ５／ｋａ－００１'),'JA5/KA-001')
        p=prepare(s,'activator','JA/ST-001',comment='memo, "one"');self.assertTrue(p.warnings);self.assertEqual(self.rows(next(iter(p.files.values())))[0][-1],"memo_ 'one'")
        with self.assertRaises(ValueError):prepare(s,'activator','JA/ST-001',comment='日本語')
    def test_nonoverwrite_stale_and_save_failure(self):
        p=prepare(self.selection(),'activator','JA/ST-001');a=save(p,self.tmp.name);b=save(p,self.tmp.name);self.assertNotEqual(a,b);self.assertEqual(a[0].read_bytes(),b[0].read_bytes())
        self.path.write_bytes(self.path.read_bytes()+b'\n')
        with self.assertRaises(ExternalChange):save(p,self.tmp.name)
    def test_editor_pagination_empty_only_and_cancel(self):
        for i in range(101):self.repo.open(self.path).append(replace(self.q,call='JA2YYY'))
        s=self.selection();refs={key(s.rows[0]):'JA/NN-001'};d=SummitDialog(s,refs);d.check_all(True);d.bulk.setText('JA/ST-002');d.fill_blank()
        self.assertEqual(d.table.rowCount(),100);self.assertEqual(d.draft[key(s.rows[0])],'JA/NN-001');d.move(1);self.assertEqual(d.table.rowCount(),2)
        d.reject();self.assertEqual(len(refs),1);d.apply();self.assertEqual(len(d.result_refs),102);d.close()
    def test_ui_selection_invalidation_export_and_menu(self):
        d=SotaDialog(self.repo,'JH1HST/1');d.check_all(True);d.load_rows();self.assertIsNotNone(d.selection);d.own_ref.setText('JA/ST-001');d.write();self.assertEqual(len(list((Path(self.tmp.name)/'output'/'sota').glob('*.csv'))),1)
        d.rmks.setText('SOTA');self.assertIsNone(d.selection);self.assertFalse(d.save_button.isEnabled());d.close()
        save_settings(self.tmp.name,{'own':'JH1HST'});w=Window(self.tmp.name)
        with patch('sota_ui.SotaDialog') as dialog:
            a=next(a for a in w.action_refs if a.text()=='SOTA提出用CSVファイル');self.assertTrue(a.isEnabled());a.trigger();self.assertTrue(dialog.return_value.exec.called)
        w.close()
