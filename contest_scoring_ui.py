"""Visual editing for schema-2 multiplier sets and final addition."""
from copy import deepcopy
from PySide6.QtWidgets import QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,QTableWidget,QPushButton,QCheckBox
from window_geometry import SafeDialog
from search_ui import button
from contest_scoring_v2 import SOURCES,validate_scoring

class ScoringDialog(SafeDialog):
    def __init__(self,value,parent=None):
        from contest_rule_ui import spin
        super().__init__(parent);self.value=deepcopy(value);self.setWindowTitle('拡張採点 — マルチ集合と最終加算');self.resize(1150,650)
        box=QVBoxLayout(self);text=QLabel('対象交信について、条件に合うマルチを独立に数えて合算します。交信点が0でもマルチ条件に合えば加算します。最終加算点は第二マルチを掛けた後に加算します。');text.setWordWrap(True);box.addWidget(text)
        row=QHBoxLayout();row.addWidget(button('交信の対象条件…',self.edit_eligible));row.addWidget(QLabel('最終加算点'));self.bonus=spin(value['bonus'],True);row.addWidget(self.bonus);box.addLayout(row)
        self.table=QTableWidget(0,7);self.table.setHorizontalHeaderLabels(['識別子','抽出元','抽出方法','開始位置','文字数','バンド別','対象条件']);box.addWidget(self.table,1)
        row=QHBoxLayout();row.addWidget(button('マルチ追加',self.add));row.addWidget(button('選択行削除',self.remove));box.addLayout(row)
        self.status=QLabel();self.status.setWordWrap(True);box.addWidget(self.status);row=QHBoxLayout();row.addStretch();row.addWidget(button('反映',self.apply));row.addWidget(button('キャンセル',self.reject));box.addLayout(row)
        for m in value['multipliers']:self.add_row(m)
    def add_row(self,m):
        from contest_rule_ui import combo,spin
        i=self.table.rowCount();self.table.insertRow(i)
        ident=QLineEdit(m['id']);src=combo(['受信ナンバー','地域','プリフィックス','国・地域','大陸']);src.setCurrentIndex(SOURCES.index(m['source']))
        kind=combo(['全体','単一数字群','位置と文字数']);kind.setCurrentIndex(['whole','digits','slice'].index(m['kind']))
        band=QCheckBox();band.setChecked(m['per_band']);cond=QPushButton('条件を編集…');cond.condition=deepcopy(m['when']);cond.clicked.connect(lambda checked=False,w=cond:self.edit_condition(w))
        for col,w in enumerate((ident,src,kind,spin(m['start']),spin(m['length']),band,cond)):self.table.setCellWidget(i,col,w)
    def add(self):self.add_row(dict(id='multi'+str(self.table.rowCount()+1),source='exchange',kind='whole',start=0,length=2,per_band=True,when={'all':[]}))
    def remove(self):
        if self.table.currentRow()>=0:self.table.removeRow(self.table.currentRow())
    def edit_condition(self,w):
        from contest_rule_ui import ConditionDialog
        d=ConditionDialog(w.condition,self)
        if d.exec()==d.Accepted:w.condition=d.result_value
    def edit_eligible(self):
        from contest_rule_ui import ConditionDialog
        d=ConditionDialog(self.value['eligible'],self)
        if d.exec()==d.Accepted:self.value['eligible']=d.result_value
    def apply(self):
        try:
            ms=[]
            for i in range(self.table.rowCount()):
                w=[self.table.cellWidget(i,c) for c in range(7)]
                ms.append(dict(id=w[0].text().strip(),source=SOURCES[w[1].currentIndex()],kind=['whole','digits','slice'][w[2].currentIndex()],start=w[3].value(),length=w[4].value(),per_band=w[5].isChecked(),when=deepcopy(w[6].condition)))
            value=dict(eligible=deepcopy(self.value['eligible']),multipliers=ms,bonus=self.bonus.value());validate_scoring(value);self.value=value;self.accept()
        except ValueError as e:self.status.setText(str(e))
