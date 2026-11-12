"""No QSL list: fixed headers, no pages, direct BURO toggles."""
from pathlib import Path
from PySide6.QtCore import Qt,Signal
from PySide6.QtWidgets import (QVBoxLayout,QHBoxLayout,QLineEdit,QLabel,QPushButton,QComboBox,QCheckBox,QFileDialog,QTableWidget,QTableWidgetItem,QAbstractItemView,QHeaderView)
from window_geometry import SafeDialog
from storage import StorageError
from no_qsl import collect,toggle,has_buro

class NoQSLDialog(SafeDialog):
    logs_changed=Signal()
    def __init__(self,repo,parent=None):
        super().__init__(parent);self.repo=repo;self.paths=[];self.rows=[];self.loaded_filters=None;self.busy=False
        self.setWindowTitle('No QSLリスト');self.resize(1120,680)
        box=QVBoxLayout(self);files=QHBoxLayout();files.addWidget(QLabel('対象ログ'))
        self.files=QLineEdit();self.files.setReadOnly(True);self.files.setPlaceholderText('対象ログファイルを選択（複数可）');files.addWidget(self.files,1)
        choose=QPushButton('ファイル選択…');choose.clicked.connect(self.choose_files);files.addWidget(choose);box.addLayout(files)
        filters=QHBoxLayout();filters.addWidget(QLabel('月'));self.month=QComboBox();self.month.addItem('すべて',0)
        for n in range(1,13):self.month.addItem(str(n)+'月',n)
        filters.addWidget(self.month);filters.addWidget(QLabel('コールサイン'));self.call=QLineEdit();self.call.setPlaceholderText('空欄は全局・部分一致');filters.addWidget(self.call,1)
        self.exclude_buro=QCheckBox('BUROありを除外');filters.addWidget(self.exclude_buro);show=QPushButton('表示');show.clicked.connect(self.show_rows);filters.addWidget(show);box.addLayout(filters)
        note=QLabel('受領済み（BURO.R・hQSL.Rなど）は除外します。BURO列をクリックすると、元ログのRMKSへBUROを追加／削除します。〇：BUROあり、ー：BUROなし。');note.setWordWrap(True);box.addWidget(note)
        self.table=QTableWidget(0,9);self.table.setHorizontalHeaderLabels(['BURO','日付','時間','コールサイン','バンド','モード','HisRST（送信）','HisJCC/JCG','RMKS'])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers);self.table.setSelectionBehavior(QAbstractItemView.SelectRows);self.table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel);self.table.verticalHeader().hide()
        for n,w in enumerate([65,105,65,125,70,85,110,110]):self.table.setColumnWidth(n,w)
        self.table.setColumnWidth(8,280);self.table.horizontalHeader().setStretchLastSection(True);self.table.cellClicked.connect(self.clicked);box.addWidget(self.table,1)
        bottom=QHBoxLayout();self.status=QLabel('対象ログを選び、表示を押してください。');self.status.setWordWrap(True);bottom.addWidget(self.status,1);close=QPushButton('閉じる');close.clicked.connect(self.reject);bottom.addWidget(close);box.addLayout(bottom)
    def filters(self):return (tuple(self.paths),self.month.currentData(),self.call.text().strip(),self.exclude_buro.isChecked())
    def choose_files(self):
        paths,_=QFileDialog.getOpenFileNames(self,'対象ログファイルを選択',str(self.repo.book),'PSLogログ (*.txt)')
        if paths:self.set_files(paths)
    def set_files(self,paths):
        self.paths=list(dict.fromkeys(str(Path(p).resolve()) for p in paths));self.files.setText(' / '.join(Path(p).name for p in self.paths));self.files.setToolTip('\n'.join(self.paths));self.rows=[];self.loaded_filters=None;self.table.setRowCount(0);self.status.setText('対象ログを選択しました。表示を押してください。')
    def show_rows(self):
        try:
            rows=collect(self.repo,self.paths,self.month.currentData(),self.call.text(),self.exclude_buro.isChecked())
        except (ValueError,OSError,StorageError) as e:
            self.rows=[];self.loaded_filters=None;self.table.setRowCount(0);self.status.setText(str(e));return
        self.rows=rows;self.loaded_filters=self.filters();self.table.setUpdatesEnabled(False)
        try:
            self.table.setRowCount(len(rows))
            for i,row in enumerate(rows):
                q=row.qso;values=['〇' if has_buro(q.remarks) else 'ー',q.date,q.time,q.call,q.band,q.mode,q.sent,q.code,q.remarks]
                for col,value in enumerate(values):
                    item=QTableWidgetItem(str(value));item.setToolTip(str(row.path)+'\n行 '+str(row.line)+'\n'+str(value))
                    if col==0:item.setTextAlignment(Qt.AlignCenter);item.setToolTip('クリックでBUROを追加／削除\n'+str(row.path)+'\n行 '+str(row.line))
                    self.table.setItem(i,col,item)
        finally:self.table.setUpdatesEnabled(True)
        self.status.setText(f'{len(self.paths)}ファイル・対象 {len(rows):,}件')
    def clicked(self,index,col):
        if col!=0 or self.busy or not 0<=index<len(self.rows):return
        if self.loaded_filters!=self.filters():self.status.setText('絞込み条件を変更しています。表示を押してから操作してください。');return
        self.busy=True;scroll=self.table.verticalScrollBar().value()
        try:
            on=toggle(self.repo,self.rows[index]);self.logs_changed.emit();self.show_rows();self.table.verticalScrollBar().setValue(scroll);self.status.setText(self.status.text()+(' ／ BUROを追加しました' if on else ' ／ BUROを削除しました'))
        except (ValueError,OSError,StorageError) as e:
            self.loaded_filters=None;self.status.setText(str(e)+'\n表示を押してログを読み直してください。')
        finally:self.busy=False
