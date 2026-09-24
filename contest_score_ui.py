"""Paged, read-only scoring evidence for every selected QSO."""
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QTableWidget,
    QTableWidgetItem,QAbstractItemView,QCheckBox,QLabel,QPushButton)

class ScoreView(QWidget):
    PAGE_SIZE=100
    def __init__(self,parent=None):
        super().__init__(parent)
        self.rows=[];self.indices=[];self.page=0
        layout=QVBoxLayout(self);layout.setContentsMargins(0,0,0,0)
        self.only_pending=QCheckBox('未確定の交信だけ表示');layout.addWidget(self.only_pending)
        self.table=QTableWidget(0,7)
        self.table.setHorizontalHeaderLabels(['対象内番号','日時 JST / 相手コール','BAND / MODE','得点','第一マルチ','マルチ判定','根拠・確認状態'])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        for i,width in enumerate((85,240,115,70,120,95,330)):self.table.setColumnWidth(i,width)
        layout.addWidget(self.table,1)
        row=QHBoxLayout();self.previous=QPushButton('前の100件');self.next=QPushButton('次の100件');self.count=QLabel()
        row.addWidget(self.previous);row.addWidget(self.count,1);row.addWidget(self.next);layout.addLayout(row)
        self.previous.clicked.connect(lambda:self.move(-1));self.next.clicked.connect(lambda:self.move(1))
        self.only_pending.toggled.connect(self.refilter);self.clear()
    def clear(self):
        self.rows=[];self.pending=set();self.refilter()
    def set_result(self,selection,result,draft):
        self.rows=list(zip(selection.rows,result.rows))
        self.pending={i for i,(source,_) in enumerate(self.rows)
                      if draft.get((str(source[2]),source[3]),{}).get('status')=='候補・要確認'}
        self.refilter()
    def row_values(self,index):
        source,value=self.rows[index];own,q,path,line=source
        pending=index in self.pending
        reason=value['reason']
        if pending:reason='抽出候補が未確認 / '+reason
        points='未確定' if pending or value['points'] is None else str(value['points'])
        multi=str(value['multi']) if value['multi'] is not None else '—'
        multi_judgement=str(value.get('multiplier_judgement') or '—')
        values=[str(index+1),q.date+' '+q.time+' / '+q.call,q.band+' / '+q.mode,
                points,multi,multi_judgement,reason]
        evidence=f'自局: {own}\n原本: {path}\n原本行: {line}\nRMKS: {q.remarks}\n{reason}'
        return values,evidence
    def refilter(self,*args):
        self.indices=([i for i,(_,value) in enumerate(self.rows) if i in self.pending or value['points'] is None]
                      if self.only_pending.isChecked() else range(len(self.rows)))
        self.page=0;self.draw()
    def move(self,delta):
        pages=max(1,(len(self.indices)+self.PAGE_SIZE-1)//self.PAGE_SIZE)
        self.page=max(0,min(pages-1,self.page+delta));self.draw()
    def draw(self):
        start=self.page*self.PAGE_SIZE;visible=self.indices[start:start+self.PAGE_SIZE]
        self.table.setRowCount(len(visible))
        for n,index in enumerate(visible):
            values,evidence=self.row_values(index)
            for col,value in enumerate(values):
                item=QTableWidgetItem(value);item.setToolTip(evidence+'\n'+value);self.table.setItem(n,col,item)
        pages=max(1,(len(self.indices)+self.PAGE_SIZE-1)//self.PAGE_SIZE)
        self.count.setText(f'{self.page+1}/{pages}ページ・表示対象 {len(self.indices):,}件 / 全 {len(self.rows):,}件')
        self.previous.setEnabled(self.page>0);self.next.setEnabled(self.page+1<pages)
        self.table.scrollToTop()
