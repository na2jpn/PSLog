"""Explicit-load DXCC status, QSO detail, and existing search handoff."""
from PySide6.QtCore import QThread,Signal
from PySide6.QtWidgets import QVBoxLayout,QHBoxLayout,QLabel,QComboBox,QPushButton,QTableWidget,QTableWidgetItem,QAbstractItemView,QMessageBox,QHeaderView,QCheckBox
from window_geometry import SafeDialog
from window_tint import apply_window_tint
from logbook_sources import amateur_station_calls
from storage import VERSION,StorageError
from award_applications import Applications
from dxcc_check import Entity,Result
from jccjcg_award_check import award_band,BAND_ORDER
from dxcc_check import aggregate

class AggregateThread(QThread):
    completed=Signal(object);failed=Signal(str)
    def __init__(self,repo,own,parent):super().__init__(parent);self.repo=repo;self.own=own
    def run(self):
        try:self.completed.emit(aggregate(self.repo,self.own,self.isInterruptionRequested))
        except Exception as e:self.failed.emit(str(e))

class DxccCheckDialog(SafeDialog):
    def __init__(self,repo,parent=None):
        super().__init__(parent);self.repo=repo;self.result=None;self.thread=None;self.applications=Applications(repo.root);self.application_entries={}
        self.setWindowTitle(f'PSLog Ver{VERSION} — DXCCチェック');self.resize(1080,740);apply_window_tint(self,'edit')
        v=QVBoxLayout(self);row=QHBoxLayout();row.addWidget(QLabel('対象自局コール'));self.own=QComboBox();self.own.addItem('選択してください','');
        for call in amateur_station_calls(repo):self.own.addItem(call,call)
        row.addWidget(self.own);self.run_button=QPushButton('表示');self.run_button.clicked.connect(self.run);row.addWidget(self.run_button);self.band=QComboBox();self.band.addItem('全バンド','*');self.band.currentIndexChanged.connect(self.refresh);row.addWidget(self.band);row.addStretch();v.addLayout(row)
        note=QLabel('チェックはアワード申請済を表します（QSL請求済ではありません）。全バンド・各バンドは独立して保存します。');note.setWordWrap(True);v.addWidget(note)
        self.summary=QLabel('交信済エンティティ数（未QSLを含む）：—　／　QSL済エンティティ数：—　／　申請済エンティティ数：—');self.summary.setWordWrap(True);v.addWidget(self.summary)
        self.status=QLabel('自局を選んで「表示」を押してください。/1・/P等の自局ログもまとめて集計します。');self.status.setWordWrap(True);v.addWidget(self.status)
        self.table=QTableWidget(0,6);self.table.setHorizontalHeaderLabels(['DXCC名','申請済','未QSL交信数','QSL済交信数','計','操作']);self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers);self.table.setAlternatingRowColors(True);v.addWidget(self.table,1)
        self.own.currentIndexChanged.connect(self.invalidate)
        self.unresolved=QPushButton('要確認の交信');self.unresolved.setEnabled(False);self.unresolved.clicked.connect(self.open_unresolved);v.addWidget(self.unresolved)
        self.close_button=QPushButton('閉じる');self.close_button.clicked.connect(self.reject);v.addWidget(self.close_button)
    def invalidate(self):
        self.result=None;self.table.setRowCount(0);self.unresolved.setEnabled(False);self.summary.setText('交信済エンティティ数（未QSLを含む）：—　／　QSL済エンティティ数：—　／　申請済エンティティ数：—')
    def run(self):
        if self.thread or not self.own.currentData():return
        self.invalidate();self.status.setText('集計中…');self.run_button.setEnabled(False);self.own.setEnabled(False);self.band.setEnabled(False)
        t=AggregateThread(self.repo,self.own.currentData(),self);self.thread=t;t.completed.connect(self.render);t.failed.connect(self.status.setText);t.finished.connect(self.finished_work);t.start()
    def finished_work(self):
        self.thread.deleteLater();self.thread=None;self.run_button.setEnabled(True);self.own.setEnabled(True);self.band.setEnabled(True)
    def render(self,result):
        self.result=result
        try:self.application_entries=self.applications.entries()
        except (StorageError,OSError) as e:self.invalidate();self.status.setText(str(e));return
        self.band.blockSignals(True);self.band.clear();self.band.addItem('全バンド','*')
        bands={award_band(h.qso) for e in result.entities for h in e.hits}
        for band in sorted(bands,key=lambda b:(BAND_ORDER.index(b) if b in BAND_ORDER else 999,b)):self.band.addItem(band,band)
        self.band.blockSignals(False);self.refresh()
    def refresh(self):
        if self.result is None:return
        band=self.band.currentData() or '*';original=self.result
        entities=[]
        for e in original.entities:
            hits=[h for h in e.hits if band=='*' or award_band(h.qso)==band]
            if hits:entities.append(Entity(e.ident,e.name,e.deleted,hits,e.names))
        result=Result(entities,original.files,sum(len(e.hits) for e in entities),original.problems,original.unresolved)
        self.table.setRowCount(len(entities))
        deleted=sum(e.deleted for e in result.entities);cfm_deleted=sum(e.deleted and bool(e.confirmed) for e in result.entities)
        applied=sum(self.applications.checked(self.own.currentData(),'DXCC',e.ident,band,self.application_entries) for e in result.entities)
        self.summary.setText(f'交信済エンティティ数（未QSLを含む）：{result.worked}　／　QSL済エンティティ数：{result.confirmed}　／　申請済エンティティ数：{applied}　（うち削除済：{deleted}／{cfm_deleted}）')
        for n,e in enumerate(result.entities):
            label=e.name+('（削除済）' if e.deleted else '')
            if e.names!={e.name}:label+=' ／記録年代名：'+', '.join(sorted(e.names))
            for c,value in enumerate((label,e.unconfirmed,e.confirmed,len(e.hits))):
                self.table.setItem(n,c if c==0 else c+1,QTableWidgetItem(str(value)))
            check=QCheckBox();check.setChecked(self.applications.checked(self.own.currentData(),"DXCC",e.ident,band,self.application_entries));check.toggled.connect(lambda checked,entity=e,c=check:self.application_changed(entity,checked,c));self.table.setCellWidget(n,1,check)
            b=QPushButton('Open');b.clicked.connect(lambda _,entity=e:self.open_entity(entity));self.table.setCellWidget(n,5,b)
        self.table.resizeColumnsToContents();self.table.horizontalHeader().setStretchLastSection(False);self.table.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeMode.Stretch)
        self.status.setText(f'{result.files}ファイル・{result.qsos}交信。要確認 {len(result.unresolved)}件／読込問題 {len(result.problems)}件。QSL済はPSLogの受領記録による参考集計です。')
        self.status.setToolTip('\n'.join(result.problems[:100]));self.unresolved.setEnabled(bool(result.unresolved))
    def application_changed(self,entity,checked,check):
        try:
            self.applications.set(self.own.currentData(),'DXCC',entity.ident,self.band.currentData() or '*',checked)
            self.application_entries=self.applications.entries()
        except (StorageError,OSError,ValueError) as e:
            check.blockSignals(True);check.setChecked(not checked);check.blockSignals(False);QMessageBox.warning(self,'保存できません',str(e));return
        self.refresh()
    def open_entity(self,entity):self.open_hits(entity.name,[(h,'QSL済' if h.qso.confirmed else '未QSL') for h in entity.hits])
    def open_unresolved(self):
        if self.result:self.open_hits('要確認',self.result.unresolved)
    def open_hits(self,title,rows):
        d=SafeDialog(self);d.setWindowTitle(title+' — 交信一覧');d.resize(1100,640);v=QVBoxLayout(d);v.addWidget(QLabel('交信をクリックすると、対象コール・ログファイルを指定したログ検索を開きます。'))
        table=QTableWidget(len(rows),9);table.setHorizontalHeaderLabels(['DATE','TIME JST','相手コール','BAND','MODE','HIS QTH','状態','元ログ','行']);table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        for n,(h,state) in enumerate(rows):
            q=h.qso
            from search_ui import detail_text
            tooltip=detail_text(h)
            for c,value in enumerate((q.date,q.time,q.call,q.band,q.mode,q.his_qth,state,h.path.name,h.line)):
                item=QTableWidgetItem(str(value));item.setToolTip(tooltip);table.setItem(n,c,item)
        table.cellClicked.connect(lambda n,c:self.open_search(rows[n][0],d));table.resizeColumnsToContents();v.addWidget(table);close=QPushButton('閉じる');close.clicked.connect(d.accept);v.addWidget(close);d.exec()
    def open_search(self,hit,parent):
        from search_ui import SearchDialog
        d=SearchDialog(self.repo,hit.own,parent,filename=hit.path.name,exact_target=True);d.filters['call'].setText(hit.qso.call)
        d.run_search();d.logs_changed.connect(lambda:self.status.setText('ログが変更されました。「表示」で再集計してください。'));d.exec()
    def reject(self):
        if self.thread:self.thread.requestInterruption();self.status.setText('集計を停止しています。完了後に閉じてください。');return
        super().reject()
    def closeEvent(self,event):
        if self.thread:self.thread.requestInterruption();event.ignore();return
        super().closeEvent(event)
