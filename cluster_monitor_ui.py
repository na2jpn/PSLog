"""Window-scoped monitoring with independently saved comma-separated conditions."""
import json,re
from pathlib import Path
from datetime import datetime
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,QPushButton,QCheckBox,QAbstractItemView,QTableWidget,QTableWidgetItem,QPlainTextEdit,QMessageBox)
from window_geometry import SafeDialog
from window_tint import apply_window_tint
from cluster_monitor import MonitorState,valid_token
from storage import Snapshot,replace_bytes,operation_lock
from alert_audio import AlertPlayer
from spot_display import ft_mode

class ConditionInput(QWidget):
 def __init__(self,kind,parent=None):
  super().__init__(parent);self.kind=kind;self.values=[];self.saved_text=''
  row=QHBoxLayout(self);row.setContentsMargins(0,0,0,0);self.edit=QLineEdit();self.edit.setMaxLength(2000);self.button=QPushButton('SET');row.addWidget(self.edit,1);row.addWidget(self.button)
 def set_values(self,values):
  self.values=list(dict.fromkeys(values));self.saved_text=', '.join(self.values);self.edit.setText(self.saved_text)
 def parsed(self):
  import unicodedata
  text=unicodedata.normalize('NFKC',self.edit.text()).upper()
  entries=list(dict.fromkeys(re.sub(r'\s+','',t) for t in text.split(',') if re.sub(r'\s+','',t)))
  bad=[t for t in entries if not valid_token(t,self.kind)]
  if bad:raise ValueError('形式を確認してください：'+', '.join(bad)+'\n区切りにはカンマを使用してください。')
  return entries

class ClusterMonitorDialog(SafeDialog):
 def __init__(self,repo,parent=None):
  super().__init__(parent);self.repo=repo;self.state=MonitorState();self.running=False;self.closing=False;self.settings_error=False
  self.alert=AlertPlayer(self)
  self.path=Path(repo.root)/'config/cluster_monitor.json';self.snapshot=Snapshot.read(self.path)
  self.setWindowTitle('ターゲットアラート');self.resize(1100,760);apply_window_tint(self,'edit')
  v=QVBoxLayout(self);note=QLabel('要インターネット。この画面を開いている間だけ監視します。国内スポットは5分に1回取得。開始時の既存情報は表示のみ、新着一致は1件につき通知音1回です。');note.setWordWrap(True);v.addWidget(note)
  row=QHBoxLayout();self.sound=QCheckBox('通知音 ON');self.sound.setChecked(True);row.addWidget(self.sound);test=QPushButton('音を確認');test.clicked.connect(self.play_alert);row.addWidget(test);row.addStretch();v.addLayout(row)
  v.addWidget(QLabel('コールサイン（例：JX1XXX, JX2XXX）'));self.calls=ConditionInput('call');v.addWidget(self.calls)
  v.addWidget(QLabel('JCC/JCG（例：1318, 13001, 13001A）'));self.codes=ConditionInput('code');v.addWidget(self.codes)
  self.calls.button.clicked.connect(lambda:self.set_condition(self.calls));self.codes.button.clicked.connect(lambda:self.set_condition(self.codes))
  hint=QLabel('カンマ区切りで入力し、各SETで保存・適用。空白・空要素は無視します。郡番号のみは郡全体、末尾文字付きは町村。RBNはコール条件のみ対象です。');hint.setWordWrap(True);v.addWidget(hint)
  row=QHBoxLayout();self.local=QCheckBox('国内クラスタ');self.local.setChecked(True);row.addWidget(self.local);self.rbn=QCheckBox('RBN');row.addWidget(self.rbn);self.include_ft=QCheckBox('FT8／FT4を対象にする');row.addWidget(self.include_ft);row.addStretch();v.addLayout(row)
  from spot_connection_ui import SpotConnection
  self.connection=SpotConnection(repo);v.addWidget(self.connection)
  from spot_feed import get_feed
  self.feed=get_feed(repo);self.feed.delivered.connect(self.receive);self.feed.message.connect(self.report)
  self.table=QTableWidget(0,9);self.table.setHorizontalHeaderLabels(['日時 JST','運用局','周波数 kHz','MODE','JCC/JCG','運用地','報告局','情報種別','コメント']);self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers);self.table.setAlternatingRowColors(True);v.addWidget(self.table,1)
  self.details=QPlainTextEdit();self.details.setReadOnly(True);self.details.document().setMaximumBlockCount(150);self.details.setFixedHeight(85);v.addWidget(self.details)
  self.status=QLabel('停止中。条件を入力して「監視開始」を押してください。');self.status.setWordWrap(True);v.addWidget(self.status)
  row=QHBoxLayout();self.start_button=QPushButton('監視開始');self.start_button.clicked.connect(self.start);row.addWidget(self.start_button);self.stop_button=QPushButton('監視停止');self.stop_button.setEnabled(False);self.stop_button.clicked.connect(self.stop);row.addWidget(self.stop_button);clear=QPushButton('表示をクリア');clear.clicked.connect(lambda:self.table.setRowCount(0));row.addWidget(clear);close=QPushButton('閉じる');close.clicked.connect(self.reject);row.addWidget(close);v.addLayout(row)
  try:
   data=json.loads(self.snapshot.data.decode('utf-8')) if self.snapshot.data else {}
   if not isinstance(data,dict):raise ValueError('設定がオブジェクトではありません')
   self.calls.set_values(data.get('calls',[]));self.codes.set_values(data.get('codes',[]));
   for field,key in ((self.calls,'calls_text'),(self.codes,'codes_text')):
    field.saved_text=data.get(key,field.saved_text);field.edit.setText(field.saved_text)
   self.include_ft.setChecked(bool(data.get('include_ft',False)));self.sound.setChecked(data.get('sound',True));self.rbn.setChecked(bool(data.get('rbn',False)));self.local.setChecked(bool(data.get('local',True)))
  except Exception as e:self.settings_error=True;self.report('設定を読めません。元ファイルは保持します：'+str(e))
  self.sound.toggled.connect(lambda checked: None if checked else self.alert.stop())
  self.include_ft.toggled.connect(self.ft_filter_changed)
  self.update_filters()
 @property
 def workers(self):return list(self.feed.active.values())
 def ft_filter_changed(self,checked):
  if not checked:
   self.alert.stop()
   for row in range(self.table.rowCount()-1,-1,-1):
    if ft_mode(self.table.item(row,3).text()):self.table.removeRow(row)
  elif self.running:self.receive(self.feed.snapshot(self.local.isChecked(),self.rbn.isChecked()),False)
  self.save_settings()
 def play_alert(self):
  if not self.sound.isChecked() or self.closing:return
  try:
   from storage import load_settings
   from preferences import validate
   values=validate(load_settings(self.repo.root));self.alert.play(values["alert_volume"],values["alert_sound"])
  except Exception as e:self.report("通知音設定を読めません："+str(e))
 def report(self,text):
  if self.closing:return
  self.status.setText(text.split('\n')[0]);self.details.appendPlainText(datetime.now().strftime('%H:%M:%S')+' '+text)
 def update_filters(self):self.state.set_filters(self.calls.values,self.codes.values)
 def save_settings(self):
  if self.settings_error:return False
  host,port,own=self.connection.values()
  data=dict(include_ft=self.include_ft.isChecked(),calls=self.calls.values,codes=self.codes.values,calls_text=self.calls.saved_text,codes_text=self.codes.saved_text,sound=self.sound.isChecked(),host=host,port=port,own=own,rbn=self.rbn.isChecked(),local=self.local.isChecked())
  try:
   self.path.parent.mkdir(parents=True,exist_ok=True)
   with operation_lock(self.path.parent):replace_bytes(self.path,(json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode('utf-8'),self.snapshot)
   self.snapshot=Snapshot.read(self.path);return True
  except Exception as e:self.report('条件の保存に失敗しました：'+str(e));return False
 def set_condition(self,field):
  try:values=field.parsed()
  except ValueError as e:QMessageBox.warning(self,'条件の入力エラー',str(e));return
  previous=field.values;previous_text=field.saved_text;field.values=values;field.saved_text=field.edit.text()
  if not self.save_settings():
   field.values=previous;field.saved_text=previous_text;QMessageBox.warning(self,'保存エラー','条件を保存できませんでした。詳細欄を確認してください。');return
  self.update_filters();self.report('条件を保存・適用しました。')
 def start(self):
  if self.running:return
  self.update_filters()
  if not self.state.calls and not self.state.codes:self.report('コールサインかJCC/JCGを入力し、SETしてください。');return
  if not self.local.isChecked() and not self.rbn.isChecked():self.report('監視する情報種別を選択してください。');return
  try:
   if self.rbn.isChecked():
    self.connection.validate()
    if not self.state.calls:raise ValueError('RBN監視にはSET済みのコールサイン条件が必要です。')
   if not self.save_settings():return
   self.running=True
   self.feed.subscribe(self,self.local.isChecked(),self.rbn.isChecked(),*self.connection.values())
  except Exception as e:self.running=False;self.report(str(e));return
  self.start_button.setEnabled(False);self.stop_button.setEnabled(True)
  for w in (self.local,self.rbn):w.setEnabled(False)
  self.receive(self.feed.snapshot(self.local.isChecked(),self.rbn.isChecked()),False);self.report('監視を開始しました。')
 def receive(self,spots,notify):
  if not self.running or self.closing:return
  spots=[s for s in spots if (s.source=='RBN' and self.rbn.isChecked()) or (s.source!='RBN' and self.local.isChecked())]
  spots=[s for s in spots if self.include_ft.isChecked() or not ft_mode(s.mode)]
  for spot in sorted(self.state.fresh(self.state.matching(spots)),key=lambda s:s.stamp):
   # Explicit JST independent of the computer's configured zone.
   from datetime import timezone,timedelta
   stamp=datetime.fromisoformat(spot.stamp).astimezone(timezone(timedelta(hours=9))).strftime('%Y-%m-%d %H:%M')
   self.table.insertRow(0)
   for col,value in enumerate((stamp,spot.call,spot.freq,spot.mode,spot.code,spot.qth,spot.reporter,spot.source,spot.comment)):
    item=QTableWidgetItem(value);item.setToolTip(value);self.table.setItem(0,col,item)
   if self.table.rowCount()>2000:self.table.removeRow(2000)
   if notify and self.sound.isChecked():self.play_alert()
  self.table.sortItems(0,Qt.SortOrder.DescendingOrder);self.table.resizeColumnsToContents()
 def stop(self):
  self.alert.stop();self.running=False;self.feed.unsubscribe(self);self.stop_button.setEnabled(False);self.start_button.setEnabled(True)
  for w in (self.local,self.rbn):w.setEnabled(True)
  self.report('停止中')
 def reject(self):
  if self.closing:return
  self.save_settings();self.stop();self.closing=True
  self.feed.delivered.disconnect(self.receive);self.feed.message.disconnect(self.report)
  super().reject()
 def closeEvent(self,event):self.reject();event.accept()

TargetAlertDialog=ClusterMonitorDialog
