"""One common A-E settings dialog, opened from either tool window."""
from PySide6.QtCore import Qt,QThread,Signal
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QCheckBox,QLineEdit,QSpinBox,QComboBox,QGridLayout,QMessageBox,QTextEdit)
from window_geometry import SafeDialog
from rbn_settings import get_settings,validate,PROFILES
from logbook_sources import amateur_station_calls
from cluster_workers import RbnWorker
from cluster_monitor import valid_token

class ProbeWorker(QThread):
 result=Signal(str);detail=Signal(str)
 def __init__(self,node,call,parent=None):super().__init__(parent);self.node=node;self.call=call;self.child=None;self.cancelled=False
 def stop(self):
  self.cancelled=True
  if self.child:self.child.stop()
 def run(self):
  from rbn_cycle import NoneState
  n=self.node;seen=[];self.child=RbnWorker(NoneState(),n['host'],n['port'],self.call,commands=PROFILES[n['profile']],duration=20)
  self.child.status.connect(self.detail.emit,Qt.ConnectionType.DirectConnection);self.child.spots.connect(lambda rows,notify:seen.extend(rows),Qt.ConnectionType.DirectConnection)
  if self.cancelled:self.child.stop()
  self.child.run()
  if self.cancelled:return
  rbn=[s for s in seen if s.mode in ('CW','RTTY','FT8','FT4') and ' dB' in s.comment]
  text='接続成功／RBN受信確認：'+str(len(rbn))+'件' if rbn else '接続成功／スポット受信（RBN未確認）' if seen else '接続成功／RBN受信は未確認' if self.child.connected else '接続失敗：'+(self.child.failure or '通信詳細を確認してください。')
  if self.child.connected and self.child.failure:text+='（途中切断・通信詳細を確認）'
  self.result.emit(text)

class RbnSettingsDialog(SafeDialog):
 def __init__(self,repo,parent=None):
  super().__init__(parent);self.repo=repo;self.store=get_settings(repo);self.probe=None;self.closing=False;self.setWindowTitle('RBN設定（両ツール共通）');self.resize(1120,650);v=QVBoxLayout(self)
  note=QLabel('A→B→C→D→Eの有効枠を60秒ごとに巡回。5枠有効なら約300秒で一周します。情報は切替時に消さず、重複はSKIPします。');note.setWordWrap(True);v.addWidget(note)
  row=QHBoxLayout();row.addWidget(QLabel('共通ログインコール'));self.own=QComboBox();self.own.setEditable(True);self.own.addItems(amateur_station_calls(repo));self.own.setCurrentText(self.store.data['own']);self.own.setToolTip('例：JX1XXX');row.addWidget(self.own);row.addStretch();v.addLayout(row)
  grid=QGridLayout();v.addLayout(grid)
  for col,text in enumerate(['有効','枠・表示名','接続先ホスト','ポート','ソフト種別','確認']):grid.addWidget(QLabel(text),0,col)
  self.rows=[]
  for i,node in enumerate(self.store.data['nodes'],1):
   enabled=QCheckBox();enabled.setChecked(node['enabled']);name=QLineEdit(node['name']);host=QLineEdit(node['host']);port=QSpinBox();port.setRange(1,65535);port.setValue(node['port']);profile=QComboBox();profile.addItems(PROFILES);profile.setCurrentText(node['profile']);test=QPushButton(node['slot']+' 接続テスト');test.clicked.connect(lambda checked,index=i-1:self.test_node(index));widgets=(enabled,name,host,port,profile,test);self.rows.append(widgets)
   for col,w in enumerate(widgets):grid.addWidget(w,i,col)
  hint=QLabel('各接続先の通信状態は接続テストで確認できます。約20秒受信して接続成功とRBN受信確認を分けて表示します。テストは両ツールのRBN受信を停止してから実行してください。');hint.setWordWrap(True);v.addWidget(hint)
  commands=QLabel('ソフト種別に応じてログイン後にRBN有効化コマンドを送ります。AR-Cluster：set dx filt ／ CC Cluster：set/skimmer と各MODE ON ／ DXSpider：set/skimmer。設定なしはコマンドを送りません。');commands.setWordWrap(True);v.addWidget(commands)
  self.details=QTextEdit();self.details.setAcceptRichText(False);self.details.setReadOnly(True);self.details.document().setMaximumBlockCount(150);v.addWidget(self.details,1)
  if self.store.error:self.details.setPlainText(self.store.error)
  self.status=QLabel('未保存の変更は監視に反映しません。保存すると両画面へ反映し、巡回中のRBN接続を切り替えます。');self.status.setWordWrap(True);v.addWidget(self.status)
  row=QHBoxLayout();self.save_button=QPushButton('保存して適用');self.save_button.clicked.connect(self.save);self.cancel=QPushButton('閉じる');self.cancel.clicked.connect(self.reject);row.addStretch();row.addWidget(self.save_button);row.addWidget(self.cancel);v.addLayout(row)
 def append_detail(self,text,color=None):
  from PySide6.QtGui import QTextCursor,QTextCharFormat,QColor
  cursor=self.details.textCursor();cursor.movePosition(QTextCursor.MoveOperation.End)
  if not self.details.document().isEmpty():cursor.insertBlock()
  fmt=QTextCharFormat();fmt.setForeground(QColor(color or ('#18733b' if '接続成功' in text else '#b3261e' if '接続失敗' in text else '#202c3a')));cursor.insertText(text,fmt);self.details.setTextCursor(cursor);self.details.ensureCursorVisible()
 def show_result(self,text):
  success=text.startswith('接続成功');color='#18733b' if success else '#b3261e';self.status.setText(text);self.status.setStyleSheet('color:'+color+';font-weight:bold');self.append_detail('【結果】'+text,color)
 def values(self):
  nodes=[]
  for slot,widgets in zip('ABCDE',self.rows):
   enabled,name,host,port,profile,test=widgets;nodes.append(dict(slot=slot,name=name.text(),host=host.text(),port=port.value(),profile=profile.currentText(),enabled=enabled.isChecked()))
  return validate(dict(own=self.own.currentText(),nodes=nodes))
 def save(self):
  if self.probe:return
  try:self.store.save(self.values())
  except Exception as e:QMessageBox.warning(self,'RBN設定の保存',str(e));return
  self.accept()
 def test_node(self,index):
  if self.probe:return
  from spot_feed import get_feed
  feed=get_feed(self.repo)
  if 'rbn' in feed.active or any(v[1] for v in feed.clients.values()):QMessageBox.information(self,'接続テスト','先に両ツールのRBN受信を停止し、停止処理の完了を待ってください。');return
  try:
   data=self.values();call=data['own'];node=data['nodes'][index]
   if not call or not valid_token(call,'call'):raise ValueError('ログインコールを入力してください。')
   if not node['host']:raise ValueError('接続先を入力してください。')
  except Exception as e:QMessageBox.warning(self,'接続テスト',str(e));return
  import time
  key=(node['host'],node['port']);remaining=feed.retries.get(key,0)-time.monotonic()
  if remaining>0:QMessageBox.information(self,'接続テスト',f'この接続先への再接続は約{int(remaining)+1}秒後に可能です。');return
  feed.retries[key]=time.monotonic()+300
  self.status.setStyleSheet('');self.details.clear();self.append_detail(f'{node["slot"]} {node["host"]}:{node["port"]} / {node["profile"]}');self.status.setText('接続テスト中（最大約20秒。名前解決などで延びる場合があります）');self.save_button.setEnabled(False)
  self.probe=ProbeWorker(node,call,self);self.probe.detail.connect(self.append_detail);self.probe.result.connect(self.show_result);self.probe.finished.connect(self.probe_finished);self.probe.start()
 def probe_finished(self):
  worker=self.probe;self.probe=None;worker.deleteLater();self.save_button.setEnabled(True)
  if self.closing:super().reject()
 def reject(self):
  if self.probe:self.closing=True;self.probe.stop();self.hide();return
  super().reject()
 def closeEvent(self,event):self.reject();event.ignore()

class SpotConnection(QWidget):
 def __init__(self,repo,parent=None):
  super().__init__(parent);self.repo=repo;self.store=get_settings(repo);row=QHBoxLayout(self);row.setContentsMargins(0,0,0,0);self.button=QPushButton('RBN設定');self.button.clicked.connect(self.open_settings);row.addWidget(self.button);self.summary=QLabel();self.summary.setWordWrap(True);row.addWidget(self.summary,1);self.store.changed.connect(self.refresh);self.refresh()
 def refresh(self):
  enabled='→'.join(n['slot'] for n in self.store.data['nodes'] if n['enabled']) or '接続先なし';self.summary.setText(f'{enabled} ／ 60秒ごと ／ '+(self.store.data['own'] or 'ログインコール未設定'))
  self.summary.setToolTip(self.store.error or '設定・接続・巡回はバンドサイトとターゲットアラートで共有します。各接続先への再接続は5分以上空けます。')
 def open_settings(self):RbnSettingsDialog(self.repo,self).exec()
 def values(self):
  node=self.store.data['nodes'][0];return node['host'],node['port'],self.store.data['own']
 def validate(self):self.store.validate_start()
 def load_values(self,data):pass  # Legacy values are migrated once by the shared store.
