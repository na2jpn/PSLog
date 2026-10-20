"""Display ranges in kHz; these are view limits, not transmitting permissions."""
import math
from datetime import datetime,timezone,timedelta
from collections import OrderedDict
BANDS=(('1.8',1800,2000),('3.5',3500,3800),('7',7000,7200),('10',10100,10150),('14',14000,14350),('18',18068,18168),('21',21000,21450),('24',24890,24990),('28',28000,29700),('50',50000,54000),('144',144000,146000),('430',430000,440000),('1200',1260000,1300000),('2400',2400000,2450000),('5600',5650000,5850000))
COLORS={'CW':'#1467c0','SSB':'#167340','USB':'#167340','LSB':'#167340','FM':'#803ca2','AM':'#803ca2','FT8':'#bd5700','FT4':'#b33176','RTTY':'#007b80'}
def frequency(spot):
 try:
  value=float(spot.freq)
  return value if math.isfinite(value) and value>0 else None
 except (ValueError,TypeError):return None

def stamp(spot):
 try:
  value=datetime.fromisoformat(spot.stamp)
  return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
 except (ValueError,TypeError):return datetime.min.replace(tzinfo=timezone.utc)

def abbreviation(spot,band):
 mhz=frequency(spot)/1000
 return f'{mhz-int(float(band)):.3f}'[1:] if int(mhz)==int(float(band)) else f'{mhz:.3f}'

class BandSpots:
 def __init__(self):self.items=OrderedDict()
 def add(self,spots,now=None):
  for spot in spots:
   if frequency(spot) is not None:self.items[spot.key]=spot;self.items.move_to_end(spot.key)
  from spot_display import ft_mode
  for ft in (False,True):
   keys=[key for key,s in self.items.items() if bool(ft_mode(s.mode))==ft]
   for key in keys[:-4000]:del self.items[key]
  self.expire(now)
 def expire(self,now=None):
  threshold=(now or datetime.now(timezone.utc))-timedelta(minutes=30)
  for key,spot in list(self.items.items()):
   if stamp(spot)<threshold:del self.items[key]
 def for_band(self,band,local=True,rbn=True,ft=None,region='all'):
  from spot_display import ft_mode,region_matches,ft_frequency_key
  _,low,high=next(b for b in BANDS if b[0]==band)
  selected={}
  for spot in sorted(self.items.values(),key=stamp):
   freq=frequency(spot)
   if ft is not None and bool(ft_mode(spot.mode))!=ft:continue
   if not region_matches(spot.call,region):continue
   if low<=freq<=high and ((spot.source=='RBN' and rbn) or (spot.source!='RBN' and local)):
    selected[(spot.call.upper(),ft_frequency_key(spot.freq) if ft_mode(spot.mode) else round(freq,1),ft_mode(spot.mode) or spot.mode)]=spot
  return list(selected.values())
