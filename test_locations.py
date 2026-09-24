import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import unittest,tempfile
from unittest.mock import patch
from PySide6.QtWidgets import QApplication,QMessageBox,QDialog
from locations import load,find,candidates,confirmed,exact_matches
from location_ui import LocationDialog
from storage import save_settings
from main import Window
from hamlog_import import convert
from test_hamlog_import import BASE,csvbytes
class LocationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def test_codes_confirmed_and_gun(self):
        data=load('/not-a-data-root')
        self.assertEqual(len(data['rows']),1899)
        for term,qth in [('足立区','Adachi Tokyo Japan'),('草加市','Soka Saitama Japan'),('上板町','Kamiita Itanogun Tokushima Japan')]:
            row=find(data,term)[0];self.assertEqual(row['verified_qth'],qth);self.assertEqual(confirmed(data,row['name'],row['source_code']),qth)
        row=find(data,'上板町')[0];self.assertEqual(len(row['code']),5);self.assertTrue(row['source_code'][-1].isalpha())
        self.assertIsNone(confirmed(data,'東京都足立区','9999'))
    def test_unverified_prefilled_and_immediately_applicable(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=LocationDialog(tmp,'東京都墨田区');d.table.selectRow(0)
            self.assertEqual(d.qth.currentText(),'Sumida Tokyo Japan')
            self.assertTrue(d.apply_button.isEnabled())
            d.apply();self.assertEqual(d.result_value[0],'Sumida Tokyo Japan')
    def test_main_my_qth_and_gl_and_off(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_settings(tmp,{'own':'JH1HST'});w=Window(tmp);w.set_text('code','JCC 100121');w.set_text('my_qth','PM95 old')
            with patch('location_ui.LocationDialog') as factory,patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.Yes):
                factory.return_value.exec.return_value=QDialog.DialogCode.Accepted;factory.return_value.result_value=('Soka Saitama Japan','1321')
                w.location('my_qth')
            self.assertEqual(w.text('my_qth'),'PM95 Soka Saitama Japan');self.assertEqual(w.text('code'),'JCC 100121')
            w.location_on.setChecked(False);self.assertFalse(w.location_button.isEnabled());self.assertFalse(w.my_location_button.isEnabled());w.close()
            w=Window(tmp);self.assertFalse(w.location_on.isChecked());w.close()

    def test_inline_his_qth_exact_match_autofills_code_without_overwriting_manual_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_settings(tmp,{'own':'JH1HST'});w=Window(tmp)
            w.location_on.setChecked(True)
            w.set_text('his_qth','Soka Saitama Japan');w.set_text('code','');w.his_qth_suggest._exact()
            self.assertEqual(w.text('code'),'1321')
            w.set_text('code','9999');w.set_text('his_qth','埼玉県草加市');w.his_qth_suggest._exact()
            self.assertEqual(w.text('code'),'9999')
            self.assertEqual(exact_matches(w.his_qth_suggest.data,'埼玉県草加市')[0]['code'],'1321')
            w.close()

    def test_csv_only_confirmed_full_name(self):
        data=load('/not-a-data-root');row=BASE.copy();place=find(data,'草加市')[0];row[7]=place['source_code']
        log,_=convert(csvbytes([row]),location_data=data);self.assertIn('Soka Saitama Japan',log.records[0][1].his_qth);self.assertIn('埼玉県草加市',log.records[0][1].remarks)
        row[11]='草加市';log,_=convert(csvbytes([row]),location_data=data);self.assertNotIn('Soka',log.records[0][1].his_qth)
