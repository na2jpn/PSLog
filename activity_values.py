"""Pure band/mode helpers shared by activity filters and non-GUI logic."""
import unicodedata
BANDS=('3.5以下','7','10','14','18','21','24','28','50','144','430','1200以上')
MODES=('FM/SSB/AM','CW','FT*','その他')
def norm(s):return unicodedata.normalize('NFKC',str(s)).strip().upper()
def band_value(s):
 s=norm(s).replace('MHZ','').replace('GHZ','G').replace('KHZ','K')
 try:return float(s[:-1])*({'G':1000,'K':.001}[s[-1]]) if s[-1:] in ('G','K') else float(s)
 except (ValueError,KeyError):return None
def band_group(s):
 v=band_value(s)
 if v is None:return None
 if v<=3.8:return BANDS[0]
 if v>=1200:return BANDS[-1]
 return {'29':'28','433':'430'}.get(str(int(v)),str(int(v)))
def mode_group(s):
 s=norm(s)
 if s in ('FM','SSB','AM','USB','LSB'):return MODES[0]
 if s=='CW':return 'CW'
 if s.startswith('FT'):return 'FT*'
 return 'その他'
