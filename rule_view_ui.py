"""Read-only rule/condition viewers for contests, QSO parties and awards."""
from __future__ import annotations

import html
from pathlib import Path
from PySide6.QtCore import Qt,QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QGridLayout,QLabel,QLineEdit,QComboBox,
    QScrollArea,QGroupBox,QFrame,QPushButton,QMessageBox,QSizePolicy)
from window_geometry import SafeDialog
from window_tint import apply_window_tint
from storage import VERSION,StorageError
from contest_rules import RuleStore,rule_label
from party import PARTIES
from award_registry import AWARDS
from rule_view_data import contest_sections,party_sections,award_sections,is_contest_rule


class _InfoViewer(SafeDialog):
    def __init__(self,title,parent=None,tint='contest'):
        super().__init__(parent);self.setWindowTitle(f'{title} — PSLog Ver{VERSION}');self.resize(1050,780);apply_window_tint(self,tint)
        self.outer=QVBoxLayout(self);self.search=QLineEdit();self.search.setPlaceholderText('名称で検索');self.selector=QComboBox()
        head=QGridLayout();head.addWidget(QLabel('検索'),0,0);head.addWidget(self.search,0,1);head.addWidget(QLabel('選択'),1,0);head.addWidget(self.selector,1,1);head.setColumnStretch(1,1);self.outer.addLayout(head)
        self.status=QLabel();self.status.setWordWrap(True);self.outer.addWidget(self.status)
        self.scroll=QScrollArea();self.scroll.setWidgetResizable(True);self.scroll.setFrameShape(QFrame.Shape.StyledPanel);self.outer.addWidget(self.scroll,1)
        self.body=QWidget();self.body_layout=QVBoxLayout(self.body);self.body_layout.setContentsMargins(10,10,10,10);self.body_layout.setSpacing(9);self.scroll.setWidget(self.body)
        close=QHBoxLayout();close.addStretch();b=QPushButton('閉じる');b.setAutoDefault(False);b.setDefault(False);b.clicked.connect(self.accept);close.addWidget(b);self.outer.addLayout(close)
    def keyPressEvent(self,event):
        if event.key() in (Qt.Key.Key_Return,Qt.Key.Key_Enter):
            event.accept();return
        super().keyPressEvent(event)

    def _open_official_url(self,url):
        qurl=QUrl(str(url))
        if qurl.scheme() not in ('http','https') or not qurl.isValid():
            QMessageBox.warning(self,'公式規約URL','公式規約URLが正しくありません。');return
        if not QDesktopServices.openUrl(qurl):
            QMessageBox.warning(self,'公式規約URL','既定のブラウザで公式規約を開けませんでした。')

    def clear_body(self):
        while self.body_layout.count():
            item=self.body_layout.takeAt(0);w=item.widget()
            if w:w.deleteLater()
    def render_sections(self,sections):
        self.clear_body()
        for title,color,rows in sections:
            box=QGroupBox(title);box.setStyleSheet(f'QGroupBox {{ border:1px solid {color}; margin-top:9px; padding-top:7px; }} QGroupBox::title {{ color:{color}; font-weight:600; }}')
            layout=QVBoxLayout(box);layout.setContentsMargins(10,12,10,9);layout.setSpacing(6)
            for label,value,important in rows:
                row_widget=QWidget();row=QHBoxLayout(row_widget);row.setContentsMargins(0,0,0,0);row.setSpacing(14)
                key=QLabel(str(label));key.setStyleSheet('font-weight:600;');key.setAlignment(Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignTop);key.setFixedWidth(175)
                row.addWidget(key,0,Qt.AlignmentFlag.AlignTop)
                if label=='公式規約URL' and str(value).startswith(('http://','https://')):
                    value_box=QWidget();value_row=QHBoxLayout(value_box);value_row.setContentsMargins(0,0,0,0);value_row.setSpacing(0)
                    text=QPushButton('公式規約を開く');text.setToolTip(str(value));text.setAutoDefault(False);text.setFixedWidth(170)
                    text.setStyleSheet('QPushButton {color:#245d98; background:#f7fbff; border:1px solid #8eb2cf; padding:4px 10px;} QPushButton:hover {background:#e7f2fa;}')
                    text.clicked.connect(lambda _checked=False,url=str(value):self._open_official_url(url));value_row.addWidget(text);value_row.addStretch(1)
                    row.addWidget(value_box,1,Qt.AlignmentFlag.AlignTop)
                else:
                    text=QLabel(str(value));text.setWordWrap(True);text.setAlignment(Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignTop);text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse);text.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Preferred);text.setMinimumWidth(0)
                    if important:text.setStyleSheet('color:#9a2f19; font-weight:600;')
                    row.addWidget(text,1,Qt.AlignmentFlag.AlignTop)
                layout.addWidget(row_widget)
            self.body_layout.addWidget(box)
        self.body_layout.addStretch(1)



class ContestRuleViewDialog(_InfoViewer):
    def __init__(self,root,parent=None):
        super().__init__('コンテストルール表示',parent,'contest');self.root=Path(root);self.catalog=[]
        self.store=RuleStore(self.root);store=self.store
        for path in store.files():
            try:r,_=store.read(path)
            except (ValueError,OSError,StorageError):continue
            if not is_contest_rule(r):continue
            self.catalog.append((path,r))
        self.search.textChanged.connect(self.refilter);self.selector.currentIndexChanged.connect(self.show_selected);self.refilter()
    def _norm(self,text):return str(text).casefold().replace('　',' ')
    def refilter(self):
        current=self.selector.currentData();tokens=[x for x in self._norm(self.search.text()).split() if x]
        self.selector.blockSignals(True);self.selector.clear();matches=[]
        for path,rule in self.catalog:
            hay=self._norm(rule.get('name','')+' '+rule.get('sort_name','')+' '+str(rule.get('year',''))+' '+rule.get('organizer',''))
            if all(t in hay for t in tokens):matches.append((path,rule))
        for path,rule in matches:self.selector.addItem(self.store.display_label(rule,path),str(path))
        if current:
            i=self.selector.findData(current)
            if i>=0:self.selector.setCurrentIndex(i)
        self.selector.blockSignals(False)
        if tokens and matches:
            self.status.setText(f'{len(matches)}件の候補があります。コンテストを選択してください。');self.status.setStyleSheet('font-size:13pt; font-weight:700; color:#244f79; padding:3px 0;')
        elif tokens and not matches:
            self.status.setText('一致するコンテストがありません。');self.status.setStyleSheet('font-size:12pt; font-weight:600; color:#9a2f19; padding:3px 0;')
        else:
            self.status.setText(f'登録済みコンテスト {len(matches)}件。表示するコンテストを選択してください。');self.status.setStyleSheet('')
        self.show_selected()
    def show_selected(self,*_):
        data=self.selector.currentData()
        if not data:self.clear_body();return
        try:rule,_=RuleStore(self.root).read(data)
        except (ValueError,OSError,StorageError) as e:self.status.setText(str(e));self.clear_body();return
        self.status.setStyleSheet('');self.status.setText(f'{rule.get("name","")}（{rule.get("year","")}） — 登録済み規約データの読み取り専用表示です。')
        self.render_sections(contest_sections(rule))


class PartyRuleViewDialog(_InfoViewer):
    def __init__(self,parent=None):
        super().__init__('QSOパーティルール表示',parent,'qso_party');self.items=list(PARTIES);self.search.textChanged.connect(self.refilter);self.selector.currentIndexChanged.connect(self.show_selected);self.refilter()
    def refilter(self):
        current=self.selector.currentData();q=self.search.text().strip().casefold();self.selector.blockSignals(True);self.selector.clear();matches=[]
        for key in self.items:
            name,year,_,_=PARTIES[key]
            if not q or q in (name+' '+year).casefold():matches.append(key);self.selector.addItem(f'{name}（{year}）',key)
        if current:
            i=self.selector.findData(current)
            if i>=0:self.selector.setCurrentIndex(i)
        self.selector.blockSignals(False);self.status.setText(f'{len(matches)}件の候補があります。QSOパーティを選択してください。' if q and matches else '一致するQSOパーティがありません。' if q else '表示するQSOパーティを選択してください。');self.show_selected()
    def show_selected(self,*_):
        key=self.selector.currentData()
        if not key:self.clear_body();return
        self.render_sections(party_sections(key))


class AwardConditionViewDialog(_InfoViewer):
    def __init__(self,root,parent=None):
        super().__init__('アワード条件表示',parent,'award');self.root=Path(root);self.items=list(AWARDS);self.search.textChanged.connect(self.refilter);self.selector.currentIndexChanged.connect(self.show_selected);self.refilter()
    def refilter(self):
        current=self.selector.currentData();q=self.search.text().strip().casefold();self.selector.blockSignals(True);self.selector.clear();matches=[]
        for name in self.items:
            if not q or q in name.casefold():matches.append(name);self.selector.addItem(name,name)
        if current:
            i=self.selector.findData(current)
            if i>=0:self.selector.setCurrentIndex(i)
        self.selector.blockSignals(False);self.status.setText(f'{len(matches)}件の候補があります。アワードを選択してください。' if q and matches else '一致するアワードがありません。' if q else '表示するアワードを選択してください。');self.show_selected()
    def show_selected(self,*_):
        name=self.selector.currentData()
        if not name:self.clear_body();return
        self.render_sections(award_sections(self.root,name))
