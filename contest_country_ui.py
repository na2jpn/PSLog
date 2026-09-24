"""Explicit selection of reference hints for contest working data only."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout,QHBoxLayout,QLabel,QTableWidget,QTableWidgetItem,QAbstractItemView
from window_geometry import SafeDialog
from search_ui import button
from countries import load

class CountryDialog(SafeDialog):
    def __init__(self,root,selection,parent=None):
        super().__init__(parent);db=load(root);self.rows=[(r,db.lookup(r[1].call)) for r in selection.rows];self.selected=set();self.page=0;self.loading=False
        self.setWindowTitle('国・地域と大陸の参照候補');self.resize(900,580)
        v=QVBoxLayout(self);note=QLabel('参照版: '+db.version+'。交信当時の運用地を確認してチェックしてください。\n空欄の作業項目だけに反映します。国内の県区分・大会用プリフィックスは変更しません。');note.setWordWrap(True);v.addWidget(note)
        self.table=QTableWidget(0,5);self.table.setHorizontalHeaderLabels(['反映','相手コール','国・地域候補','大陸','照合情報']);v.addWidget(self.table,1)
        for i,w in enumerate((55,150,230,70,270)):self.table.setColumnWidth(i,w)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers);self.table.itemChanged.connect(self.changed)
        h=QHBoxLayout();self.prev=button('前の100件',lambda:self.move(-1));self.next=button('次の100件',lambda:self.move(1));self.count=QLabel();h.addWidget(self.prev);h.addWidget(self.count);h.addWidget(self.next);v.addLayout(h)
        h=QHBoxLayout();h.addWidget(button('このページの候補を選択',self.select_page));h.addWidget(button('選択解除',self.clear));h.addStretch();h.addWidget(button('選択した候補を反映',self.accept));h.addWidget(button('キャンセル',self.reject));v.addLayout(h);self.draw()
    def changed(self,item):
        if self.loading or item.column()!=0:return
        i=self.page*100+item.row()
        if item.checkState()==Qt.Checked:self.selected.add(i)
        else:self.selected.discard(i)
        self.label()
    def label(self):self.count.setText(f'{self.page+1}/{max(1,(len(self.rows)+99)//100)}ページ / 選択 {len(self.selected)}件')
    def move(self,delta):self.page=max(0,min(max(0,(len(self.rows)-1)//100),self.page+delta));self.draw()
    def select_page(self):
        self.selected.update(i for i in range(self.page*100,min(len(self.rows),(self.page+1)*100)) if self.rows[i][1]);self.draw()
    def clear(self):self.selected.clear();self.draw()
    def draw(self):
        self.loading=True;rows=self.rows[self.page*100:(self.page+1)*100];self.table.setRowCount(len(rows))
        for n,(source,hint) in enumerate(rows):
            for col,text in enumerate(['',source[1].call,hint['country'] if hint else '要確認・自動判定なし',hint['continent'] if hint else '',hint['matched'] if hint else '運用地を手入力してください']):
                item=QTableWidgetItem(text)
                if col==0:
                    item.setFlags(Qt.ItemIsEnabled|Qt.ItemIsUserCheckable if hint else Qt.NoItemFlags);item.setCheckState(Qt.Checked if self.page*100+n in self.selected else Qt.Unchecked)
                self.table.setItem(n,col,item)
        self.prev.setEnabled(self.page>0);self.next.setEnabled((self.page+1)*100<len(self.rows));self.label();self.loading=False
    def apply_to(self,draft):
        for i in sorted(self.selected):
            row,hint=self.rows[i];d=draft.setdefault((str(row[2]),row[3]),{})
            if any(d.get(f) and d[f].casefold()!=hint[f].casefold() for f in ('country','continent')):continue
            for field in ('country','continent'):
                if not d.get(field):d[field]=hint[field]
