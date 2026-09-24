import unittest,tempfile
from pathlib import Path
import xml.etree.ElementTree as ET
from importing import prepare
from storage import Repository,save_settings
from locations import load,confirmed
from location_overrides import Overrides

class AdifLocationTests(unittest.TestCase):
    def run_import(self,root,qth,code='',call='JA1AAA',country=''):
        node=ET.Element('ADX');record=ET.SubElement(ET.SubElement(node,'RECORDS'),'RECORD')
        for k,v in dict(CALL=call,QSO_DATE='20260911',TIME_ON='0000',MODE='CW',BAND='40m',QTH_INTL=qth,GRIDSQUARE='PM95',COMMENT='BURO',COUNTRY=country).items():ET.SubElement(record,k).text=v
        if code:ET.SubElement(record,'APP',PROGRAMID='PSLOG',FIELDNAME='JCCJCG').text=code
        source=Path(root)/'input.adx';source.write_bytes(ET.tostring(node,encoding='utf-8'))
        plan=prepare(Repository(root),source,'JH1HST');self.assertFalse(plan.log.issues);return plan.log.records[0][1]
    def test_confirmed_gun_and_original_remark(self):
        with tempfile.TemporaryDirectory() as root:
            q=self.run_import(root,'徳島県板野郡上板町','JCG 37002C')
            self.assertEqual(q.his_qth,'Kamiita Itanogun Tokushima Japan PM95');self.assertIn('BURO QTH:徳島県板野郡上板町',q.remarks);self.assertEqual(q.code,'JCG 37002C')
            q=self.run_import(root,'徳島県板野郡上板町','JCC 37002C');self.assertEqual(q.his_qth,'Japan PM95')
    def test_unmatched_off_and_foreign_conflict(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertEqual(self.run_import(root,'未登録所在地').his_qth,'Japan PM95')
            self.assertEqual(self.run_import(root,'埼玉県草加市',country='France').his_qth,'France PM95')
            self.assertEqual(self.run_import(root,'未登録所在地',call='JH1HST/JD1').his_qth,'PM95')
            save_settings(root,{'location_assist':False})
            q=self.run_import(root,'埼玉県草加市');self.assertEqual(q.his_qth,'埼玉県草加市 PM95');self.assertEqual(q.remarks,'BURO')
    def test_user_confirmed_spelling_is_reused(self):
        with tempfile.TemporaryDirectory() as root:
            row=next(r for r in load(root)['rows'] if r['name']=='東京都足立区')
            Overrides(root).remember(row,'Adachi Tokyo Japan')
            self.assertEqual(self.run_import(root,row['name'],'JCC 100121').his_qth,'Adachi Tokyo Japan PM95')
