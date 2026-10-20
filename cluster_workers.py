"""Network threads with cooperative stop; never touch GUI widgets."""
import socket,time,threading,re
from PySide6.QtCore import QThread,Signal
from cluster_monitor import fetch_local,parse_rbn,POLL_GATE
from internet_common import InternetError

# DNS resolution is not covered by socket timeouts on every OS. Bound the
# caller's wait and close late results; keep at most one pending dial per host.
_PENDING_DIALS=set()
_DIAL_LOCK=threading.Lock()
def bounded_connect(address,stop_event,timeout=15,connector=socket.create_connection):
 key=tuple(address);done=threading.Event();lock=threading.Lock();state={'cancelled':False}
 with _DIAL_LOCK:
  if key in _PENDING_DIALS or len(_PENDING_DIALS)>=8:raise TimeoutError('前の名前解決・接続処理が終了していません')
  _PENDING_DIALS.add(key)
 def dial():
  sock=None
  try:
   sock=connector(address,timeout=timeout)
   with lock:
    if state['cancelled']:sock.close()
    else:state['sock']=sock
  except Exception as e:
   with lock:state['error']=e
  finally:
   with _DIAL_LOCK:_PENDING_DIALS.discard(key)
   done.set()
 threading.Thread(target=dial,daemon=True,name='PSLog-RBN-connect').start();deadline=time.monotonic()+timeout
 while not done.wait(.05):
  if stop_event.is_set() or time.monotonic()>=deadline:
   with lock:
    state['cancelled']=True
    if state.get('sock'):state.pop('sock').close()
   raise TimeoutError('接続を停止しました' if stop_event.is_set() else '名前解決・接続の合計15秒タイムアウト')
 with lock:
  if stop_event.is_set():
   if state.get('sock'):state.pop('sock').close()
   raise TimeoutError('接続を停止しました')
  if 'error' in state:raise state['error']
  return state.pop('sock')

class LocalWorker(QThread):
 spots=Signal(object,bool);status=Signal(str)
 def __init__(self,state,parent=None,gate=None,fetch=None):
  super().__init__(parent);self.state=state;self.gate=gate or POLL_GATE;self.fetch=fetch or fetch_local;self.stop_event=threading.Event()
 def stop(self):self.stop_event.set()
 def run(self):
  first=True
  while not self.stop_event.is_set():
   if not self.gate.claim():
    self.status.emit(f'国内スポット：次回取得まで約{int(self.gate.remaining())+1}秒');self.stop_event.wait(min(10,max(.1,self.gate.remaining())));continue
   try:
    spots=self.fetch();self.gate.succeeded()
    if self.stop_event.is_set():break
    self.spots.emit(self.state.matching(spots),not first);first=False
    self.status.emit(f'国内スポット：取得成功 {len(spots)}件／5分間隔。開始時の既存情報は通知音なし。')
   except Exception as e:
    self.gate.failed(e.retry_after if isinstance(e,InternetError) else 0)
    if not self.stop_event.is_set():self.status.emit('国内スポット取得失敗：'+str(e)+'\n待機時間を延長します。')

class RbnWorker(QThread):
 spots=Signal(object,bool);status=Signal(str)
 def __init__(self,state,host,port,call,parent=None,connector=None,commands=(),duration=None):
  super().__init__(parent);self.state=state;self.host=host;self.port=port;self.call=call;self.connector=connector or socket.create_connection;self.stop_event=threading.Event();self.sock=None;self.commands=tuple(commands);self.duration=duration;self.logged_in=False;self.connected=False;self.failure=''
 def stop(self):
  self.stop_event.set()
  if self.sock:
   try:self.sock.shutdown(socket.SHUT_RDWR)
   except OSError:pass
 def run(self):
  started=time.monotonic()
  try:
   if self.stop_event.is_set():return
   self.status.emit('RBN：接続中…');self.sock=bounded_connect((self.host,self.port),self.stop_event,connector=self.connector);self.connected=True;self.status.emit('RBN：接続成功');self.sock.settimeout(.5)
   buffer=b'';login=False;deadline=time.monotonic()+30;batch=[];last=time.monotonic()
   while not self.stop_event.is_set() and (self.duration is None or time.monotonic()-started<self.duration):
    try:chunk=self.sock.recv(8192)
    except socket.timeout:chunk=None
    if chunk==b'':raise OSError('接続先が切断しました')
    if chunk:
     buffer+=chunk
     # Remove Telnet option negotiations and decline them.
     while re.search(b'\xff[\xfb-\xfe].',buffer):
      match=re.search(b'\xff[\xfb-\xfe].',buffer);cmd=match[0][1];option=match[0][2]
      if cmd in (251,253):self.sock.sendall(bytes([255,254 if cmd==251 else 252,option]))
      buffer=buffer[:match.start()]+buffer[match.end():]
     if not login and re.search(rb'(?:login|call(?:sign)?|user(?:name)?)\s*:',buffer,re.I):
      self.sock.sendall((self.call+'\r\n').encode('ascii'));login=True;self.logged_in=True
      for command in self.commands:self.sock.sendall((command+'\r\n').encode('ascii'))
      self.status.emit('RBN：受信中')
     while b'\n' in buffer:
      line,buffer=buffer.split(b'\n',1);spot=parse_rbn(line.decode('ascii',errors='replace'))
      if spot and self.state.matching([spot]):batch.append(spot)
     if len(buffer)>65536:raise ValueError('RBN応答の1行が長すぎます')
    if not login and time.monotonic()>deadline:raise TimeoutError('ログイン案内を確認できません')
    if batch and (time.monotonic()-last>=1 or len(batch)>=100):
     self.spots.emit(batch,True);batch=[];last=time.monotonic()
   if batch and not self.stop_event.is_set():self.spots.emit(batch,True)
  except Exception as e:
   self.failure=type(e).__name__+': '+str(e)
   if not self.stop_event.is_set():self.status.emit('RBN接続失敗：'+type(e).__name__+': '+str(e)+'\n自動連続再接続はしません。接続先を確認し、5分以上空けて再開してください。')
  finally:
   if self.sock:
    try:self.sock.close()
    except OSError:pass
   self.sock=None
