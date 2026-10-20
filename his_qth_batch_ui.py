"""Explicit internet lookup, bounded worker, review and guarded save."""
import time,math
from PySide6.QtCore import Qt,QThread,Signal,QTimer,QEvent
from PySide6.QtWidgets import QVBoxLayout,QHBoxLayout,QLabel,QComboBox,QListWidget,QListWidgetItem,QLineEdit,QCheckBox,QTableWidget,QTableWidgetItem,QPushButton,QAbstractItemView,QMessageBox,QHeaderView
from window_geometry import SafeDialog
from window_tint import apply_window_tint
from logbook_sources import amateur_log_files,amateur_station_calls,file_identity,base_station_call
from storage import VERSION
import his_qth_batch as batch

class LookupThread(QThread):
    completed=Signal(object,str);failed=Signal(str);progressed=Signal(int,int,str)
    def __init__(self,repo,paths,own,limit,include_code,parent,start_at=''):
        super().__init__(parent);self.repo=repo;self.paths=paths;self.own=own;self.limit=limit;self.include_code=include_code;self.start_at=start_at
    def run(self):
        try:
            rows,status=batch.lookup_batch(self.repo,self.paths,self.own,self.limit,self.include_code,cancelled=self.isInterruptionRequested,progress=self.progressed.emit,start_at=self.start_at)
            self.completed.emit(rows,status)
        except Exception as e:self.failed.emit(str(e))

class HisQthBatchDialog(SafeDialog):
    def __init__(self,repo,own='',parent=None):
        super().__init__(parent);self.repo=repo;self.rows=[];self.thread=None;self.saved=False;self.cooldown_until=0.0;self._busy=False
        self.cooldown_timer=QTimer(self);self.cooldown_timer.setInterval(200);self.cooldown_timer.timeout.connect(self.update_cooldown)
        self.setWindowTitle(f'PSLog Ver{VERSION} — HIS QTH作成');self.resize(1150,760);apply_window_tint(self,'edit')
        v=QVBoxLayout(self);note=QLabel('［A］日本の局のみ総務省DBから引用（要インターネット、/1・/Pなどはスキップ）\nHIS QTHがJapanのみ、または空欄の交信を対象にします。照会間隔は2秒。日時の古い順に取得し、変更内容を確認してログに反映します。');note.setWordWrap(True);v.addWidget(note)
        row=QHBoxLayout();row.addWidget(QLabel('自局コール'));self.own=QComboBox();self.own.addItems(amateur_station_calls(repo,own));row.addWidget(self.own);row.addWidget(QLabel('1回の処理件数'));self.limit=QComboBox();self.limit.addItems(['10','20','30','40','50','70','90']);self.limit.setCurrentText('20');row.addWidget(self.limit);v.addLayout(row)
        row=QHBoxLayout();row.addWidget(QLabel('開始日時（JST）'));self.start_at=QLineEdit();self.start_at.setMaxLength(100);self.start_at.setPlaceholderText('YYYYMMDDHHii ／ 空欄なら先頭から');row.addWidget(self.start_at);v.addLayout(row)
        self.logs=QListWidget();self.logs.setMaximumHeight(150);v.addWidget(self.logs)
        select=QPushButton('ログを全て選択');select.clicked.connect(lambda:[self.logs.item(n).setCheckState(Qt.CheckState.Checked) for n in range(self.logs.count())]);v.addWidget(select)
        self.include_code=QCheckBox('JCC/JCGが空欄の場合は、あわせて補完する');self.include_code.setChecked(True);v.addWidget(self.include_code)
        self.table=QTableWidget(0,10);self.table.setHorizontalHeaderLabels(['反映','DATE','TIME JST','相手コール','HIS QTH（変更後）','JCC/JCG（変更後）','免許開始日','免許満了・有効期間','結果','元ログ']);self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        header=self.table.horizontalHeader();header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive);header.setMinimumSectionSize(40)
        for col,width in enumerate((48,105,80,95,210,145,115,155,260,165)):
            self.table.setColumnWidth(col,max(width,self.table.fontMetrics().horizontalAdvance(self.table.horizontalHeaderItem(col).text())+22))
        self.table.viewport().installEventFilter(self);self.table.itemChanged.connect(self.selection_changed);v.addWidget(self.table,1)
        self.status=QLabel('対象ログを選択してください。取得済みの詳細QTHは次回の処理から除外します。');self.status.setWordWrap(True);v.addWidget(self.status)
        row=QHBoxLayout();self.lookup_button=QPushButton('取得・確認');self.lookup_button.clicked.connect(self.run);row.addWidget(self.lookup_button);self.cancel_button=QPushButton('取得を中止');self.cancel_button.setEnabled(False);self.cancel_button.clicked.connect(self.cancel);row.addWidget(self.cancel_button)
        self.save_button=QPushButton('チェックした結果をログに反映');self.save_button.setEnabled(False);self.save_button.clicked.connect(self.save);row.addWidget(self.save_button);self.close_button=QPushButton('閉じる');self.close_button.clicked.connect(self.reject);row.addWidget(self.close_button);v.addLayout(row)
        self.include_code.toggled.connect(self.update_code_preview)
        self.own.currentTextChanged.connect(self.find_logs);self.find_logs()
    def update_code_preview(self,on):
        from dataclasses import replace
        for c in self.rows:
            if c.after is not None:c.after=replace(c.after,code=c.obtained_code if on and not c.qso.code.strip() else c.qso.code)
        if self.rows:self.render(self.rows,'')
    def find_logs(self):
        self.logs.clear();self.rows=[];self.table.setRowCount(0);self.save_button.setEnabled(False)
        for path in amateur_log_files(self.repo):
            if base_station_call(file_identity(path)[1])==base_station_call(self.own.currentText()):
                i=QListWidgetItem(path.name);i.setData(Qt.ItemDataRole.UserRole,str(path));i.setFlags(i.flags()|Qt.ItemFlag.ItemIsUserCheckable);i.setCheckState(Qt.CheckState.Unchecked);self.logs.addItem(i)
    def run(self):
        if self.thread or time.monotonic()<self.cooldown_until:return
        try:start_at=batch.validate_start(self.start_at.text().strip())
        except ValueError as e:self.status.setText(str(e));return
        if self.rows and any(c.after for c in self.rows):
            if QMessageBox.question(self,'未保存の取得結果','未保存の取得結果を破棄して再取得しますか？')!=QMessageBox.StandardButton.Yes:return
        paths=[self.logs.item(n).data(Qt.ItemDataRole.UserRole) for n in range(self.logs.count()) if self.logs.item(n).checkState()==Qt.CheckState.Checked]
        if not paths:self.status.setText('対象ログを選択してください。');return
        self.rows=[];self.table.setRowCount(0);self.busy(True)
        t=LookupThread(self.repo,paths,self.own.currentText(),int(self.limit.currentText()),self.include_code.isChecked(),self,start_at);self.thread=t
        t.progressed.connect(lambda done,total,call:self.status.setText(f'処理 {done}/{total}件　{call}'))
        t.completed.connect(self.render);t.failed.connect(self.status.setText);t.finished.connect(self.finished_work);t.start()
    def busy(self,on):
        self._busy=on
        for w in (self.own,self.logs,self.limit,self.start_at,self.include_code,self.lookup_button):w.setEnabled(not on)
        self.cancel_button.setEnabled(on);self.save_button.setEnabled(False)
        self.update_cooldown()
    def update_cooldown(self):
        remaining=max(0,math.ceil(self.cooldown_until-time.monotonic()))
        self.lookup_button.setText(f'取得・確認（あと{remaining}秒）' if remaining else '取得・確認')
        self.lookup_button.setEnabled(not self._busy and self.thread is None and remaining==0)
        if not remaining:self.cooldown_timer.stop()
    def finished_work(self):
        self.thread.deleteLater();self.thread=None
        self.cooldown_until=time.monotonic()+30;self.cooldown_timer.start();self.busy(False);self.save_button.setEnabled(bool(self.selected_rows()))
        if self.rows:
            stamp=batch.minute_key(self.rows[-1].qso)
            if QMessageBox.question(self,'次回の開始日時',f'開始日時を、今回最後に処理した交信の日時（{stamp} JST）に変更しますか？\n同じ分の交信を飛ばさないよう、この分を含めて再開します。',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)==QMessageBox.StandardButton.Yes:self.start_at.setText(stamp)
    def eventFilter(self,obj,event):
        if hasattr(self,'table') and obj is self.table.viewport() and event.type()==QEvent.Type.Resize:
            spare=self.table.viewport().width()-sum(self.table.columnWidth(c) for c in range(10) if c!=8)
            self.table.setColumnWidth(8,max(260,spare))
        return super().eventFilter(obj,event)
    def selected_rows(self):return [c for c in self.rows if c.after is not None and c.selected]
    def sync_checks(self):
        self.table.blockSignals(True)
        try:
            chosen={c.key for c in self.rows if c.after is not None and c.selected}
            for n,c in enumerate(self.rows):
                item=self.table.item(n,0)
                if item is None:continue
                flags=Qt.ItemFlag.ItemIsSelectable
                if c.after is not None:
                    flags|=Qt.ItemFlag.ItemIsUserCheckable
                    if c.selected or c.key not in chosen:flags|=Qt.ItemFlag.ItemIsEnabled
                item.setFlags(flags);item.setCheckState(Qt.CheckState.Checked if c.after is not None and c.selected else Qt.CheckState.Unchecked)
        finally:self.table.blockSignals(False)
        self.save_button.setEnabled(self.thread is None and bool(self.selected_rows()))
    def selection_changed(self,item):
        if item.column()!=0 or item.row()>=len(self.rows):return
        c=self.rows[item.row()];checked=item.checkState()==Qt.CheckState.Checked
        if c.after is not None:
            c.selected=checked and not any(other is not c and other.key==c.key and other.after is not None and other.selected for other in self.rows)
        self.sync_checks()
    def render(self,rows,status):
        self.rows=rows;self.table.blockSignals(True);self.table.setRowCount(len(rows))
        try:
            for n,c in enumerate(rows):
                self.table.setItem(n,0,QTableWidgetItem(''))
                q=c.after or c.qso
                dates=(c.license_start or '未取得',c.license_end or '未取得')
                for col,value in enumerate((q.date,q.time,q.call,q.his_qth,q.code,*dates,c.note,c.path.name),1):
                    item=QTableWidgetItem(str(value));item.setToolTip(str(value));self.table.setItem(n,col,item)
        finally:self.table.blockSignals(False)
        self.sync_checks()
        self.status.setText(f'確認 {len({c.key for c in rows})}交信／候補 {len(rows)}行／補完可能 {len({c.key for c in rows if c.after is not None})}交信。'+status)
    def save(self):
        if self.thread:return
        rows=self.selected_rows()
        if not rows:return
        if QMessageBox.question(self,'HIS QTH作成',f'{len(rows)}件を補完します。更新前のバックアップを保存します。実行しますか？')!=QMessageBox.StandardButton.Yes:return
        try:count,files=batch.commit(self.repo,rows)
        except Exception as e:self.status.setText(str(e));return
        self.saved=True;self.rows=[];self.table.setRowCount(0);self.save_button.setEnabled(False);self.status.setText(f'{count}交信／{files}ファイルを保存しました。時間を空けて次の取得を実行できます。')
    def cancel(self):
        if self.thread:self.thread.requestInterruption();self.status.setText('中止待ちです（通信待ちは最大15秒）。')
    def reject(self):
        if self.thread:self.cancel();return
        if any(c.after for c in self.rows) and QMessageBox.question(self,'未保存の取得結果','変更内容を保存せず閉じますか？')!=QMessageBox.StandardButton.Yes:return
        super().reject()
    def closeEvent(self,event):
        if self.thread:self.cancel();event.ignore();return
        if any(c.after for c in self.rows):
            if QMessageBox.question(self,'未保存の取得結果','変更内容を保存せず閉じますか？')!=QMessageBox.StandardButton.Yes:event.ignore();return
        super().closeEvent(event)
