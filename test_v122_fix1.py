"""Location requirements follow operation circumstances, not empty declarations."""
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from PySide6.QtWidgets import QApplication,QCheckBox
from contest_locations import check
from contest_rules import score
from contest_submit_ui import SubmissionPane
from contest_event_ui import EventDialog
from test_all_osaka_2026 import r,row,ctx

class LocationFixTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
 def test_stationary_osaka_blank_locations_scores(self):
  spec=r();v=ctx(spec,'CM');v.pop('operating_locations');self.assertEqual(score(spec,[row()],v).total,1)
 def test_digital_mismatch_still_blocked_in_2026(self):
  spec=r();v=ctx(spec,'RTTY');v['operating_locations']['digital']='埼玉県草加市';self.assertIsNone(score(spec,[row(mode='RTTY',time='12:00')],v).total)
 def test_invalid_location_text_still_rejected(self):
  spec=r();v=ctx(spec,'CM');v['operating_locations']['cw']='<bad>'
  with self.assertRaises(ValueError):check(spec['event'],{'location_group':'cw'},v)
 def test_old_explicit_match_condition_preserved(self):
  event={'operating_locations':{'groups':{'cw':'電信','digital':'デジタル'},'matches':{'digital':['cw']}}}
  with self.assertRaises(ValueError):check(event,{'location_group':'digital'},{'operating_locations':{'cw':'A','digital':'B'}})
 def test_dialog_explains_optional_locations(self):
  spec=r();d=EventDialog(spec['event'],ctx(spec,'CM'));self.assertIn('任意',d.locations['cw'].placeholderText());d.deleteLater()
 def fake_pane(self,kind='HOME',confirmed=False,place='',own='JX1XXX',portable=False):
  # Exercise prepare's actual UI guards, stopping before output construction.
  info={'opplace':place,'portable':portable,'fd_location_confirmed':confirmed}
  wizard=SimpleNamespace(rule_path=None,rule_snapshot=None,rule={'event':{'station_factor':'jarl_fd'}},selection=SimpleNamespace(rows=[(own,None)]),event_context=lambda:{'fd_class':kind})
  return SimpleNamespace(invalidate=lambda:None,wizard=wizard,current_format='JARL R1.0',club_match=None,info=lambda:info,set_status=lambda *args,**kwargs:None)
 def test_fd_unchecked_confirmation_blocks_preparation(self):
  p=self.fake_pane()
  with patch('contest_submit_ui.check_jarl_official_required') as gate:
   SubmissionPane.prepare(p);gate.assert_not_called()
 def test_fd_home_confirmed_allows_blank_location(self):
  p=self.fake_pane(confirmed=True)
  with patch('contest_submit_ui.check_jarl_official_required',side_effect=ValueError('stop after guards')) as gate:
   SubmissionPane.prepare(p);gate.assert_called_once()
 def test_portable_requires_location_even_if_confirmed(self):
  for own,flag in [('JX1XXX/1',False),('JX1XXX',True)]:
   p=self.fake_pane(kind='B',confirmed=True,own=own,portable=flag)
   with patch('contest_submit_ui.check_jarl_official_required') as gate:
    SubmissionPane.prepare(p);gate.assert_not_called()
 def test_portable_with_location_passes_ui_guards(self):
  p=self.fake_pane(kind='B',confirmed=True,place='埼玉県草加市',own='JX1XXX/1')
  with patch('contest_submit_ui.check_jarl_official_required',side_effect=ValueError('stop after guards')) as gate:
   SubmissionPane.prepare(p);gate.assert_called_once()
if __name__=='__main__':unittest.main()
