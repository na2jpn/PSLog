"""Display grouping only: no inference of operating mode from frequency."""
import re
from decimal import Decimal, ROUND_HALF_UP
from collections import defaultdict
from band_site import frequency,stamp
from cluster_monitor import valid_token
_JA=re.compile(r'(?:(?:J[A-S])\d|[78][J-N]\d)[A-Z0-9]+')
def ft_mode(mode):
 match=re.search(r'\bFT[48]\b',str(mode).upper());return match[0] if match else None

def station_region(call):
 """Callsign classification, including explicit portable prefixes; unknown is None."""
 call=str(call).strip().upper()
 if not valid_token(call,'call'):return None
 parts=call.split('/')
 if any(p in ('MM','AM') for p in parts[1:]):return None
 meaningful=[p for p in parts if p not in ('P','QRP','QRO') and not p.isdigit()]
 if not meaningful:return None
 if len(meaningful)==1:return 'ja' if _JA.fullmatch(meaningful[0]) else 'dx'
 # A shorter prefix on either side explicitly identifies the operation area.
 prefixes=[p for p in meaningful if len(p)<=4]
 if len(prefixes)!=1:return None
 prefix=prefixes[0]
 return 'ja' if re.fullmatch(r'J[A-S]\d?|[78][J-N]\d',prefix) else 'dx'

def region_matches(call,selection):return selection=='all' or station_region(call)==selection

def ft_frequency_key(freq_khz):
 return int((Decimal(str(freq_khz))/1000).quantize(Decimal("0.01"),rounding=ROUND_HALF_UP)*1000)

def ft_groups(spots):
 """One card per MHz rounded to two decimals and mode, one newest row per call."""
 groups=defaultdict(dict)
 for s in sorted(spots,key=stamp):
  mode=ft_mode(s.mode);freq=frequency(s)
  if mode and freq is not None:groups[(ft_frequency_key(s.freq),mode)][s.call.upper()]=s
 return {key:sorted(sorted(rows.values(),key=lambda s:s.call),key=stamp,reverse=True) for key,rows in sorted(groups.items())}
