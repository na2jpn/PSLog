from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout,QHBoxLayout,QLineEdit,QLabel,QTableWidget,QTableWidgetItem,QAbstractItemView
from window_geometry import SafeDialog
from search_ui import button

class ClubDialog(SafeDialog):
    def __init__(self,master,query='',parent=None):
        super().__init__(parent);self.master=master;self.result_value=None;self.rows=[];self.page=0;self.setWindowTitle('登録クラブを検索');self.resize(900,600);v=QVBoxLayout(self);self.search=QLineEdit(query);self.search.setPlaceholderText('クラブ番号・名称で検索');v.addWidget(self.search);self.table=QTableWidget(0,2);self.table.setHorizontalHeaderLabels(['クラブ番号','クラブ名']);self.table.setColumnWidth(0,160);self.table.setColumnWidth(1,580);self.table.setSelectionBehavior(QAbstractItemView.SelectRows);self.table.setSelectionMode(QAbstractItemView.SingleSelection);self.table.setEditTriggers(QAbstractItemView.NoEditTriggers);v.addWidget(self.table,1);row=QHBoxLayout();self.prev=button('前へ',lambda:self.move(-1));self.next=button('次へ',lambda:self.move(1));self.count=QLabel();row.addWidget(self.prev);row.addWidget(self.count);row.addWidget(self.next);v.addLayout(row);self.info=QLabel(master.label());self.info.setWordWrap(True);v.addWidget(self.info);row=QHBoxLayout();row.addStretch();self.pick=button('このクラブを選択',self.apply);row.addWidget(self.pick);row.addWidget(button('キャンセル',self.reject));v.addLayout(row);self.search.textChanged.connect(self.find);self.table.itemSelectionChanged.connect(self.enabled);self.table.itemDoubleClicked.connect(self.apply);self.find()
    def find(self,*args):self.rows=self.master.search(self.search.text());self.page=0;self.draw()
    def draw(self):
        self.table.setRowCount(0)
        for i,r in enumerate(self.rows[self.page*100:(self.page+1)*100]):
            self.table.insertRow(i)
            for j,k in enumerate(('number','name')):self.table.setItem(i,j,QTableWidgetItem(r[k]))
        pages=max(1,(len(self.rows)+99)//100);self.count.setText(f'{len(self.rows):,}件・{self.page+1}/{pages}ページ（100件ずつ）');self.prev.setEnabled(self.page>0);self.next.setEnabled(self.page+1<pages);self.enabled()
    def move(self,d):self.page+=d;self.draw()
    def enabled(self):self.pick.setEnabled(self.table.currentRow()>=0)
    def apply(self,*args):
        i=self.table.currentRow()
        if i>=0:self.result_value=self.rows[self.page*100+i];self.accept()
