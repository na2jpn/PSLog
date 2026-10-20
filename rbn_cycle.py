"""Single socket rotation. Each enabled endpoint has a minimum 300s retry interval."""
import time,threading
from PySide6.QtCore import QThread,Signal,Qt
from cluster_workers import RbnWorker
from rbn_settings import PROFILES
class CycleSchedule:
 def __init__(self,nodes,retries=None):self.nodes=[dict(n) for n in nodes if n['enabled']];self.retries=retries if retries is not None else {};self.index=0
 def next(self,now):
  if not self.nodes:return None,60
  waits=[]
  for offset in range(len(self.nodes)):
   index=(self.index+offset)%len(self.nodes);node=self.nodes[index];key=(node['host'],node['port']);wait=self.retries.get(key,0)-now
   if wait<=0:self.index=(index+1)%len(self.nodes);self.retries[key]=now+300;return node,0
   waits.append(wait)
  return None,max(.1,min(waits))

class RbnCycleWorker(QThread):
 spots=Signal(object,bool);status=Signal(str);snapshot=Signal(str,object)
 def __init__(self,data,parent=None,retries=None,worker_factory=RbnWorker,slot_seconds=60):
  super().__init__(parent);self.data=data;self.schedule=CycleSchedule(data['nodes'],retries);self.worker_factory=worker_factory;self.slot_seconds=slot_seconds;self.stop_event=threading.Event();self.current=None
 def stop(self):
  self.stop_event.set()
  if self.current:self.current.stop()
 def run(self):
  while not self.stop_event.is_set():
   node,wait=self.schedule.next(time.monotonic())
   if node is None:
    self.status.emit(f'RBN：次の接続まで約{int(wait)+1}秒（各接続先の再接続間隔は5分以上）');self.stop_event.wait(min(wait,10));continue
   started=time.monotonic();slot=node['slot'];rows={}
   self.status.emit(f'RBN {slot}：{node["name"]} / {node["host"]}:{node["port"]}（60秒枠）')
   child=self.worker_factory(NoneState(),node['host'],node['port'],self.data['own'],commands=PROFILES[node['profile']],duration=self.slot_seconds);self.current=child
   def receive(spots,notify):
    for spot in spots:
     rows[spot.key]=spot
     if len(rows)>4000:rows.pop(next(iter(rows)))
    if not self.stop_event.is_set():self.spots.emit(spots,notify)
   child.spots.connect(receive,Qt.ConnectionType.DirectConnection)
   child.status.connect(lambda text:self.status.emit(f'RBN {slot}：'+text.replace('自動連続再接続はしません。接続先を確認し、5分以上空けて再開してください。','この枠の終了後、次の候補へ進みます。')),Qt.ConnectionType.DirectConnection)
   if self.stop_event.is_set():child.stop()
   child.run();self.current=None
   if rows and not self.stop_event.is_set():self.snapshot.emit(slot,list(rows.values()))
   # A failure consumes its slot, preventing bursts of connection attempts.
   self.stop_event.wait(max(0,self.slot_seconds-(time.monotonic()-started)))

class NoneState:
 def matching(self,spots):return spots
