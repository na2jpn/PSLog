"""User-confirmed domestic area hints; never infer an exchange from a callsign."""
import re
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout,QHBoxLayout,QLabel,QTableWidget,QTableWidgetItem,QAbstractItemView
from window_geometry import SafeDialog
from search_ui import button
from contest_country_ui import CountryDialog
from locations import load


def area_hint(data,code):
    match=re.fullmatch(r'(?:(JCC|JCG)\s+)?([0-9]+[A-Z]?)',code.strip().upper())
    if not match:return None
    kind,value=match.groups()
    found=[r for r in data['rows'] if (not kind or r['kind']==kind) and value in (r['code'],r['source_code'])]
    areas={r['code'][:2] for r in found}
    if len(areas)!=1:return None
    area=areas.pop()
    return {'area':area,'matched':code.strip(),'names':'／'.join(dict.fromkeys(r['name'] for r in found))}


class AreaDialog(CountryDialog):
    def __init__(self,root,selection,parent=None):
        SafeDialog.__init__(self,parent)
        db=load(root);self.rows=[(r,area_hint(db,r[1].code)) for r in selection.rows]
        self.selected=set();self.page=0;self.loading=False
        self.setWindowTitle('JCC/JCGから都道府県コードを補助入力');self.resize(900,580)
        v=QVBoxLayout(self)
        note=QLabel('所在地DBに一致したJCC/JCGの先頭2桁を候補にします。交信当時の所在地と大会規約を確認してください。\n選択した交信の空欄の「地域」だけに反映します。交換ナンバー・元ログは変更しません。')
        note.setWordWrap(True);v.addWidget(note)
        self.table=QTableWidget(0,5);self.table.setHorizontalHeaderLabels(['反映','相手コール','元のJCC/JCG','県コード候補','DB所在地']);v.addWidget(self.table,1)
        for i,w in enumerate((55,140,140,100,360)):self.table.setColumnWidth(i,w)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers);self.table.itemChanged.connect(self.changed)
        h=QHBoxLayout();self.prev=button('前の100件',lambda:self.move(-1));self.next=button('次の100件',lambda:self.move(1));self.count=QLabel();h.addWidget(self.prev);h.addWidget(self.count);h.addWidget(self.next);v.addLayout(h)
        h=QHBoxLayout();h.addWidget(button('このページの候補を選択',self.select_page));h.addWidget(button('選択解除',self.clear));h.addStretch();h.addWidget(button('選択した候補を反映',self.accept));h.addWidget(button('キャンセル',self.reject));v.addLayout(h);self.draw()

    def draw(self):
        self.loading=True;rows=self.rows[self.page*100:(self.page+1)*100];self.table.setRowCount(len(rows))
        for n,(source,hint) in enumerate(rows):
            values=['',source[1].call,source[1].code,hint['area'] if hint else '',hint['names'] if hint else '候補なし・必要な場合は地域を手入力']
            for col,value in enumerate(values):
                item=QTableWidgetItem(value);item.setToolTip(value)
                if col==0:
                    item.setFlags(Qt.ItemIsEnabled|Qt.ItemIsUserCheckable if hint else Qt.NoItemFlags)
                    item.setCheckState(Qt.Checked if self.page*100+n in self.selected else Qt.Unchecked)
                self.table.setItem(n,col,item)
        self.prev.setEnabled(self.page>0);self.next.setEnabled((self.page+1)*100<len(self.rows));self.label();self.loading=False

    def apply_to(self,draft):
        for i in sorted(self.selected):
            row,hint=self.rows[i]
            if not hint:continue
            d=draft.setdefault((str(row[2]),row[3]),{})
            if not d.get('area','').strip():d['area']=hint['area']
