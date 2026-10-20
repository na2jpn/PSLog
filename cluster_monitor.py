"""Read-only spot adapters, exact region matching and bounded duplicate suppression."""
from dataclasses import dataclass
from collections import OrderedDict
from datetime import datetime,timedelta,timezone
from decimal import Decimal,InvalidOperation
from xml.etree import ElementTree as ET
import re,threading,time,unicodedata
from internet_common import request_bytes,InternetError
from logbook_sources import base_station_call

LOCAL_URL='https://qrv.jp/xml/All100.xml'
MIN_INTERVAL=300

@dataclass(frozen=True)
class Spot:
 source:str
 ident:str
 stamp:str
 call:str
 freq:str
 mode:str
 code:str=''
 qth:str=''
 reporter:str=''
 comment:str=''
 @property
 def key(self):return (self.source,self.ident) if self.ident else (self.source,self.stamp,self.call,self.freq,self.mode)

def tokens(text):return [t for t in re.split(r'[,，、;；\s]+',unicodedata.normalize('NFKC',text).strip().upper()) if t]
def valid_token(token,kind):
 return bool(re.fullmatch(r'\d{4}|\d{6}|\d{5}[A-Z]?',token) if kind=='code' else re.fullmatch(r'(?=[A-Z0-9/]*[A-Z])(?=[A-Z0-9/]*\d)[A-Z0-9]+(?:/[A-Z0-9]+)*',token))
def region_matches(wanted,actual):
 actual=actual.upper().strip()
 return wanted==actual or (len(wanted)==5 and wanted.isdigit() and bool(re.fullmatch(re.escape(wanted)+r'[A-Z]',actual)))
def matches(spot,calls,codes):
 return any(c==spot.call or ('/' not in c and base_station_call(spot.call)==c) for c in calls) or (spot.source!='RBN' and any(region_matches(c,spot.code) for c in codes))

class MonitorState:
 def __init__(self):self.calls=();self.codes=();self.seen=OrderedDict()
 def set_filters(self,calls,codes):self.calls=tuple(calls);self.codes=tuple(codes)
 def matching(self,spots):return [s for s in spots if matches(s,self.calls,self.codes)]
 def fresh(self,spots):
  out=[]
  for s in spots:
   if s.key in self.seen:continue
   self.seen[s.key]=None;out.append(s)
   if len(self.seen)>20000:self.seen.popitem(last=False)
  return out

class PollGate:
 """Also protects rapid stop/start and reopen in the same app process."""
 def __init__(self):self.next_at=0.;self.failures=0;self.lock=threading.Lock()
 def claim(self,now=None):
  now=time.monotonic() if now is None else now
  with self.lock:
   if now<self.next_at:return False
   self.next_at=now+MIN_INTERVAL;return True
 def remaining(self):return max(0,self.next_at-time.monotonic())
 def failed(self,retry_after=0):
  with self.lock:
   self.failures+=1;delay=max(MIN_INTERVAL*min(2**min(self.failures,4),16),min(retry_after,86400))
   self.next_at=max(self.next_at,time.monotonic()+delay)
 def succeeded(self):self.failures=0
POLL_GATE=PollGate()

def _frequency(value):
 try:
  number=Decimal(value.replace(',','').strip())
  if not number.is_finite() or number<=0:raise ValueError('周波数が不正です')
  return format(number,'f')
 except InvalidOperation as e:raise ValueError('周波数が不正です: '+value) from e

def parse_local(raw):
 if len(raw)>2_000_000:raise ValueError('応答が2MBを超えています')
 declaration=raw[:160].decode('ascii',errors='ignore')
 enc=re.search(r'encoding=["\']([^"\']+)',declaration,re.I)
 encoding=enc[1].lower() if enc else 'utf-8-sig'
 if encoding not in ('shift_jis','shift-jis','sjis','utf-8','utf8','utf-8-sig'):raise ValueError('未対応のXML文字コード: '+encoding)
 text=raw.decode('cp932' if encoding in ('shift_jis','shift-jis','sjis') else 'utf-8-sig')
 if re.search(r'<!ENTITY',text,re.I):raise ValueError('外部・独自エンティティを含むXMLには対応しません')
 root=ET.fromstring(text)
 if root.tag!='List':raise ValueError('国内スポットの応答形式がListではありません')
 out=[]
 for row in root.findall('Spot')[:1000]:
  def value(path):return (row.findtext(path) or '').strip()
  call=value('SpotStation/CallSign').upper()
  if not valid_token(call,'call'):continue
  day=value('Date').replace('/','-');hour=value('Time');zone=value('TimeZone') or '+9:00'
  z=re.fullmatch(r'([+-])(\d{1,2}):(\d{2})',zone)
  if not z:raise ValueError('不明なタイムゾーン: '+zone)
  tz=timezone(timedelta(minutes=(1 if z[1]=='+' else -1)*(int(z[2])*60+int(z[3]))))
  stamp=datetime.fromisoformat(day+'T'+hour).replace(tzinfo=tz).astimezone(timezone.utc).isoformat()
  message=row.find('Message');comment=''.join(message.itertext()) if message is not None else ''
  out.append(Spot('国内',row.get('ID',''),stamp,call,_frequency(value('Freq')),value('Mode'),value('SpotStation/QthID').upper(),' '.join(value('SpotStation/'+n) for n in ('QthName1','QthName2','QthName3')).strip(),value('ReportStation/CallSign'),comment))
 return out

def fetch_local(opener=None):return parse_local(request_bytes(LOCAL_URL,'application/xml,text/xml',opener))

def parse_rbn(line,now=None):
 # Receiver identity is deliberately excluded from the duplicate key.
 m=re.search(r'DX de\s+(\S+):\s*([\d.]+)\s+(\S+)\s+(.*?)\s+(\d{4})Z\b',line)
 if not m:return None
 reporter,freq,call,comment,clock=m.groups();call=call.upper()
 if not valid_token(call,'call'):return None
 now=now or datetime.now(timezone.utc);hour=int(clock[:2]);minute=int(clock[2:])
 if hour>23 or minute>59:return None
 stamp=now.replace(hour=hour,minute=minute,second=0,microsecond=0)
 if stamp-now>timedelta(hours=12):stamp-=timedelta(days=1)
 if now-stamp>timedelta(hours=12):stamp+=timedelta(days=1)
 mode=next((v for v in ('CW','RTTY','FT8','FT4') if re.search(r'\b'+v+r'\b',comment)), '')
 return Spot('RBN','',stamp.isoformat(),call,_frequency(freq),mode,reporter=reporter,comment=comment)
