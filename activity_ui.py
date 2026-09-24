"""Party and award selection workspaces backed by untouched source log sessions."""
import json,csv,io
from pathlib import Path
from datetime import date
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QApplication,QVBoxLayout,QHBoxLayout,QFormLayout,QComboBox,QLineEdit,QLabel,QPushButton,QCheckBox,QListWidget,QListWidgetItem,QTableWidget,QTableWidgetItem,QTabWidget,QWidget,QPlainTextEdit,QFileDialog,QMessageBox,QScrollArea,QGroupBox,QGridLayout)
from window_geometry import SafeDialog
from window_tint import apply_window_tint
from activity_filters import FilterPane
from exporting import select_rows
from search import file_identity,hits_to_rows
from storage import Snapshot,replace_bytes,StorageError
from party import PARTIES,exchange,member,stats,jarl_text,xlsx_bytes,hamtte_sheets
from award_registry import AWARDS,Ledger,candidate,list_tsv,universe,target_count

def button(text,fn):
 b=QPushButton(text);b.clicked.connect(fn);return b
class ActivityDialog(SafeDialog):
 def __init__(self,repo,own='',parent=None,award=False,hits=None):
  super().__init__(parent);self.repo=repo;self.award=award;self.imported_hits=list(hits or []) if not award else [];self.rows=[];self.sessions=[];self.loaded=None;self.setWindowTitle(('アワード' if award else 'QSOパーティー')+' — PSLog');self.resize(1350,850);apply_window_tint(self,'award' if award else 'qso_party')
  v=QVBoxLayout(self);self.tabs=QTabWidget();v.addWidget(self.tabs);self.status=QLabel();self.status.setWordWrap(True);v.addWidget(self.status);v.addWidget(button('閉じる',self.reject))
  w=QWidget();f=QFormLayout(w);self.tabs.addTab(w,'1 対象・抽出');self.kind=QComboBox();self.kind.addItems(list(AWARDS) if award else list(PARTIES));
  if not award:
   for i,k in enumerate(PARTIES):self.kind.setItemText(i,PARTIES[k][0]+'（'+PARTIES[k][1]+'）');self.kind.setItemData(i,k)
  f.addRow('アワード' if award else 'パーティー',self.kind)
  if self.imported_hits:
   source_note=QLabel('ログ検索でチェックした交信を使用中です。対象交信は固定され、ここではパーティーの種類や交換内容などを設定します。')
   source_note.setWordWrap(True);source_note.setStyleSheet('color:#b00020; font-weight:bold;');f.addRow(source_note)
  self.year=QLineEdit(str(date.today().year));f.addRow('年度（変更可能）',self.year);self.year.setVisible(not award);self.year.textChanged.connect(self.year_changed)
  self.calls=QListWidget();self.calls.setMaximumHeight(120);calls=sorted({file_identity(p)[1] for p in repo.book.glob('*.txt') if file_identity(p)})
  for c in calls:
   item=QListWidgetItem(c);item.setFlags(item.flags()|Qt.ItemIsUserCheckable);item.setCheckState(Qt.Checked if c==own else Qt.Unchecked);self.calls.addItem(item)
  f.addRow('自局（アワードは同一免許人の個人局を複数選択可）',self.calls)
  self.start=QLineEdit();self.end=QLineEdit()
  for e in (self.start,self.end):e.setPlaceholderText('YYYYMMDDhhmm・先頭だけでも可（空欄は制限なし）')
  f.addRow('開始 JST',self.start);f.addRow('終了 JST（指定分を含む）',self.end);range_note=QLabel('空欄は制限なし。開始は指定期間の先頭、終了は指定期間の末尾として扱います。例：終了 20260917 → 2026/09/17 23:59');range_note.setWordWrap(True);f.addRow(range_note);self.marker=QLineEdit();f.addRow('RMKS判定文字（任意）',self.marker);self.filters=FilterPane(warc=True);f.addRow(self.filters)
  self.sent=QLineEdit();f.addRow('共通送信名／番号（RSTを含めない）',self.sent);self.sent.setVisible(not award)
  self.profile=QLineEdit('特記なし');f.addRow('実績の特記名（DBを分ける）',self.profile);self.profile.setVisible(award)
  self.endorse_band=QComboBox();self.endorse_band.addItems(['指定なし','0.135','0.475','1.9','3.5','7','10','14','18','21','24','28','50','144','430','1200','2400','5600','10000','24000','47000','77000']);f.addRow('周波数特記 MHz',self.endorse_band);self.endorse_band.setVisible(award)
  self.endorse_mode=QComboBox();self.endorse_mode.addItems(['指定なし','AM','FM','SSB','CW','Digital','D-STAR','ATV','SSTV','FAX']);f.addRow('モード特記',self.endorse_mode);self.endorse_mode.setVisible(award)
  self.endorse_other=QComboBox();self.endorse_other.setEditable(True);self.endorse_other.addItems(['指定なし','QRP','QRPp','Satellite','EME','同一都道府県','同一コールエリア','同一スクエア']);f.addRow('その他特記（対象は本人確認）',self.endorse_other);self.endorse_other.setVisible(award)
  self.qsl=QCheckBox('QSL受領済み（.R）のみ');self.qsl.setChecked(True);self.qsl.setVisible(award);f.addRow(self.qsl)
  self.onlynew=QCheckBox('提出・認定済みの単位を除いた候補');self.onlynew.setChecked(True);self.onlynew.setVisible(award);f.addRow(self.onlynew)
  f.addRow(button('候補を抽出して確認一覧へ',self.extract))
  for field in (self.year,self.sent,self.profile,self.endorse_band,self.endorse_mode,self.endorse_other):
   label=f.labelForField(field)
   if label:label.setVisible(not field.isHidden())
  w=QWidget();b=QVBoxLayout(w);self.tabs.addTab(w,'2 確認・選択');b.addWidget(QLabel('申請に使う交信を確認してください。通常は自動で重複を整理して選択済みです。必要な行だけチェックを調整し、終わったら「次へ」で進みます。\n変更は原本ログへ書き戻しません。'))
  self.table=QTableWidget();b.addWidget(self.table);row=QHBoxLayout();b.addLayout(row)
  row.addWidget(button('すべて選択',lambda:self.check_all(True)));row.addWidget(button('すべて選択解除',lambda:self.check_all(False)))
  if award:row.addWidget(button('重複を除いて1単位1件を選択',self.unique))
  row.addStretch();row.addWidget(button('次へ',self.go_submission))
  self.summary_label=QLabel();self.summary_label.setWordWrap(True);b.addWidget(self.summary_label)
  self.table.itemClicked.connect(lambda _item:self.summary())
  w=QWidget();f=QFormLayout(w);scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(w);self.tabs.addTab(scroll,'3 提出・出力');self.info={}
  fields=[('title','提出大会名'),('own','提出コールサイン'),('category','部門コード／JAG会員番号'),('categoryname','部門名称（JAG：一般・電信など）'),('name','氏名'),('address','住所'),('email','メール'),('tel','電話'),('power','最大電力 W'),('opplace','運用地'),('licensedate','免許年月日（ウェルカム）'),('comments','意見／特記事項'),('signature','署名氏名'),('reviewer1','審査者1（コール・氏名）'),('reviewer2','審査者2（コール・氏名）')]
  for k,label in fields:self.info[k]=QLineEdit();f.addRow(label,self.info[k])
  self.info['own'].setText(own)
  self.participant=QComboBox();self.participant.addItems(['一般','会員','N','C','W','HN','HC','HW']);f.addRow('参加区分（本人選択）',self.participant)
  self.jag_mode=QComboBox();self.jag_mode.addItems(['電話','電信','デジタル']);f.addRow('JAG提出部門',self.jag_mode)
  self.participant.currentIndexChanged.connect(self.participant_changed);self.jag_mode.currentIndexChanged.connect(self.participant_changed)
  self.version=QComboBox();self.version.addItems(['R2.1','R1.0']);f.addRow('JARL形式',self.version)
  self.sticker=QComboBox();self.sticker.addItems(['ステッカー不要','ステッカー希望','ステッカー・台紙希望']);f.addRow('JAGステッカー',self.sticker)
  self.oath=QCheckBox('提出内容が事実と相違ないことを確認した');f.addRow(self.oath)
  self.preview_button=button('プレビューを更新',self.preview)
  self.save_button=button('ファイルに保存…',self.save_output)
  self.copy_button=button('カードリスト6列をコピー（C6へ貼付）',self.copy_list);self.copy_button.setVisible(award)
  if award:
   guide=QLabel('選択した交信から提出用カードリストを作成します。内容は下に自動表示されます。\n確認後、「ファイルに保存…」または「カードリスト6列をコピー」を選んでください。')
   guide.setWordWrap(True);guide.setStyleSheet('background:#e7f0f7; border:1px solid #b8cad8; padding:7px; color:#243746;')
   f.addRow(guide)
   actions=QWidget();actions_row=QHBoxLayout(actions);actions_row.setContentsMargins(0,0,0,0);actions_row.setSpacing(6)
   actions_row.addWidget(self.preview_button);actions_row.addWidget(self.save_button);actions_row.addWidget(self.copy_button);actions_row.addStretch()
   f.addRow(actions)
  else:
   f.addRow(self.preview_button);f.addRow(self.save_button)
  self.output=QPlainTextEdit();self.output.setReadOnly(True)
  if award:
   self.output.setMinimumHeight(180);self.output.setMaximumHeight(300)
   f.addRow('提出内容プレビュー',self.output)
   nav=QWidget();navrow=QHBoxLayout(nav);navrow.setContentsMargins(0,0,0,0);navrow.setSpacing(6)
   navrow.addWidget(button('戻る',lambda:self.tabs.setCurrentIndex(1)));navrow.addStretch();navrow.addWidget(button('次へ',lambda:self.tabs.setCurrentIndex(3)))
   f.addRow(nav)
  else:f.addRow(self.output)
  self.submission_form=f
  if award:
   for widget in list(self.info.values())+[self.participant,self.jag_mode,self.version,self.sticker,self.oath]:
    widget.hide();label=f.labelForField(widget)
    if label:label.hide()
  if award:
   w=QWidget();outer4=QVBoxLayout(w);outer4.setContentsMargins(8,8,8,8);outer4.setSpacing(8);self.tabs.addTab(w,'4 実績・履歴（任意）')
   guide=QLabel('この画面は任意です。過去に取得・提出した実績や、今回選んだ交信の申請状況をPSLogへ記録しておく画面です。\n初めて申請するだけなら、この画面は使う必要はありません。提出ファイルの保存は前の「3 提出・出力」で行います。')
   guide.setWordWrap(True);guide.setStyleSheet('background:#e7f0f7; border:1px solid #b8cad8; padding:7px; color:#243746;');outer4.addWidget(guide)

   grid=QGridLayout();grid.setContentsMargins(0,0,0,0);grid.setHorizontalSpacing(10);grid.setVerticalSpacing(8);grid.setColumnStretch(0,1);grid.setColumnStretch(1,1);outer4.addLayout(grid)

   past_box=QGroupBox('過去の取得実績を登録');past=QFormLayout(past_box);past.setVerticalSpacing(6);grid.addWidget(past_box,0,0)
   past_help=QLabel('すでに取得済み・提出済みの地域番号を登録すると、次回以降の候補抽出から除外できます。');past_help.setWordWrap(True);past_help.setStyleSheet('color:#55636c;');past.addRow(past_help)
   self.import_text=QPlainTextEdit();self.import_text.setPlaceholderText('例：100101\n100102\n100201\n\n地域番号を改行・カンマ区切りで貼り付けます。CSV/TSV/TXTでは先頭列を読みます。');self.import_text.setMinimumHeight(70);self.import_text.setMaximumHeight(95);past.addRow('既存実績の番号一覧（任意）',self.import_text)
   import_row=QWidget();ir=QHBoxLayout(import_row);ir.setContentsMargins(0,0,0,0);ir.setSpacing(6);ir.addWidget(button('ファイルから読込…',self.read_units));ir.addWidget(button('地域一覧から選ぶ…',self.pick_units));ir.addStretch();past.addRow(import_row)
   self.remaining=QCheckBox('入力した番号が「未取得・残り」の一覧');self.remaining.setToolTip('チェックすると、基準一覧との差分を取得済み実績として登録します。');past.addRow(self.remaining)
   self.claim_status=QComboBox();self.claim_status.addItems(['認定済み','提出済み','未交信','QSL未受領','未申請']);past.addRow('番号一覧の状態',self.claim_status)
   status_help=QLabel('認定済みなら「認定済み」、申請済みで結果待ちなら「提出済み」を選びます。');status_help.setWordWrap(True);status_help.setStyleSheet('color:#55636c;');past.addRow('',status_help)
   past.addRow(button('番号一覧を実績DBへ登録…',self.import_claims))

   current_box=QGroupBox('今回選択した交信を履歴に記録');current=QFormLayout(current_box);current.setVerticalSpacing(6);grid.addWidget(current_box,0,1);self.history_form=current
   current_help_top=QLabel('タブ2で選んだ交信について、候補・提出済み・認定済みなどの状態を申請履歴として残します。');current_help_top.setWordWrap(True);current_help_top.setStyleSheet('color:#55636c;');current.addRow(current_help_top)
   self.level=QLineEdit();self.level.setPlaceholderText('例：JCC200 / AJA1000 / 18MHz賞 100局');self.number=QLineEdit();self.number.setPlaceholderText('例：12345（発行番号がある場合のみ）');current.addRow('取得段階・クラス名（任意）',self.level);current.addRow('既得アワード発行番号（任意）',self.number)
   self.app_status=QComboBox();self.app_status.addItems(['候補','提出済み','認定済み']);current.addRow('今回選択した交信の状態',self.app_status)
   current.addRow(button('今回選択した交信を申請履歴へ記録…',self.record_application))
   self.aja_import_status=QComboBox();self.aja_import_status.addItems(['提出済み','認定済み','候補']);current.addRow('AJA表を取り込む場合の状態',self.aja_import_status)
   self.aja_import_button=button('記入済みAJA表（xls/xlsx）を取り込む…',self.import_aja);current.addRow(self.aja_import_button)

   history_box=QGroupBox('登録済み実績');history_layout=QVBoxLayout(history_box);history_layout.setSpacing(6);grid.addWidget(history_box,1,0,1,2)
   history_help=QLabel('PSLogに保存されている過去の取得・申請履歴を確認します。通常は直接編集する必要はありません。');history_help.setWordWrap(True);history_help.setStyleSheet('color:#55636c;');history_layout.addWidget(history_help)
   self.history=QPlainTextEdit();self.history.setMinimumHeight(90);self.history.setMaximumHeight(125);self.history.setPlaceholderText('「登録済み実績を表示」を押すと、PSLogが管理している実績データを表示します。');history_layout.addWidget(self.history)
   history_row=QWidget();hr=QHBoxLayout(history_row);hr.setContentsMargins(0,0,0,0);hr.setSpacing(6);hr.addWidget(button('登録済み実績を表示',self.show_history));hr.addWidget(button('表示内容で上書き保存…',self.edit_history));hr.addStretch();history_layout.addWidget(history_row)

   nav4=QWidget();n4=QHBoxLayout(nav4);n4.setContentsMargins(0,0,0,0);n4.setSpacing(6);n4.addWidget(button('戻る（提出・出力）',lambda:self.tabs.setCurrentIndex(2)));n4.addStretch();outer4.addWidget(nav4)
  self.kind.currentIndexChanged.connect(self.defaults);self.defaults()
  self.prefs_path=self.repo.root/'config'/('award_workspace.json' if award else 'party_workspace.json');self.prefs_snap=Snapshot.read(self.prefs_path)
  if self.prefs_snap.data:
   try:
    prefs=json.loads(self.prefs_snap.data.decode('utf-8'))
    for k,val in prefs.get('info',{}).items():
     if k in self.info and k not in ('title','category','categoryname'):self.info[k].setText(str(val))
    self.sent.setText(prefs.get('sent',''))
   except (ValueError,TypeError):self.status.setText('前回の入力設定を読めません。既存ファイルは保存時に上書きしません。');self.prefs_snap=None
  if self.imported_hits:
   self.extract();self.tabs.setCurrentIndex(1)
   self.status.setText('ログ検索でチェックした交信を読み込みました。「1 対象・抽出」でパーティーを設定し、「候補を抽出して確認一覧へ」を押して内容を更新してください。')
 def reject(self):
  if getattr(self,'prefs_snap',None) is not None:
   try:
    values={'info':{k:e.text() for k,e in self.info.items()},'sent':self.sent.text()}
    replace_bytes(self.prefs_path,json.dumps(values,ensure_ascii=False,indent=2).encode(),self.prefs_snap)
   except (OSError,StorageError) as e:
    self.status.setText('入力設定を保存できません：'+str(e));return
  super().reject()
 def kind_id(self):return self.kind.currentText() if self.award else self.kind.currentData()
 def year_changed(self):
  if not self.award and hasattr(self,'info'):
   k=self.kind_id();self.kind.setItemText(self.kind.currentIndex(),PARTIES[k][0]+'（'+self.year.text()+'）');self.info['title'].setText(PARTIES[k][0].replace('100周年/','')+'（'+self.year.text()+'）')
 def participant_changed(self):
  if self.award:return
  k=self.kind_id();p=self.participant.currentText()
  if k=='jag_warc':
   self.info['categoryname'].setText(('会員' if p=='会員' else '一般')+'・'+self.jag_mode.currentText())
   for name,c in self.filters.modes.items():c.setChecked(name=={'電話':'FM/SSB/AM','電信':'CW'}.get(self.jag_mode.currentText()) or self.jag_mode.currentText()=='デジタル' and name in ('FT*','その他'))
   if p!='会員':self.info['category'].clear()
  elif k=='welcome':self.info['category'].setText(p if p in ('N','C','W','HN','HC','HW') else '')
  elif k.startswith('hamtte'):self.info['category'].setText(p)
 def owners(self):return [self.calls.item(i).text() for i in range(self.calls.count()) if self.calls.item(i).checkState()==Qt.Checked]
 def defaults(self):
  if self.award:
   from special_awards import is_anniversary,is_japan,is_world
   aja=self.kind_id()=='AJA';anniv=is_anniversary(self.kind_id());japan=is_japan(self.kind_id());world=is_world(self.kind_id());special=anniv or japan or world
   if aja or japan:self.endorse_band.setCurrentText('指定なし')
   self.endorse_band.setEnabled(not aja and not japan);self.endorse_mode.setEnabled(True);self.endorse_other.setEnabled(not japan)
   self.endorse_band.setToolTip('AJAは周波数特記を付けられません。各バンドはポイント計数に使用します。' if aja else '全日本10,000局系の特記はSINGLE MODEのみです。' if japan else '')
   self.copy_button.setVisible(not aja and not special);self.aja_import_status.setVisible(aja);self.aja_import_button.setVisible(aja)
   for widget in (self.aja_import_status,self.aja_import_button):
    label=self.history_form.labelForField(widget)
    if label:label.setVisible(aja)
   for key in ('own','name','signature','reviewer1','reviewer2'):
    show=(aja or special) and (key not in ('reviewer1','reviewer2') or japan or world);widget=self.info[key];widget.setVisible(show);label=self.submission_form.labelForField(widget)
    if label:label.setVisible(show)
   self.qsl.setEnabled(not anniv);self.qsl.setChecked(not anniv)
   award_type=AWARDS[self.kind_id()][1]
   if award_type.startswith('band:'):
    from activity_filters import band_group
    target_group=band_group(award_type.split(':',1)[1])
    for name,c in self.filters.bands.items():c.setChecked(name==target_group)
   else:
    for c in self.filters.bands.values():c.setChecked(True)
   if anniv:self.start.setText('202606010000');self.end.setText('202710010000')
   else:self.start.clear();self.end.clear()
   self.status.setText('AJAは地域×バンドと同一コール×同一バンドを重複させず、2バンド以上を確認します。' if aja else '100周年はQSL不要です。記念運用局はRMKSの確認タグで指定します。' if anniv else 'QSL受領済みの同一局を1回だけ数え、専用条件と帳票を確認します。' if special else '')
  else:
   k=self.kind_id();name,y,start,end=PARTIES[k];self.year.setText(y);self.start.setText(start);self.end.setText(end);self.info['title'].setText(name.replace('100周年/','')+'（'+y+'）');self.participant.setVisible(k!='nyp');self.jag_mode.setVisible(k=='jag_warc');self.info['categoryname'].setVisible(k=='jag_warc');self.sticker.setVisible(k=='jag_warc')
   self.status.setText('初期期間は確認済み資料の開催回です。年度と日時は変更できます。')
   for widget in (self.participant,self.jag_mode,self.info['categoryname'],self.sticker):
    label=self.submission_form.labelForField(widget)
    if label:label.setVisible(not widget.isHidden())
   bands={'jag_warc':{'10','18','24'},'welcome':{'3.5以下','7','21','28','50','144','430','1200以上'}}.get(k)
   if k.startswith('hamtte'):bands={'3.5以下','7','21','50','144','430','1200以上'}
   for name,c in self.filters.bands.items():c.setChecked(bands is None or name in bands)
   if k=='welcome':self.participant.setCurrentText('HW')
   elif k!='nyp':self.participant.setCurrentText('一般')
   self.participant_changed()
 def scope(self):return self.kind_id(),tuple(self.owners()),self.start.text(),self.end.text(),self.marker.text(),self.filters.state(),self.profile_id(),self.qsl.isChecked(),self.onlynew.isChecked()
 def profile_id(self):return self.profile.text()+' / '+' / '.join(c.currentText() for c in (self.endorse_band,self.endorse_mode,self.endorse_other) if c.currentText()!='指定なし')
 def ledger(self):return Ledger(self.repo.root,self.kind_id(),self.profile_id(),','.join(sorted(self.owners())))
 def guard(self):
  if self.loaded!=self.scope():raise ValueError('抽出条件が変わりました。候補を再抽出してください。')
  for s in self.sessions:s.snapshot.check(s.path)
 def extract(self):
  try:
   owners=self.owners()
   if not owners:raise ValueError('自局を選択してください。')
   if not self.award and len(owners)!=1:raise ValueError('パーティーは自局を1つ選択してください。')
   if self.imported_hits and not self.award:
    imported_owners=sorted({h.own for h in self.imported_hits})
    if len(imported_owners)!=1:raise ValueError('検索結果には自局を1つだけ含めてください。')
    owners=imported_owners
    sessions,src=hits_to_rows(self.imported_hits)
   else:
    paths=[p for p in self.repo.book.glob('*.txt') if file_identity(p) and file_identity(p)[1] in owners]
    from sota_export import minute_boundary
    sessions,src=select_rows(self.repo,paths,minute_boundary(self.start.text(),False) if self.start.text() else '',minute_boundary(self.end.text(),True) if self.end.text() else '')
   rows=[]
   ledger=self.ledger() if self.award else None;used=ledger.used() if self.award and self.onlynew.isChecked() else set();used_stations=ledger.used_station_keys() if self.award and self.onlynew.isChecked() and self.kind_id()=='AJA' else set()
   import countries
   countrydb=countries.load(self.repo.root) if self.award else None
   for row in src:
    own,q,path,line=row
    if not self.imported_hits and (not self.filters.accepts(q) or self.marker.text() and self.marker.text().casefold() not in q.remarks.casefold()):continue
    if self.award:
     from activity_filters import band_value,norm,mode_group
     if self.endorse_band.currentText()!='指定なし' and band_value(q.band)!=float(self.endorse_band.currentText()):continue
     mode=self.endorse_mode.currentText()
     if mode!='指定なし' and not (norm(q.mode)==mode.upper() or mode=='Digital' and (mode_group(q.mode)=='FT*' or norm(q.mode) in ('RTTY','PSK','PSK31','JT65','JT9','MFSK','OLIVIA','DIGITAL','DATA'))):continue
     try:
      r=candidate(self.kind_id(),row,countrydb)
     except ValueError as e:
      # A single ambiguous callsign (typically a slash form where the base call
      # cannot be chosen uniquely) must not abort the whole award extraction.
      # Keep it visible as an unchecked review row so the user can identify the
      # exact QSO and decide whether/how to correct the counting unit.
      if self.qsl.isChecked() and not q.confirmed:continue
      r=dict(unit='',own=own,call=q.call,date=q.date,time=q.time,band=q.band,mode=q.mode,
             remarks=q.remarks,qth=q.his_qth,code=q.code,confirmed=q.confirmed,
             notes='候補判定できません：'+str(e),path=str(path),line=line,
             _candidate_error=True)
      r['output_notes']=' / '.join(c.currentText() for c in (self.endorse_band,self.endorse_mode,self.endorse_other) if c.currentText()!='指定なし')
      rows.append(r);continue
     if not r.get('unit'):continue
     r['output_notes']=' / '.join(c.currentText() for c in (self.endorse_band,self.endorse_mode,self.endorse_other) if c.currentText()!='指定なし')
     if self.qsl.isChecked() and not r['confirmed']:continue
     if r['unit'] in used:continue
     if self.kind_id()=='AJA' and r.get('station_key') in used_stations:continue
    else:
     r=dict(own=own,date=q.date,time=q.time,band=q.band,mode=q.mode,call=q.call,remarks=q.remarks,rst_sent=q.sent,rst_received=q.received,sent=self.sent.text(),received=exchange(self.kind_id(),q.remarks,q.received,self.marker.text()),member=member(q.remarks),path=str(path),line=line)
    rows.append(r)
   self.sessions,self.rows=sessions,rows
   self.loaded=self.scope();self.draw();self.info['own'].setText(','.join(owners));self.tabs.setCurrentIndex(1);self.summary()
   problem_rows=sum(bool(r.get('_candidate_error')) for r in rows)
   if rows:
    self.status.setText('候補を '+str(len(rows)-problem_rows)+'件抽出しました。'+((' 基本コール等を判定できない要確認QSOが '+str(problem_rows)+'件あります。') if problem_rows else '')+' 確認・選択タブで内容を確認してください。')
   else:self.status.setText('条件に合う候補は0件でした。確認・選択タブへ移動しました。')
  except (ValueError,OSError,StorageError) as e:
   message='候補を抽出できません：'+str(e);self.status.setText(message);QMessageBox.warning(self,'アワード候補の抽出',message)
 def draw(self):
  if self.award:
   from special_awards import is_anniversary,is_japan,is_world
   extra=['unit']
   if is_anniversary(self.kind_id()):extra+=['anniv_type','extra_region','pref','area']
   elif is_japan(self.kind_id()):extra+=['licensee','pref','area']
   elif is_world(self.kind_id()):extra+=['licensee','entity','itu','continent','japan_group']
   self.columns=['use','date','time','call','band','mode','remarks']+extra+['output_notes','notes']
  else:self.columns=['use','date','time','call','band','mode','remarks','rst_sent','sent','rst_received','received','member']
  labels={'use':'提出対象','date':'交信日','time':'時刻 JST','call':'相手コール','band':'BAND','mode':'MODE','remarks':'原本RMKS','unit':'地域・計数単位（修正可）','licensee':'同一コール別免許人（氏名等）','anniv_type':'100周年局種別','extra_region':'別に定める運用地','pref':'都道府県番号','area':'コールエリア','entity':'ARRL Entity候補','itu':'ITU Zone候補','continent':'大陸候補','japan_group':'日本局区分','output_notes':'出力備考','notes':'確認事項','rst_sent':'送信RST','sent':'送信名・番号','rst_received':'受信RST','received':'受信名・番号','member':'HAMtte会員'}
  self.table.setColumnCount(len(self.columns));self.table.setHorizontalHeaderLabels([labels[k] for k in self.columns]);self.table.setRowCount(len(self.rows))
  for i,r in enumerate(self.rows):
   for j,k in enumerate(self.columns):
    item=QTableWidgetItem(str(r.get(k,'')))
    if k in ('use','member'):
     item.setText('');item.setFlags(Qt.ItemIsEnabled|Qt.ItemIsUserCheckable)
     checked=(k=='use' and not r.get('_candidate_error')) or (k=='member' and bool(r.get(k)))
     item.setCheckState(Qt.Checked if checked else Qt.Unchecked)
    elif k in ('remarks','notes'):item.setFlags(item.flags()&~Qt.ItemIsEditable)
    self.table.setItem(i,j,item)
  self.table.resizeColumnsToContents();self.table.setColumnWidth(self.columns.index('remarks'),220)
  if self.award:self.unique()
 def go_submission(self):
  self.summary()
  if not self.selected():
   self.status.setText('提出対象を1件以上選択してください。');return
  self.status.clear();self.tabs.setCurrentIndex(2)
  if self.award:self.preview()
 def check_all(self,on):
  for i in range(self.table.rowCount()):self.table.item(i,0).setCheckState(Qt.Checked if on else Qt.Unchecked)
  self.summary()
 def selected(self):
  out=[]
  for i,r in enumerate(self.rows):
   if self.table.item(i,0).checkState()!=Qt.Checked:continue
   r=dict(r)
   for j,k in enumerate(self.columns[1:],1):
    r[k]=self.table.item(i,j).checkState()==Qt.Checked if k=='member' else self.table.item(i,j).text()
   if self.award and self.kind_id()=='AJA':
    from aja import region_kind
    from contest_regional import base_call
    parts=r.get('unit','').rsplit('@',1)
    if len(parts)==2:
     r['region'],r['aja_band']=parts;r['region_type']=region_kind(r['region'],r.get('date',''))[0];r['station_key']=base_call(r.get('call',''))+'@'+r['aja_band']
   elif self.award:
    from special_awards import is_ten_thousand
    if is_ten_thousand(self.kind_id()) and r.get('licensee','').strip():r['unit']=base_call(r.get('call',''))+'#'+r['licensee'].strip()
   out.append(r)
  return out
 def unique(self):
  from special_awards import SPECIAL_AWARDS,selection_indices
  if self.kind_id() in SPECIAL_AWARDS:
   live=[]
   for i,r in enumerate(self.rows):
    item=dict(r)
    for key in ('call','band','unit','licensee'):
     if key not in self.columns:continue
     item[key]=self.table.item(i,self.columns.index(key)).text()
    live.append(item)
   chosen=set(selection_indices(self.kind_id(),live))
   for i in range(self.table.rowCount()):self.table.item(i,0).setCheckState(Qt.Checked if i in chosen else Qt.Unchecked)
   self.summary();return
  seen=set();stations=set();j=self.columns.index('unit');callj=self.columns.index('call')
  for i in range(self.table.rowCount()):
   u=self.table.item(i,j).text();station=''
   if self.kind_id()=='AJA' and '@' in u:
    from contest_regional import base_call
    station=base_call(self.table.item(i,callj).text())+'@'+u.rsplit('@',1)[1]
   on=bool(u) and u not in seen and (not station or station not in stations);self.table.item(i,0).setCheckState(Qt.Checked if on else Qt.Unchecked)
   if on:seen.add(u);stations.add(station) if station else None
  self.summary()
 def summary(self):
  rows=self.selected()
  if self.award and self.kind_id()=='AJA':
   from aja import distinct,stats as aja_stats
   cumulative,_=distinct(self.ledger().used_records()+rows);s=aja_stats(cumulative);warning='2バンド未満です。' if s['bands']<2 else ''
   self.summary_label.setText(f'候補 {len(self.rows)}行 ／ 今回選択 {len(rows)}ポイント ／ 累計詳細 {s["points"]}ポイント（市{s["cities"]}・郡{s["guns"]}・区{s["wards"]}、{s["bands"]}バンド）。{warning}\n同一コール・同一バンドと地域・バンドの重複は1件だけ選択します。')
  elif self.award:
   from special_awards import SPECIAL_AWARDS,metrics
   if self.kind_id() in SPECIAL_AWARDS:
    cumulative=self.ledger().used_records()+rows;m=metrics(self.kind_id(),cumulative);details=''
    if 'pref_sets' in m:details=f' ／ 47都道府県セット {m["pref_sets"]}/{m["required_sets"]}'
    if 'entities' in m:details=f' ／ Entity {m["entities"]}/{m["requirements"][0]}・ITU {m["itus"]}/{m["requirements"][1]}・大陸 {m["continents"]}/{m["requirements"][2]}'
    self.summary_label.setText(f'候補 {len(self.rows)}行 ／ 今回選択 {len(rows)} ／ 累計詳細 {m["selected"]}/{m["target"]}{details} ／ '+('条件充足候補' if m['complete'] else '未達または要確認')+'\n'+'\n'.join(m['warnings'][:5]))
   else:self.summary_label.setText(f'候補 {len(self.rows)}行 ／ 選択 {len(rows)}行 ／ 異なる単位 {len({r["unit"] for r in rows})} ／ 初回・全地域の参考目標 {target_count(self.repo.root,self.kind_id())}。追加段階は実績タブで指定。地域・QSL・特記は確認のうえ選択してください。')
  else:
   s=stats(self.kind_id(),rows);self.summary_label.setText(f'選択 {s["rows"]}行 ／ 参考局数 {s["units"]} ／ メンバー {s["members"]}\n'+'\n'.join(s['warnings'][:8]))
 def info_values(self):
  d={k:e.text() for k,e in self.info.items()};d.update(version=self.version.currentText(),sticker=self.sticker.currentText(),oath=self.oath.isChecked());return d
 def output_data(self):
  self.guard();rows=self.selected()
  if not rows:raise ValueError('対象を選択してください。')
  if self.award:
   rows.sort(key=lambda r:(r['unit'],r['band'],r['call'],r['date']))
   if any(not r['unit'] for r in rows):raise ValueError('空欄の計数単位を確認してください。')
   if self.kind_id()=='AJA':
    from aja import distinct,xlsx_bytes as aja_xlsx
    cumulative,warnings=distinct(self.ledger().used_records()+rows)
    if len({r.get('aja_band') or r['unit'].rsplit('@',1)[-1] for r in cumulative})<2:self.status.setText('AJAは2バンド以上が必要です。確認用Excelは作成できます。')
    return aja_xlsx(self.repo.root,cumulative,self.info_values()),'.xlsx'
   from special_awards import SPECIAL_AWARDS,selection_indices,workbook_bytes
   if self.kind_id() in SPECIAL_AWARDS:
    cumulative=self.ledger().used_records()+rows;indices=selection_indices(self.kind_id(),[dict(r) for r in cumulative]);cumulative=[cumulative[i] for i in indices]
    return workbook_bytes(self.kind_id(),cumulative,self.info_values()),'.xlsx'
   return list_tsv(rows).encode('utf-8-sig'),'.tsv'
  info=self.info_values();text=jarl_text(self.kind_id(),rows,info)
  if self.kind_id().startswith('hamtte'):return xlsx_bytes(hamtte_sheets(rows,info)),'.xlsx'
  return text.encode('cp932'),'.txt'
 def preview(self):
  try:
   data,ext=self.output_data()
   if ext=='.xlsx':
    if self.award:self.output.setPlainText(('AJA-Listと累計記録表' if self.kind_id()=='AJA' else '専用申請書と交信・集計リスト')+f'を作成します。\nExcelサイズ：{len(data):,} bytes\nプレビューは保存後にExcelで確認してください。')
    else:self.output.setPlainText(json.dumps(hamtte_sheets(self.selected(),self.info_values()),ensure_ascii=False,indent=2))
   else:self.output.setPlainText(data.decode('utf-8-sig' if ext=='.tsv' else 'cp932'))
  except (ValueError,OSError,StorageError) as e:
   message=str(e);self.status.setText(message);self.output.setPlainText('プレビューを作成できません。\n'+message)
 def save_output(self):
  try:
   from special_awards import SPECIAL_AWARDS
   data,ext=self.output_data();stem='AJA-list' if self.award and self.kind_id()=='AJA' else ('special-award-list' if self.award and self.kind_id() in SPECIAL_AWARDS else 'award-list' if self.award else self.kind_id());path,_=QFileDialog.getSaveFileName(self,'保存',str(self.repo.root/stem)+ext,'*'+ext)
   if path:
    target=Path(path).resolve()
    if target.is_relative_to(self.repo.book.resolve()):raise ValueError('原本ログのフォルダーには提出ファイルを保存できません。別の保存先を選んでください。')
    replace_bytes(target,data,Snapshot.read(target));self.status.setText('保存しました。元ログは変更していません。')
  except (ValueError,OSError,StorageError) as e:self.status.setText(str(e))
 def copy_list(self):
  try:
   if not self.award or self.kind_id()=='AJA':raise ValueError('AJAは専用Excelへ出力してください。')
   data,_=self.output_data();QApplication.clipboard().setText(data.decode('utf-8-sig'));self.status.setText('6列のカードリストをコピーしました。ExcelのC6へ貼り付けできます。')
  except (ValueError,StorageError) as e:self.status.setText(str(e))
 def pick_units(self):
  try:
   known=sorted(universe(self.repo.root,self.kind_id()))
   if not known:raise ValueError('このアワードには地域一覧がありません。番号を入力してください。')
   d=SafeDialog(self);d.setWindowTitle('地域を選択');v=QVBoxLayout(d);lst=QListWidget();v.addWidget(lst)
   for u in known:
    i=QListWidgetItem(u);i.setFlags(i.flags()|Qt.ItemIsUserCheckable);i.setCheckState(Qt.Unchecked);lst.addItem(i)
   v.addWidget(button('選択を入力欄へ',d.accept));v.addWidget(button('キャンセル',d.reject))
   if d.exec()==d.Accepted:self.import_text.setPlainText('\n'.join(lst.item(i).text() for i in range(lst.count()) if lst.item(i).checkState()==Qt.Checked))
  except (ValueError,OSError,StorageError) as e:self.status.setText(str(e))
 def read_units(self):
  p,_=QFileDialog.getOpenFileName(self,'番号リストを読む','','CSV/TXT (*.csv *.tsv *.txt)')
  if p:
   try:
    raw=Path(p).read_bytes()
    try:text=raw.decode('utf-8-sig')
    except UnicodeDecodeError:text=raw.decode('cp932')
    delimiter='\t' if '\t' in text else ',';self.import_text.setPlainText('\n'.join(r[0] for r in csv.reader(io.StringIO(text),delimiter=delimiter) if r and r[0].strip() and r[0].strip().lower() not in ('unit','地域番号','市郡番号','番号','code')))
   except (OSError,UnicodeError) as e:self.status.setText(str(e))
 def import_claims(self):
  try:
   text=self.import_text.toPlainText();l=self.ledger();units,status=l.preview_units(text,self.remaining.isChecked(),self.claim_status.currentText());n=len(universe(self.repo.root,self.kind_id()));message=f'対象：{self.kind_id()} / {self.profile_id()}\n基準一覧 {n}単位（同梱の現行地域一覧）。登録 {len(units)}単位 / {status}\n本人申告として登録する番号：\n'+', '.join(sorted(units))
   if QMessageBox.question(self,'実績の登録',message)!=QMessageBox.Yes:return
   count=l.import_units(text,self.remaining.isChecked(),self.claim_status.currentText());self.status.setText(f'{count}単位を登録しました。');self.show_history()
  except (ValueError,OSError,StorageError) as e:self.status.setText(str(e))
 def import_aja(self):
  if not self.award or self.kind_id()!='AJA':return
  path,_=QFileDialog.getOpenFileName(self,'記入済みAJA表を読む','','AJA Excel (*.xls *.xlsx)')
  if not path:return
  try:
   from aja import import_workbook,stats as aja_stats
   result=import_workbook(path)
   if not result['records']:raise ValueError('記入済みのAJA交信を見つけられません。')
   s=aja_stats(result['records']);message=f'読取 {result["read"]}件 ／ 重複整理後 {result["selected"]}ポイント\n市 {s["cities"]}・郡 {s["guns"]}・区 {s["wards"]} ／ {s["bands"]}バンド\n状態：{self.aja_import_status.currentText()}\n\n元のExcelは変更しません。実績DBへ取り込みますか？'
   if result['warnings']:message+='\n\n確認事項：\n'+'\n'.join(result['warnings'][:8])
   if QMessageBox.question(self,'AJA表の取込',message)!=QMessageBox.Yes:return
   count=self.ledger().import_records(result['records'],self.aja_import_status.currentText(),'記入済みAJA表取込：'+Path(path).name);self.status.setText(f'AJA実績 {count}件を取り込みました。元のExcelは変更していません。');self.show_history()
  except (ValueError,OSError,StorageError) as e:self.status.setText(str(e))
 def record_application(self):
  try:
   if self.loaded is not None:self.guard();records=self.selected()
   else:
    if not self.level.text().strip():raise ValueError('既得段階を入力するか、今回の対象を抽出してください。')
    records=[]
   self.ledger().application(records,self.app_status.currentText(),self.number.text(),self.level.text());self.show_history()
   if not records:self.status.setText('既得段階を記録しました。使用地域が未登録のため追加分の照合はできません。')
  except (ValueError,OSError,StorageError) as e:self.status.setText(str(e))
 def show_history(self):
  try:self.history_ledger=self.ledger();self.history.setPlainText(json.dumps(self.history_ledger.data,ensure_ascii=False,indent=2))
  except (ValueError,OSError,StorageError) as e:self.status.setText(str(e))
 def edit_history(self):
  try:
   l=self.history_ledger
   if l.path!=self.ledger().path:raise ValueError('選択が変わりました。実績を再表示してください。')
   data=json.loads(self.history.toPlainText())
   if any(data.get(k)!=l.data[k] for k in ('schema','award','profile','owners')):raise ValueError('識別情報は変更できません。')
   if not isinstance(data.get('claims'),list) or not isinstance(data.get('applications'),list):raise ValueError('実績の形式が不正です。')
   l.data=data;l.save();self.status.setText('訂正を保存しました。以前の実績はバックアップに保持しました。')
  except (AttributeError,ValueError,OSError,StorageError) as e:self.status.setText(str(e))
