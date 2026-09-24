from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QVBoxLayout,QHBoxLayout,QFormLayout,QWidget,QSplitter,QLineEdit,QLabel,QComboBox,QCheckBox,QListWidget,QListWidgetItem,QFileDialog,QTableWidget,QTableWidgetItem,QAbstractItemView)
from window_geometry import SafeDialog
from search_ui import button
from search import file_identity,hits_to_rows
from storage import StorageError,VERSION
from sota_export import Selection,select,prepare,save,SaveFailure,norm,summit,key

class SummitDialog(SafeDialog):
    def __init__(self,selection,refs,parent=None):
        super().__init__(parent);self.rows=selection.rows;self.draft=dict(refs);self.result_refs=None;self.checks=set();self.page=0;self.loading=False
        self.setWindowTitle('相手の山頂番号を設定');self.resize(1100,640);layout=QVBoxLayout(self)
        row=QHBoxLayout();self.bulk=QLineEdit();self.bulk.setPlaceholderText('例：JA/ST-001');row.addWidget(self.bulk);row.addWidget(button('選択した空欄に一括設定',self.fill_blank));layout.addLayout(row)
        row=QHBoxLayout();row.addWidget(button('全交信を選択',lambda:self.check_all(True)));row.addWidget(button('選択解除',lambda:self.check_all(False)));layout.addLayout(row)
        self.table=QTableWidget(0,6);self.table.setHorizontalHeaderLabels(['選択','日時 JST','相手コール','BAND / MODE','RMKS','相手山頂番号']);self.table.setColumnWidth(0,45);self.table.setColumnWidth(1,150);self.table.setColumnWidth(2,100);self.table.setColumnWidth(3,110);self.table.setColumnWidth(4,155);self.table.setColumnWidth(5,150);layout.addWidget(self.table,1)
        row=QHBoxLayout();self.prev=button('前へ',lambda:self.move(-1));row.addWidget(self.prev);self.page_label=QLabel();row.addWidget(self.page_label);self.next=button('次へ',lambda:self.move(1));row.addWidget(self.next);layout.addLayout(row)
        self.status=QLabel('山頂の実在・有効期間は照合しません。');self.status.setWordWrap(True);layout.addWidget(self.status)
        row=QHBoxLayout();row.addStretch();row.addWidget(button('設定を反映',self.apply));row.addWidget(button('キャンセル',self.reject));layout.addLayout(row)
        self.table.itemChanged.connect(self.changed);self.draw()
    def draw(self):
        self.loading=True;self.table.setRowCount(0)
        for i,r in enumerate(self.rows[self.page*100:(self.page+1)*100]):
            q=r[1];self.table.insertRow(i)
            for j,text in enumerate(['',q.date+' '+q.time,q.call,q.band+' / '+q.mode,q.remarks,self.draft.get(key(r),'')]):
                item=QTableWidgetItem(text)
                if j==0:item.setFlags(Qt.ItemFlag.ItemIsEnabled|Qt.ItemFlag.ItemIsUserCheckable);item.setCheckState(Qt.CheckState.Checked if key(r) in self.checks else Qt.CheckState.Unchecked)
                elif j!=5:item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                item.setToolTip(text);self.table.setItem(i,j,item)
        pages=max(1,(len(self.rows)+99)//100);self.page_label.setText(f'{self.page+1} / {pages}（100行ずつ）');self.prev.setEnabled(self.page>0);self.next.setEnabled(self.page+1<pages);self.loading=False
    def changed(self,item):
        if self.loading:return
        k=key(self.rows[self.page*100+item.row()])
        if item.column()==5:self.draft[k]=item.text()
        elif item.column()==0:
            if item.checkState()==Qt.CheckState.Checked:self.checks.add(k)
            else:self.checks.discard(k)
    def check_all(self,on):self.checks={key(r) for r in self.rows} if on else set();self.draw()
    def move(self,d):self.page+=d;self.draw()
    def fill_blank(self):
        try:value=summit(self.bulk.text())
        except ValueError as e:self.status.setText(str(e));return
        count=0
        for k in self.checks:
            if not self.draft.get(k,'').strip():self.draft[k]=value;count+=1
        self.draw();self.status.setText(f'{count}件の空欄に設定しました。')
    def apply(self):
        try:self.result_refs={key(r):summit(self.draft.get(key(r),''),optional=True) for r in self.rows}
        except ValueError as e:self.status.setText(str(e));return
        self.accept()

class SotaDialog(SafeDialog):
    def __init__(self,repo,own='',parent=None,hits=None):
        super().__init__(parent);self.repo=repo;self.selection=None;self.refs={};self.imported_hits=list(hits or [])
        self.setWindowTitle(f'PSLog Ver{VERSION} — SOTA提出用CSVファイル');self.resize(1140,650)
        layout=QVBoxLayout(self)
        self.source_note=QLabel();self.source_note.setWordWrap(True);self.source_note.hide();layout.addWidget(self.source_note)
        split=QSplitter(Qt.Orientation.Horizontal);layout.addWidget(split,1)
        left=QWidget();self.source_panel=left;box=QVBoxLayout(left);split.addWidget(left);form=QFormLayout();box.addLayout(form)
        self.search=QLineEdit(own);form.addRow('自局コールで検索',self.search);self.own=QComboBox();form.addRow('出力元の自局',self.own)
        self.logs=QListWidget();box.addWidget(self.logs,1);row=QHBoxLayout();self.all_button=button('全て選択',lambda:self.check_all(True));self.none_button=button('選択解除',lambda:self.check_all(False));row.addWidget(self.all_button);row.addWidget(self.none_button);box.addLayout(row)
        form=QFormLayout();box.addLayout(form)
        self.start=QLineEdit();self.end=QLineEdit()
        for e in (self.start,self.end):e.setPlaceholderText('YYYYMMDDhhmm・先頭だけでも可（空欄は制限なし）')
        form.addRow('開始',self.start);form.addRow('終了',self.end);period_note=QLabel('空欄は制限なし。開始は指定期間の先頭、終了は指定期間の末尾として扱います。例：終了 20260917 → 2026/09/17 23:59');period_note.setWordWrap(True);form.addRow(period_note);self.rmks=QLineEdit();self.rmks.setPlaceholderText('空欄なら絞り込みなし');form.addRow('RMKSに含む文字',self.rmks)
        self.load_button=button('対象交信を読み込む',self.load_rows);box.addWidget(self.load_button)
        right=QWidget();form=QFormLayout(right);split.addWidget(right);split.setSizes([560,580])
        self.kind=QComboBox();self.kind.addItems(['Activator（山頂から運用）','Chaser（山頂局と交信）','S2S（山頂同士）']);form.addRow('運用種別',self.kind)
        self.own_ref=QLineEdit();self.own_ref.setPlaceholderText('例：JA/ST-001');form.addRow('自局の山頂番号',self.own_ref)
        self.other_button=button('相手の山頂番号を設定…',self.edit_refs);form.addRow(self.other_button)
        self.count=QLabel();self.count.setWordWrap(True);form.addRow(self.count)
        self.comment=QLineEdit();self.comment.setPlaceholderText('任意・半角英数字と記号');form.addRow('提出用メモ',self.comment)
        default_folder=getattr(repo,'sota_output',repo.root/'output'/'sota')
        try:default_folder.mkdir(parents=True,exist_ok=True)
        except OSError:pass
        self.folder=QLineEdit(str(default_folder));row=QHBoxLayout();row.addWidget(self.folder);row.addWidget(button('変更…',self.browse));form.addRow('保存先',row)
        note=QLabel('SOTA CSV V2・UTC日ごとに別ファイル。\n同名ファイルは連番で保存します。\n\nActivatorの相手山頂は任意、Chaser・S2Sは必須。\n入力した山頂番号は元ログに書き込みません。\n\n提出用メモのカンマは _ に置換します。\n山頂番号の実在・有効期間は未照合です。');note.setWordWrap(True);form.addRow(note)
        self.status=QLabel();self.status.setWordWrap(True);layout.addWidget(self.status);row=QHBoxLayout();row.addStretch();self.save_button=button('CSVを出力',self.write);row.addWidget(self.save_button);row.addWidget(button('閉じる',self.reject));layout.addLayout(row)
        self.search.textChanged.connect(self.find_calls);self.own.currentTextChanged.connect(self.find_logs);self.logs.itemChanged.connect(self.invalidate)
        for e in (self.start,self.end,self.rmks):e.textChanged.connect(self.invalidate)
        self.kind.currentIndexChanged.connect(self.refresh)
        for e in (self.own_ref,self.comment,self.folder):e.textChanged.connect(self.refresh)
        self.folder.textChanged.connect(self.folder.setToolTip);self.folder.setToolTip(self.folder.text());self.find_calls();self.refresh();self.apply_imported_hits()
    def apply_imported_hits(self):
        if not self.imported_hits:return
        self.source_note.show()
        self.source_note.setStyleSheet('color:#b00020;font-weight:bold;background:#fff0f0;border:1px solid #e2a4ac;padding:7px')
        self.source_panel.hide()
        sessions,rows=hits_to_rows(self.imported_hits);owns=sorted({r[0] for r in rows})
        files=[]
        for _,_,path,_ in rows:
            if str(path) not in files:files.append(str(path))
        self.logs.blockSignals(True);self.logs.clear()
        for path in files:
            item=QListWidgetItem(Path(path).name);item.setToolTip(path);item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled);self.logs.addItem(item)
        self.logs.blockSignals(False)
        for widget in (self.search,self.own,self.logs,self.all_button,self.none_button,self.start,self.end,self.rmks,self.load_button):widget.setEnabled(False)
        if len(owns)==1:
            own=owns[0]
            self.search.blockSignals(True);self.search.setText(own);self.search.blockSignals(False)
            self.own.blockSignals(True);self.own.clear();self.own.addItem(own);self.own.blockSignals(False)
            self.selection=Selection(sessions,rows);self.refs={}
            self.source_note.setText(f'【ログ検索結果を使用中】 チェック済み {len(rows):,}交信をそのまま使用します。\nログ・期間・RMKSの再指定は行いません。検索結果一覧でチェックした交信だけが対象です。')
        else:
            self.selection=None;self.refs={}
            self.source_note.setText('検索結果に複数の自局コールが含まれています。SOTA用はログ検索で1つの運用コールに絞ってください。')
        self.status.clear();self.refresh()
    def invalidate(self,*args):self.selection=None;self.refs={};self.refresh();self.status.setText('対象条件を変更しました。交信を読み込んでください。')
    def refresh(self,*args):
        manual_source=not self.imported_hits
        self.start.setEnabled(manual_source);self.end.setEnabled(manual_source);self.own_ref.setEnabled(self.kind.currentIndex()!=1);self.other_button.setEnabled(self.selection is not None);self.save_button.setEnabled(self.selection is not None)
        count=len(self.selection.rows) if self.selection else 0;assigned=sum(bool(self.refs.get(key(r))) for r in self.selection.rows) if self.selection else 0
        self.count.setText(f'対象 {count:,}交信 ／ 相手山頂設定済み {assigned:,}件')
    def find_calls(self):
        self.own.clear();calls=set()
        for p in self.repo.book.glob('*.txt'):
            ident=file_identity(p)
            if ident and norm(self.search.text()) in ident[1]:calls.add(ident[1])
        self.own.addItems(sorted(calls));self.find_logs()
    def find_logs(self):
        self.logs.clear()
        if self.own.currentText():
            for p in self.repo.files(self.own.currentText()):
                item=QListWidgetItem(p.name);item.setData(Qt.ItemDataRole.UserRole,str(p));item.setToolTip(str(p));item.setFlags(item.flags()|Qt.ItemFlag.ItemIsUserCheckable);item.setCheckState(Qt.CheckState.Unchecked);self.logs.addItem(item)
        self.invalidate()
    def check_all(self,on):
        for i in range(self.logs.count()):self.logs.item(i).setCheckState(Qt.CheckState.Checked if on else Qt.CheckState.Unchecked)
    def load_rows(self):
        self.invalidate()
        try:
            paths=[self.logs.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.logs.count()) if self.logs.item(i).checkState()==Qt.CheckState.Checked]
            self.selection=select(self.repo,paths,self.own.currentText(),self.start.text(),self.end.text(),self.rmks.text().strip());self.status.clear();self.refresh()
        except (ValueError,StorageError,OSError) as e:self.status.setText(str(e))
    def edit_refs(self):
        if not self.selection:return
        dialog=SummitDialog(self.selection,self.refs,self)
        if dialog.exec()==SafeDialog.DialogCode.Accepted:self.refs=dialog.result_refs;self.refresh()
    def browse(self):
        p=QFileDialog.getExistingDirectory(self,'出力先',self.folder.text())
        if p:self.folder.setText(p)
    def write(self):
        if not self.selection:return
        self.save_button.setEnabled(False)
        try:
            plan=prepare(self.selection,['activator','chaser','s2s'][self.kind.currentIndex()],self.own_ref.text(),self.refs,self.comment.text());paths=save(plan,self.folder.text())
            self.status.setText(f'{plan.qsos}交信を{len(paths)}ファイルへ出力しました。\n保存先: {Path(self.folder.text()).resolve()}\n'+paths[0].name+(' ほか' if len(paths)>1 else '')+('\n'+'\n'.join(plan.warnings) if plan.warnings else ''))
        except SaveFailure as e:self.status.setText(str(e)+'\n作成済み: '+', '.join(p.name for p in e.saved[:3]))
        except (ValueError,StorageError,OSError) as e:self.status.setText(str(e));self.refresh()
