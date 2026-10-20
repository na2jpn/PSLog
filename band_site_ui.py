"""Independent, clipped band maps driven by the shared spot feed."""
import json,math
from pathlib import Path
from datetime import datetime,timezone,timedelta
from PySide6.QtCore import Qt,QTimer,QRectF
from PySide6.QtGui import QPainter,QColor,QPen
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QGridLayout,QLabel,QPushButton,QCheckBox,QScrollArea,QToolTip,QMessageBox,QComboBox,QFrame,QTableWidget,QTableWidgetItem,QAbstractItemView,QHeaderView)
from window_geometry import SafeDialog
from window_tint import apply_window_tint
from storage import Snapshot,replace_bytes,operation_lock
from band_site import BANDS,COLORS,BandSpots,frequency,stamp,abbreviation
from spot_feed import get_feed
from spot_connection_ui import SpotConnection
from spot_display import ft_groups
VIEW_KEYS=tuple(b[0] for b in BANDS)+tuple(b[0]+'-FT' for b in BANDS)

class BandPanel(QWidget):
 def __init__(self,band,parent=None):
  super().__init__(parent);self.band,self.low,self.high=band;self.spots=[];self.hits=[];self.setMouseTracking(True);self.setMinimumSize(170,190)
 def set_spots(self,spots):self.spots=spots;self.update()
 def description(self,s):
  when=stamp(s).astimezone(timezone(timedelta(hours=9))).strftime('%m/%d %H:%M JST')
  return f'{s.call}  {frequency(s)/1000:.4f} MHz  {s.mode or "不明"}\n{when} / {s.source} / {s.reporter}\n{s.code} {s.qth}\n{s.comment}'
 def paintEvent(self,event):
  p=QPainter(self);p.setClipRect(self.rect());p.fillRect(self.rect(),QColor('#fafbfd'));p.setPen(QColor('#bac4cf'));p.drawRect(self.rect().adjusted(0,0,-1,-1));p.setPen(QColor('#202c3a'));p.drawText(10,23,f'{self.band} MHz  ·  {len(self.spots)}局')
  top=47;bottom=max(top+45,self.height()-30);axis=63
  p.setPen(QColor('#65778a'));p.drawLine(axis,top,axis,bottom)
  for i in range(5):
   y=top+(bottom-top)*i/4;freq=(self.low+(self.high-self.low)*i/4)/1000
   p.drawLine(axis-4,int(y),axis+4,int(y));p.drawText(QRectF(1,y-9,56,18),Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignVCenter,f'{freq:.3f}'.rstrip('0').rstrip('.'))
  self.hits=[];line=max(19,self.fontMetrics().height()+3);capacity=max(1,int((bottom-top)/line));recent=sorted(self.spots,key=stamp,reverse=True);shown=sorted(recent[:capacity],key=frequency);positions=[]
  for s in shown:
   actual=top+(frequency(s)-self.low)/(self.high-self.low)*(bottom-top)
   y=max(actual,positions[-1][1]+line if positions else top)
   positions.append((s,y,actual))
  ceiling=bottom
  for i in range(len(positions)-1,-1,-1):
   s,y,a=positions[i];y=min(y,ceiling);positions[i]=(s,y,a);ceiling=y-line
  for s,y,actual in positions:
   color=QColor(COLORS.get(s.mode.upper(),'#596574'));p.setPen(QPen(color,1));p.drawEllipse(QRectF(axis-2,actual-2,4,4));p.drawLine(axis+3,int(actual),axis+12,int(y));text=f'{abbreviation(s,self.band)}  {s.mode or "?"}  {s.call}';rect=QRectF(axis+14,y-line/2,max(1,self.width()-axis-19),line);p.drawText(rect,Qt.AlignmentFlag.AlignVCenter,self.fontMetrics().elidedText(text,Qt.TextElideMode.ElideRight,int(rect.width())));self.hits.append((rect,self.description(s)))
  if not self.spots:p.setPen(QColor('#708090'));p.drawText(QRectF(axis+12,top,self.width()-axis-20,50),Qt.TextFlag.TextWordWrap,'このバンドの新しい情報はありません')
  if len(recent)>capacity:
   rect=QRectF(8,self.height()-25,self.width()-16,22);p.setPen(QColor('#404c5a'));p.drawText(rect,Qt.AlignmentFlag.AlignVCenter,f'他 {len(recent)-capacity}局（ここにマウスを置く）');self.hits.append((rect,'\n\n'.join(self.description(s) for s in recent[capacity:capacity+40])))
 def mouseMoveEvent(self,event):
  for rect,text in self.hits:
   if rect.contains(event.position()):QToolTip.showText(event.globalPosition().toPoint(),text,self);return
  QToolTip.hideText()

class FtPanel(QWidget):
 def __init__(self,band,parent=None):
  super().__init__(parent);self.band=band[0];self.spots=[];self.cards={};self.signatures={};self.setMinimumSize(170,190)
  v=QVBoxLayout(self);v.setContentsMargins(5,5,5,5);self.title=QLabel();v.addWidget(self.title);scroll=QScrollArea();scroll.setWidgetResizable(True);body=QWidget();self.layout_cards=QVBoxLayout(body);self.layout_cards.setContentsMargins(0,0,0,0);self.empty=QLabel('このバンドのFT8／FT4情報はありません');self.empty.setWordWrap(True);self.layout_cards.addWidget(self.empty);self.layout_cards.addStretch();scroll.setWidget(body);v.addWidget(scroll,1)
 def set_spots(self,spots):
  self.spots=spots;groups=ft_groups(spots);self.title.setText(f'{self.band}-FT  ·  {sum(len(rows) for rows in groups.values())}局');self.empty.setVisible(not groups)
  for key in set(self.cards)-set(groups):
   card,table,header=self.cards.pop(key);self.layout_cards.removeWidget(card);card.deleteLater();self.signatures.pop(key,None)
  for index,(key,rows) in enumerate(groups.items()):
   if key not in self.cards:
    card=QFrame();card.setObjectName('ftcard');card.setStyleSheet('QFrame#ftcard { background:#fafbfd; border:1px solid #bac4cf; border-radius:4px; }');v=QVBoxLayout(card);v.setContentsMargins(6,5,6,5);header=QLabel();header.setWordWrap(True);v.addWidget(header);table=QTableWidget(0,3);table.setHorizontalHeaderLabels(['コールサイン','周波数 MHz','最終受信 JST']);table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers);table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows);table.setAlternatingRowColors(True);table.verticalHeader().hide();table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents);table.setMinimumHeight(85);v.addWidget(table);self.cards[key]=(card,table,header)
   card,table,header=self.cards[key];self.layout_cards.insertWidget(index,card);freq,mode=key;header.setText(f'{freq/1000:.2f} MHz台 ｜ {mode} ｜ {len(rows)}局');header.setStyleSheet('font-weight:bold;color:'+COLORS[mode]);signature=tuple((r.key,r.stamp,r.freq,r.reporter,r.comment) for r in rows)
   if self.signatures.get(key)==signature:continue
   self.signatures[key]=signature;position=table.verticalScrollBar().value();table.setRowCount(len(rows))
   for row,spot in enumerate(rows):
    when=stamp(spot).astimezone(timezone(timedelta(hours=9))).strftime('%m/%d %H:%M')
    for col,text in enumerate((spot.call,f'{frequency(spot)/1000:.4f}',when)):
     item=QTableWidgetItem(text);item.setToolTip(BandPanel.description(self,spot));table.setItem(row,col,item)
   table.setFixedHeight(min(215,max(85,table.horizontalHeader().height()+len(rows)*table.verticalHeader().defaultSectionSize()+5)));table.verticalScrollBar().setValue(position)

class BandSiteDialog(SafeDialog):
 def __init__(self,repo,parent=None):
  super().__init__(parent);self._own_scroll_area=True;self.repo=repo;self.closing=False;self.running=False;self.store=BandSpots();self.selected=['7'];self.panels={};self.path=Path(repo.root)/'config/band_site.json';self.snapshot=Snapshot.read(self.path);self.settings_error=False
  self.setWindowTitle('バンドサイト');self.resize(1150,780);apply_window_tint(self,'edit');v=QVBoxLayout(self)
  note=QLabel('要インターネット。バンドを選択／解除（最大8）。国内クラスタは5分間隔、RBNは受信時に更新。直近30分を表示し、この画面を閉じると受信を停止します。');note.setWordWrap(True);v.addWidget(note)
  scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setFixedHeight(94);bar=QWidget();buttons_grid=QGridLayout(bar);buttons_grid.setContentsMargins(3,3,3,3);self.buttons={}
  for col,(name,low,high) in enumerate(BANDS):
   for row,key in enumerate((name,name+'-FT')):
    button=QPushButton(key);button.setCheckable(True);button.setMinimumWidth(65);button.clicked.connect(lambda checked,n=key:self.toggle_band(n,checked));self.buttons[key]=button;buttons_grid.addWidget(button,row,col)
  scroll.setWidget(bar);v.addWidget(scroll)
  row=QHBoxLayout();self.local=QCheckBox('国内クラスタ');self.local.setChecked(True);self.rbn=QCheckBox('RBN');row.addWidget(self.local);row.addWidget(self.rbn);row.addStretch();row.addWidget(QLabel('運用局'));self.scope=QComboBox()
  for text,key in [('すべて','all'),('JA局のみ','ja'),('DX局のみ','dx')]:self.scope.addItem(text,key)
  self.scope.setToolTip('運用局のコールサインで選択。日本のコール（JD1等を含む）と明示的な移動先表記で判定。判定不能は「すべて」にだけ表示します。');row.addWidget(self.scope);v.addLayout(row)
  legend=QLabel('通常：CW 青 / SSB 緑 / FM 紫 / RTTY 青緑　　○-FT：FT8 橙 / FT4 桃（周波数別カード）');legend.setWordWrap(True);v.addWidget(legend)
  self.connection=SpotConnection(repo);v.addWidget(self.connection)
  self.canvas=QWidget();self.grid=QGridLayout(self.canvas);self.grid.setContentsMargins(0,0,0,0);self.grid.setSpacing(6)
  canvas_scroll=QScrollArea();canvas_scroll.setWidgetResizable(True);canvas_scroll.setWidget(self.canvas);v.addWidget(canvas_scroll,1)
  hint=QLabel('上段は通常の周波数軸、下段○-FTはFT8／FT4専用。合計最大8枠。FTカードは1kHz単位にまとめ、各局の実周波数・最終受信JSTを表示。マウスで詳細表示。表示範囲は送信可能範囲を示すものではありません。');hint.setWordWrap(True);v.addWidget(hint)
  self.status=QLabel('停止中');self.status.setWordWrap(True);v.addWidget(self.status)
  row=QHBoxLayout();self.start_button=QPushButton('受信開始');self.stop_button=QPushButton('受信停止');self.stop_button.setEnabled(False);clear=QPushButton('表示をクリア');close=QPushButton('閉じる')
  for w in (self.start_button,self.stop_button,clear,close):row.addWidget(w)
  v.addLayout(row);self.start_button.clicked.connect(self.start);self.stop_button.clicked.connect(self.stop);clear.clicked.connect(self.clear);close.clicked.connect(self.reject)
  self.feed=get_feed(repo);self.feed.delivered.connect(self.receive);self.feed.updated.connect(self.receive_update);self.feed.message.connect(self.report)
  try:
   data=json.loads(self.snapshot.data.decode('utf-8')) if self.snapshot.data else {}
   self.selected=[key for key in VIEW_KEYS if key in data.get('bands',['7'])][:8];self.scope.setCurrentIndex(max(0,self.scope.findData(data.get('scope','all'))));self.connection.load_values(data);self.local.setChecked(bool(data.get('local',True)));self.rbn.setChecked(bool(data.get('rbn',False)))
  except Exception as e:self.settings_error=True;self.report('設定を読めません。元ファイルを保持します：'+str(e))
  self.scope.currentIndexChanged.connect(self.scope_changed)
  self.rebuild();self.timer=QTimer(self);self.timer.timeout.connect(self.refresh);self.timer.start(15000)
 def report(self,text):
  if not self.closing:self.status.setText(text)
 def save_settings(self):
  if self.settings_error:return False
  host,port,own=self.connection.values();data=dict(bands=self.selected,scope=self.scope.currentData(),local=self.local.isChecked(),rbn=self.rbn.isChecked(),host=host,port=port,own=own)
  try:
   self.path.parent.mkdir(parents=True,exist_ok=True)
   with operation_lock(self.path.parent):replace_bytes(self.path,(json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode('utf-8'),self.snapshot)
   self.snapshot=Snapshot.read(self.path);return True
  except Exception as e:self.report('設定を保存できません：'+str(e));return False
 def toggle_band(self,name,on):
  if on and name not in self.selected:
   if len(self.selected)>=8:self.buttons[name].setChecked(False);QMessageBox.information(self,'バンド選択','通常とFTを合わせて8枠までです。');return
   self.selected.append(name)
  elif not on and name in self.selected:self.selected.remove(name)
  self.selected=[key for key in VIEW_KEYS if key in self.selected];self.rebuild();self.save_settings()
 def rebuild(self):
  while self.grid.count():
   item=self.grid.takeAt(0)
   if item.widget():item.widget().hide();item.widget().deleteLater()
  self.panels={}
  for i in range(8):self.grid.setColumnStretch(i,0);self.grid.setRowStretch(i,0)
  n=len(self.selected);cols=n if n<=3 else math.ceil(n/2)
  for name,b in self.buttons.items():b.setChecked(name in self.selected)
  for i,name in enumerate(self.selected):
   band=name.removesuffix('-FT');panel=(FtPanel if name.endswith('-FT') else BandPanel)(next(b for b in BANDS if b[0]==band));self.panels[name]=panel;r,c=divmod(i,cols);self.grid.addWidget(panel,r,c);self.grid.setColumnStretch(c,1);self.grid.setRowStretch(r,1)
  if not n:self.grid.addWidget(QLabel('上のボタンで表示するバンドを選択してください。'),0,0)
  self.refresh()
 def scope_changed(self):self.refresh();self.save_settings()
 def refresh(self):
  self.store.expire()
  for name,panel in self.panels.items():panel.set_spots(self.store.for_band(name.removesuffix('-FT'),self.local.isChecked(),self.rbn.isChecked(),ft=name.endswith('-FT'),region=self.scope.currentData()))
 def receive_update(self,spots):self.receive(spots,False)
 def receive(self,spots,notify):
  if not self.running or self.closing:return
  self.store.add(spots);self.refresh()
 def clear(self):self.store.items.clear();self.refresh()
 def start(self):
  if self.running:return
  try:
   if not self.local.isChecked() and not self.rbn.isChecked():raise ValueError('受信する情報種別を選択してください。')
   if self.rbn.isChecked():self.connection.validate()
   if not self.save_settings():return
   self.running=True;self.feed.subscribe(self,self.local.isChecked(),self.rbn.isChecked(),*self.connection.values())
  except Exception as e:self.running=False;self.report(str(e));return
  self.start_button.setEnabled(False);self.stop_button.setEnabled(True)
  for w in (self.local,self.rbn):w.setEnabled(False)
  self.receive(self.feed.snapshot(self.local.isChecked(),self.rbn.isChecked()),False);self.report('受信中。情報がないバンドには局を表示しません。')
 def stop(self):
  self.running=False;self.feed.unsubscribe(self);self.start_button.setEnabled(True);self.stop_button.setEnabled(False)
  for w in (self.local,self.rbn):w.setEnabled(True)
  self.report('停止中')
 def reject(self):
  if self.closing:return
  self.save_settings();self.stop();self.timer.stop();self.closing=True;self.feed.delivered.disconnect(self.receive);self.feed.updated.disconnect(self.receive_update);self.feed.message.disconnect(self.report);super().reject()
 def closeEvent(self,event):self.reject();event.accept()
