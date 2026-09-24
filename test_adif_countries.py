import unittest,tempfile
from pathlib import Path
from countries import load
from adif_import import convert
from importing import prepare
from storage import Repository,save_settings

class AdifCountryTests(unittest.TestCase):
    def adi(self,**extra):
        fields=dict(CALL='DL5TI',QSO_DATE='20260911',TIME_ON='0000',BAND='40m',MODE='CW',GRIDSQUARE='JO62')
        fields.update(extra)
        return (''.join(f'<{k}:{len(v)}>{v}' for k,v in fields.items())+'<EOR>').encode()
    def test_blank_qth_hint_and_grid_preserved(self):
        data=load(Path(__file__).parent)
        log,_=convert(self.adi(),'adi','JH1HST',country_data=data)
        self.assertFalse(log.issues);self.assertEqual(log.records[0][1].his_qth,'Fed. Rep. of Germany JO62')
        self.assertTrue(any('国名候補' in x.reason for x in log.notices))
        log,_=convert(self.adi(QTH='Berlin'),'adi','JH1HST',country_data=data)
        self.assertEqual(log.records[0][1].his_qth,'Berlin JO62')
    def test_explicit_country_and_ambiguous_operation(self):
        data=load(Path(__file__).parent)
        log,_=convert(self.adi(COUNTRY='France'),'adi','JH1HST',country_data=data)
        q=log.records[0][1];self.assertEqual(q.his_qth,'France JO62');self.assertIn('France',q.remarks)
        log,_=convert(self.adi(CALL='JH1HST/JD1',GRIDSQUARE='QL17'),'adi','JH1HST',country_data=data)
        self.assertEqual(log.records[0][1].his_qth,'QL17')
    def test_import_setting_off_and_on(self):
        with tempfile.TemporaryDirectory() as root:
            repo=Repository(root);source=Path(root)/'source.adi';source.write_bytes(self.adi())
            save_settings(root,{'location_assist':False})
            plan=prepare(repo,source,'JH1HST');self.assertEqual(plan.log.records[0][1].his_qth,'JO62')
            save_settings(root,{'location_assist':True})
            plan=prepare(repo,source,'JH1HST');self.assertEqual(plan.log.records[0][1].his_qth,'Fed. Rep. of Germany JO62')
