"""Free-radio search/edit UI.  It deliberately exposes no amateur QSL/export workflow."""
from dataclasses import asdict
from PySide6.QtCore import Qt,QTimer
from PySide6.QtWidgets import (QVBoxLayout,QHBoxLayout,QGridLayout,QLabel,QLineEdit,QComboBox,QPushButton,
    QTableWidget,QTableWidgetItem,QHeaderView,QAbstractItemView,QTextEdit,QMessageBox,QDialog,QFormLayout,QScrollArea,QWidget)
from window_geometry import SafeDialog
from storage import StorageError,VERSION
from free_radio import FREE_TYPES,FreeQSO,free_station_calls,free_file_identity,radio_values
from free_search import FreeCriteria,free_search
from input_normalization import time_text

SELECT='選択してください'
ALL='すべて'

class FreeEditDialog(SafeDialog):
    def __init__(self,hit,parent=None):
        super().__init__(parent);self.hit=hit;self.saved=False;self.deleted=False
        ident=free_file_identity(hit.path);self.kind=ident[2] if ident else '';self.model=ident[3] if ident else ''
        self.setWindowTitle(f'PSLog Ver{VERSION} — フリラ交信を編集');self.resize(760,650)
        outer=QVBoxLayout(self);outer.addWidget(QLabel(f'種類: {self.kind}　機種: {self.model}　自局: {hit.own}'))
        scroll=QScrollArea();scroll.setWidgetResizable(True);body=QWidget();form=QFormLayout(body);scroll.setWidget(body);outer.addWidget(scroll,1)
        q=hit.qso;self.inputs={}
        for key,label in [('date','DATE'),('time','TIME（JST）'),('call','HIS CALLSIGN'),('sent','RSTs（送信）'),('received','RSTr（受信）'),('his_qth','HIS QTH'),('code','JCC / JCG'),('my_qth','MY QTH'),('remarks','RMKS')]:
            e=QLineEdit(getattr(q,key));self.inputs[key]=e;form.addRow(label,e)
        band,mode=radio_values(self.kind)
        info=QLabel(f'BAND: {band}　MODE: {mode}（種類から自動設定）');form.addRow('種類情報',info)
        self.status=QLabel();self.status.setWordWrap(True);outer.addWidget(self.status)
        row=QHBoxLayout();delete=QPushButton('この交信を削除');delete.clicked.connect(self.delete);row.addWidget(delete);row.addStretch()
        save=QPushButton('変更を保存');save.clicked.connect(self.save);cancel=QPushButton('キャンセル');cancel.clicked.connect(self.reject);row.addWidget(save);row.addWidget(cancel);outer.addLayout(row)
    def _qso(self):
        band,mode=radio_values(self.kind)
        return FreeQSO(self.inputs['date'].text(),self.inputs['time'].text(),band,mode,self.inputs['call'].text(),self.inputs['sent'].text(),self.inputs['received'].text(),self.inputs['his_qth'].text(),self.inputs['my_qth'].text(),self.inputs['remarks'].text(),self.inputs['code'].text())
    def save(self):
        try:q=self._qso();q.validate();self.hit.apply(q)
        except (ValueError,StorageError,OSError) as e:self.status.setText(str(e));return
        self.saved=True;self.accept()
    def delete(self):
        q=self.hit.qso
        if QMessageBox.question(self,'交信の削除確認',f'{q.date} {q.time} JST　{q.call}\nこの交信を削除しますか？',QMessageBox.Yes|QMessageBox.No,QMessageBox.No)!=QMessageBox.Yes:return
        try:self.hit.apply()
        except (StorageError,OSError) as e:self.status.setText(str(e));return
        self.saved=True;self.deleted=True;self.accept()

class FreeSearchDialog(SafeDialog):
    def __init__(self,repo,own='',parent=None,autorun=False):
        super().__init__(parent);self.repo=repo;self.hits=[]
        self.setWindowTitle(f'PSLog Ver{VERSION} — フリラログ検索・編集');self.resize(1220,760)
        outer=QVBoxLayout(self);form=QGridLayout();outer.addLayout(form)
        self.own=QComboBox();self.own.addItem(SELECT);self.own.addItems(free_station_calls(repo))
        if own and self.own.findText(own)>=0:self.own.setCurrentText(own)
        self.kind=QComboBox();self.kind.addItem(ALL);self.kind.addItems(FREE_TYPES)
        self.call=QLineEdit();self.remarks=QLineEdit();self.his_qth=QLineEdit();self.my_qth=QLineEdit();self.code=QLineEdit();self.start=QLineEdit();self.end=QLineEdit()
        form.addWidget(QLabel('対象自局'),0,0);form.addWidget(self.own,0,1);form.addWidget(QLabel('種類'),0,2);form.addWidget(self.kind,0,3);form.addWidget(QLabel('HIS CALLSIGN'),0,4);form.addWidget(self.call,0,5)
        form.addWidget(QLabel('RMKS'),1,0);form.addWidget(self.remarks,1,1,1,5)
        form.addWidget(QLabel('HIS QTH'),2,0);form.addWidget(self.his_qth,2,1);form.addWidget(QLabel('JCC/JCG'),2,2);form.addWidget(self.code,2,3);form.addWidget(QLabel('MY QTH'),2,4);form.addWidget(self.my_qth,2,5)
        form.addWidget(QLabel('開始日時 JST'),3,0);form.addWidget(self.start,3,1);form.addWidget(QLabel('終了日時 JST'),3,2);form.addWidget(self.end,3,3)
        action=QHBoxLayout();action.addStretch();self.search_button=QPushButton('検索 / 再読み込み');self.search_button.clicked.connect(self.run_search);action.addWidget(self.search_button);outer.addLayout(action)
        self.status=QLabel('対象自局を選択して検索してください。種類「すべて」はCB/LCR/DCR等を横断します。');self.status.setWordWrap(True);outer.addWidget(self.status)
        self.table=QTableWidget(0,10);self.table.setHorizontalHeaderLabels(['HIS CALLSIGN','DATE','TIME JST','種類','RSTs','RSTr','HIS QTH','MY QTH','RMKS','JCC/JCG'])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows);self.table.setSelectionMode(QAbstractItemView.SingleSelection);self.table.setEditTriggers(QAbstractItemView.NoEditTriggers);self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive);self.table.setColumnWidth(0,145);self.table.setColumnWidth(1,95);self.table.setColumnWidth(2,75);self.table.setColumnWidth(3,75);self.table.setColumnWidth(8,220);outer.addWidget(self.table,1)
        self.table.itemDoubleClicked.connect(lambda *_:self.edit_selected())
        bottom=QHBoxLayout();self.edit_button=QPushButton('交信を編集…');self.edit_button.clicked.connect(self.edit_selected);bottom.addWidget(self.edit_button);bottom.addStretch();close=QPushButton('閉じる');close.clicked.connect(self.reject);bottom.addWidget(close);outer.addLayout(bottom)
        self.table.itemSelectionChanged.connect(self._selection);self._selection()
        if autorun and own:QTimer.singleShot(0,self.run_search)
    def _selection(self):self.edit_button.setEnabled(self.table.currentRow()>=0)
    def run_search(self):
        if self.own.currentText()==SELECT:
            self.status.setText('対象自局を選択してください。');return
        try:
            criteria=FreeCriteria(self.own.currentText(),'' if self.kind.currentText()==ALL else self.kind.currentText(),self.call.text(),self.remarks.text(),self.his_qth.text(),self.my_qth.text(),self.code.text(),self.start.text().replace('-','').replace(':','').replace(' ',''),self.end.text().replace('-','').replace(':','').replace(' ',''))
            result=free_search(self.repo,criteria)
        except (ValueError,StorageError,OSError) as e:self.status.setText(str(e));return
        self.hits=list(result.hits);self.table.setRowCount(len(self.hits))
        for r,h in enumerate(self.hits):
            q=h.qso;values=[q.call,q.date,q.time,getattr(h,'free_kind',''),q.sent,q.received,q.his_qth,q.my_qth,q.remarks,q.code]
            for c,v in enumerate(values):self.table.setItem(r,c,QTableWidgetItem(v))
        self.status.setText(f'{len(self.hits):,}件 / 対象{result.files}ファイル　要確認{len(result.problems)}件。')
        self._selection()
    def edit_selected(self):
        row=self.table.currentRow()
        if not 0<=row<len(self.hits):return
        dialog=FreeEditDialog(self.hits[row],self);dialog.exec()
        if dialog.saved:self.run_search()
