"""Shared domestic feed and one five-slot RBN rotation for both windows."""
from collections import OrderedDict
from decimal import Decimal,InvalidOperation
from pathlib import Path
import time
from PySide6.QtCore import QObject,Signal
from PySide6.QtWidgets import QApplication
from cluster_workers import LocalWorker
from rbn_settings import get_settings
from rbn_cycle import RbnCycleWorker
class AllSpots:
 def matching(self,spots):return spots

class SpotFeed(QObject):
 delivered=Signal(object,bool);updated=Signal(object);message=Signal(str)
 def __init__(self,parent=None,settings=None):
  super().__init__(parent);self.clients={};self.active={};self.retiring=set();self.cache=OrderedDict();self.recent=OrderedDict();self.exact=OrderedDict();self.source_snapshots={};self.retries={};self.shutting_down=False;self.settings=settings
  if settings:settings.changed.connect(self.configuration_changed)
 def subscribe(self,owner,local,rbn,*legacy):
  if rbn:
   if self.settings is None:raise ValueError('共通RBN設定がありません。')
   self.settings.validate_start()
  self.clients[owner]=(local,rbn);self._sync()
 def unsubscribe(self,owner):self.clients.pop(owner,None);self._sync()
 def configuration_changed(self):
  worker=self.active.get('rbn')
  if worker and worker not in self.retiring:worker.stop();self.retiring.add(worker)
  self._sync()
 def snapshot(self,local,rbn):return [s for s in self.cache.values() if (local and s.source!='RBN') or (rbn and s.source=='RBN')]
 def _sync(self):
  if self.shutting_down:return
  desired=set()
  if any(c[0] for c in self.clients.values()):desired.add('local')
  if any(c[1] for c in self.clients.values()) and self.settings and any(n['enabled'] for n in self.settings.data['nodes']):desired.add('rbn')
  for key,worker in list(self.active.items()):
   if key not in desired and worker not in self.retiring:worker.stop();self.retiring.add(worker)
  for key in desired:
   if key in self.active:continue
   if key=='local':worker=LocalWorker(AllSpots(),self)
   else:
    worker=RbnCycleWorker(self.settings.data,self,retries=self.retries);worker.snapshot.connect(self._snapshot)
   self.active[key]=worker;worker.spots.connect(self._receive);worker.status.connect(self.message);worker.finished.connect(self._finished);worker.start()
 def _snapshot(self,slot,rows):self.source_snapshots[slot]=list(rows)
 def _receive(self,spots,notify):
  if self.shutting_down:return
  out=[];updates=[];now=time.monotonic()
  for spot in spots:
   if spot.source=='RBN':
    try:
     from spot_display import ft_mode,ft_frequency_key
     freq=str(ft_frequency_key(spot.freq)) if ft_mode(spot.mode) else str(Decimal(spot.freq).normalize())
    except (InvalidOperation,ValueError):continue
    identity=(spot.call.upper(),freq,spot.mode.upper());exact=identity+(spot.stamp,)
    cache_key=('RBN-latest',)+identity
    old=self.cache.get(cache_key)
    if old is None or spot.stamp>=old.stamp:self.cache[cache_key]=spot;self.cache.move_to_end(cache_key)
    if exact in self.exact:
     if spot.mode.upper() in ('FT8','FT4'):updates.append(spot)
     continue
    self.exact[exact]=None
    while len(self.exact)>20000:self.exact.popitem(last=False)
    if now-self.recent.get(identity,-1e20)<300:
     if spot.mode.upper() in ('FT8','FT4'):updates.append(spot)
     continue
    self.recent[identity]=now
    while len(self.recent)>20000:self.recent.popitem(last=False)
   if spot.source!='RBN':self.cache[spot.key]=spot;self.cache.move_to_end(spot.key)
   out.append(spot)
   if len(self.cache)>20000:self.cache.popitem(last=False)
  while len(self.cache)>20000:self.cache.popitem(last=False)
  if self.clients and out:self.delivered.emit(out,notify)
  if self.clients and updates:self.updated.emit(updates)
 def _finished(self):
  worker=self.sender();retiring=worker in self.retiring;self.retiring.discard(worker)
  for key,value in list(self.active.items()):
   if value is worker:del self.active[key]
  worker.deleteLater()
  if retiring:self._sync()
 def shutdown(self):
  self.shutting_down=True;self.clients.clear()
  for worker in self.active.values():worker.stop()
  for worker in self.active.values():worker.wait(17000)

def get_feed(repo):
 app=QApplication.instance()
 if not hasattr(app,'_pslog_spot_feeds'):app._pslog_spot_feeds={}
 key=str(Path(repo.root).resolve())
 if key not in app._pslog_spot_feeds:
  feed=SpotFeed(app,get_settings(repo));app._pslog_spot_feeds[key]=feed;app.aboutToQuit.connect(feed.shutdown)
 return app._pslog_spot_feeds[key]
