import unittest
from preferences import validate
from radio_control import (
    ICOM_MODELS,HAMLIB_MODELS,CUSTOM_ICOM,CUSTOM_HAMLIB,
    infer_radio_model,normalized_radio_settings,radio_model_profile,
)

class RadioSettingsFix1Tests(unittest.TestCase):
    def test_never_configured_default_does_not_fake_ic7300(self):
        self.assertEqual(infer_radio_model({'radio_enabled':False,'radio_method':'CI-V','radio_civ_address':'94','radio_port':'AUTO'}),'')

    def test_legacy_enabled_settings_are_migrated_to_model(self):
        self.assertEqual(infer_radio_model({'radio_enabled':True,'radio_method':'CI-V','radio_civ_address':'A4','radio_port':'COM8'}),'IC-705')
        self.assertEqual(infer_radio_model({'radio_enabled':True,'radio_method':'Hamlib','radio_hamlib_model':'1035'}),'FT-991 / FT-991A')
        self.assertEqual(infer_radio_model({'radio_enabled':True,'radio_method':'CI-V','radio_civ_address':'AA'}),CUSTOM_ICOM)
        self.assertEqual(infer_radio_model({'radio_enabled':True,'radio_method':'Hamlib','radio_hamlib_model':'9999'}),CUSTOM_HAMLIB)

    def test_known_models_fill_backend_values(self):
        ic=normalized_radio_settings({'radio_enabled':True,'radio_model':'IC-705','radio_method':'Hamlib','radio_civ_address':'00','radio_hamlib_model':'999','radio_port':'COM8','radio_baud':'AUTO'})
        self.assertEqual(ic['radio_method'],'CI-V');self.assertEqual(ic['radio_civ_address'],'A4');self.assertEqual(ic['radio_hamlib_model'],'')
        ft=normalized_radio_settings({'radio_enabled':True,'radio_model':'FT-991 / FT-991A','radio_method':'CI-V','radio_civ_address':'94','radio_port':'COM9','radio_baud':38400})
        self.assertEqual(ft['radio_method'],'Hamlib');self.assertEqual(ft['radio_hamlib_model'],'1035');self.assertEqual(ft['radio_civ_address'],'')

    def test_auto_port_and_baud_are_valid_preferences(self):
        values=validate({'radio_port':'AUTO','radio_baud':'AUTO','radio_model':'IC-7300'})
        self.assertEqual(values['radio_port'],'AUTO');self.assertEqual(values['radio_baud'],'AUTO')
        with self.assertRaises(ValueError):validate({'radio_baud':'12345'})

    def test_reference_model_tables_include_expected_radios(self):
        self.assertEqual(ICOM_MODELS['IC-7300'],0x94)
        self.assertEqual(ICOM_MODELS['IC-7300MK2'],0xB6)
        self.assertEqual(ICOM_MODELS['IC-905'],0xAC)
        self.assertEqual(HAMLIB_MODELS['FT-991 / FT-991A'],1035)
        self.assertEqual(HAMLIB_MODELS['FTX-1'],1051)
        self.assertEqual(HAMLIB_MODELS['TS-590SG'],2037)

if __name__=='__main__':unittest.main()
