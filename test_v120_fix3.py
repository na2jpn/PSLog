import unittest
from dataclasses import replace
from datetime import datetime,timezone,timedelta
from cluster_monitor import Spot
from spot_display import ft_groups,ft_frequency_key
from band_site import BandSpots
class Fix3Tests(unittest.TestCase):
 def test_rounding_boundary(self):
  self.assertEqual(ft_frequency_key('7074.0'),7070)
  self.assertEqual(ft_frequency_key('7074.1'),7070)
  self.assertEqual(ft_frequency_key('7075'),7080)
 def test_latest_original_frequency_retained(self):
  now=datetime.now(timezone.utc)
  a=Spot('RBN','',now.isoformat(),'JX1XXX','7074.0','FT8','')
  b=replace(a,freq='7074.1',stamp=(now+timedelta(seconds=1)).isoformat())
  self.assertEqual(ft_groups([a,b])[(7070,'FT8')],[b])
  store=BandSpots();store.add([a,b]);self.assertEqual(store.for_band('7',ft=True),[b])
if __name__=='__main__':unittest.main()
