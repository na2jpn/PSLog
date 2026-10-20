"""Read-only MIC diagnostic lookup; no log updates."""
import json,time
from PySide6.QtCore import QThread,Signal,QTimer
from PySide6.QtWidgets import QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,QPushButton,QPlainTextEdit
from window_geometry import SafeDialog
from window_tint import apply_window_tint
from locations import load,qth_for_row
from his_qth_batch import request_location,location_from_response,location_url,DOMESTIC

class MicWorker(QThread):
 completed=Signal(object);failed=Signal(str)
 def __init__(self,call,parent):super().__init__(parent);self.call=call
 def run(self):
  try:self.completed.emit(request_location(self.call))
  except Exception as e:self.failed.emit(str(e))

class MicLookupDialog(SafeDialog):
 def __init__(self,repo,parent=None):
  super().__init__(parent);self.repo=repo;self.worker=None;self.closing=False
  self.setWindowTitle('総務省DB参照');self.resize(900,680);apply_window_tint(self,'edit')
  v=QVBoxLayout(self);note=QLabel('要インターネット。日本のコールサインを入力してください。無線設備所在地とPSLogの表記を確認します。ログは変更しません。');note.setWordWrap(True);v.addWidget(note)
  row=QHBoxLayout();self.call=QLineEdit();self.call.setPlaceholderText('例：JX1XXX（/1・/P等は入力しない）');row.addWidget(self.call)
  self.lookup=QPushButton('照会');self.lookup.clicked.connect(self.run);row.addWidget(self.lookup);v.addLayout(row);self.call.returnPressed.connect(self.run)
  self.progress_timer=QTimer(self);self.progress_timer.setInterval(250);self.progress_timer.timeout.connect(self.update_progress)
  self.status=QLabel('未照会');self.status.setWordWrap(True);v.addWidget(self.status)
  self.detail=QPlainTextEdit();self.detail.setReadOnly(True);v.addWidget(self.detail,1)
  close=QPushButton('閉じる');close.clicked.connect(self.reject);v.addWidget(close)
 def run(self):
  if self.worker:return
  call=self.call.text().strip().upper()
  if '/' in call or not DOMESTIC.fullmatch(call):self.status.setText('日本の移動表記なしのコールサインを入力してください。');return
  self.call.setText(call);self.lookup.setEnabled(False);self.call.setEnabled(False);self.started=time.monotonic();self.status.setText('総務省APIへ照会中…');self.detail.setPlainText('照会URL: '+location_url(call));self.progress_timer.start()
  w=MicWorker(call,self);self.worker=w;w.completed.connect(self.render);w.failed.connect(self.failed);w.finished.connect(self.worker_finished);w.start()
 def update_progress(self):
  self.status.setText(f"総務省APIへ照会中… 経過 {time.monotonic()-self.started:.1f}秒（通信全体の制限15秒）")
 def render(self,data):
  self.progress_timer.stop()
  records=data.get('musen') if isinstance(data,dict) else None
  if isinstance(data,dict) and (data.get('err') or data.get('errs')):status='通信成功／APIがエラーを返しました'
  elif records==[]:status='通信成功／該当局なし'
  else:status='通信成功'
  text=[]
  try:
   row=location_from_response(data,self.call.text(),load(self.repo.root));text=['所在地: '+row['name'],'PSLog表記: '+qth_for_row(row),'JCC/JCG: '+row['source_code']];status+='／所在地判定成功'
  except Exception as e:status+='／所在地判定未確定';text=['所在地判定: '+str(e)]
  self.status.setText(status);self.detail.setPlainText('\n'.join(text)+'\n\n取得したAPI応答（局情報・所在地候補）:\n'+json.dumps(data,ensure_ascii=False,indent=2))
 def failed(self,message):self.progress_timer.stop();self.status.setText('取得失敗（詳細を確認してください）');self.detail.setPlainText(message)
 def worker_finished(self):
  self.progress_timer.stop()
  self.worker.deleteLater();self.worker=None;self.lookup.setEnabled(True);self.call.setEnabled(True)
  if self.closing:super().reject()
 def reject(self):
  if self.worker:self.closing=True;self.hide();return
  super().reject()
 def closeEvent(self,event):
  if self.worker:self.reject();event.ignore();return
  super().closeEvent(event)
