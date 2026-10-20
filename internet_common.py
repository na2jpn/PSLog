"""Bounded HTTP access and readable diagnostics shared by internet tools."""
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
import socket
USER_AGENT='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36'
MAX_BYTES=2_000_000
class InternetError(Exception):
 def __init__(self,message,status=None,retry_after=0):
  super().__init__(message);self.status=status;self.retry_after=retry_after

def excerpt(raw):
 return raw[:2000].decode('utf-8',errors='replace').replace('\x00','')

def request_bytes(url,accept='*/*',opener=None,timeout=15,headers=None):
 request_headers={'User-Agent':USER_AGENT,'Accept':accept}
 if headers:request_headers.update(headers)
 req=Request(url,headers=request_headers)
 try:
  with (opener or urlopen)(req,timeout=timeout) as response:
   raw=response.read(MAX_BYTES+1)
   if len(raw)>MAX_BYTES:raise InternetError('応答サイズが上限2MBを超えました。\nURL: '+url)
   return raw
 except HTTPError as e:
  try:body=excerpt(e.read(2000))
  except Exception:body='（応答本文を取得できません）'
  try:retry=int(e.headers.get('Retry-After','0'))
  except (ValueError,TypeError,AttributeError):retry=0
  raise InternetError(f'HTTP {e.code} {e.reason}\nURL: {url}\n種別: {type(e).__name__}\n応答: {body}',e.code,retry) from e
 except (TimeoutError,socket.timeout) as e:raise InternetError(f'タイムアウト（{timeout}秒）\nURL: {url}\n{type(e).__name__}: {e}') from e
 except (URLError,OSError) as e:raise InternetError(f'通信エラー\nURL: {url}\n{type(e).__name__}: {e}') from e
