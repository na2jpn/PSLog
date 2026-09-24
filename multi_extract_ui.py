from copy import deepcopy
from PySide6.QtWidgets import QVBoxLayout,QHBoxLayout,QTableWidget,QTableWidgetItem,QLabel,QAbstractItemView
from window_geometry import SafeDialog
from search_ui import button

SOURCES=['exchange','area','prefix','country','continent']
KINDS=['whole','digits','slice']
class ExtractionDialog(SafeDialog):
    def __init__(self,rules,parent=None):
        from contest_rule_ui import combo,spin
        super().__init__(parent);self.rules=deepcopy(rules);self.setWindowTitle('第一マルチの抽出ルール');self.resize(1000,600)
        v=QVBoxLayout(self);label=QLabel('上から最初に一致した規則を採用します。一致なし・必要情報なしは未確定。\n開始位置は0から。元の受信ナンバーは変更しません。');label.setWordWrap(True);v.addWidget(label)
        self.table=QTableWidget(0,5);self.table.setHorizontalHeaderLabels(['条件','抽出元','方法','開始位置','文字数']);self.table.setColumnWidth(0,330);self.table.setSelectionBehavior(QAbstractItemView.SelectRows);self.table.setEditTriggers(QAbstractItemView.NoEditTriggers);v.addWidget(self.table,1)
        h=QHBoxLayout()
        for label,cb in [('追加',self.add),('条件を編集',self.edit),('削除',self.remove),('上へ',lambda:self.move(-1)),('下へ',lambda:self.move(1))]:h.addWidget(button(label,cb))
        v.addLayout(h);h=QHBoxLayout();h.addStretch();h.addWidget(button('反映',self.apply));h.addWidget(button('キャンセル',self.reject));v.addLayout(h);self.draw()
    def sync(self):
        for i,r in enumerate(self.rules):
            r.update(source=SOURCES[self.table.cellWidget(i,1).currentIndex()],kind=KINDS[self.table.cellWidget(i,2).currentIndex()],start=self.table.cellWidget(i,3).value(),length=self.table.cellWidget(i,4).value())
    def draw(self):
        from contest_rule_ui import combo,spin,describe
        self.table.setRowCount(len(self.rules))
        for i,r in enumerate(self.rules):
            self.table.setItem(i,0,QTableWidgetItem(describe(r['when'])))
            source=combo(['受信ナンバー','国内地域（作業値）','大会プリフィックス（作業値）','国・地域名','大陸']);source.setCurrentIndex(SOURCES.index(r['source']))
            kind=combo(['全体','単一の数字群','位置と文字数']);kind.setCurrentIndex(KINDS.index(r['kind']))
            for col,w in enumerate((source,kind,spin(r['start']),spin(r['length'])),1):self.table.setCellWidget(i,col,w)
            self.table.cellWidget(i,4).setMinimum(1)
    def add(self):
        self.sync();self.rules.append(dict(when={'all':[]},source='exchange',kind='whole',start=0,length=2));self.draw()
    def edit(self):
        from contest_rule_ui import ConditionDialog
        i=self.table.currentRow()
        if i<0:return
        self.sync();d=ConditionDialog(self.rules[i]['when'],self)
        if d.exec()==d.Accepted:self.rules[i]['when']=d.result_value;self.draw()
    def remove(self):
        i=self.table.currentRow()
        if i>=0:self.sync();self.rules.pop(i);self.draw()
    def move(self,delta):
        i=self.table.currentRow();j=i+delta
        if 0<=i<len(self.rules) and 0<=j<len(self.rules):self.sync();self.rules[i],self.rules[j]=self.rules[j],self.rules[i];self.draw();self.table.selectRow(j)
    def apply(self):self.sync();self.accept()
