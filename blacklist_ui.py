from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog,QVBoxLayout,QHBoxLayout,QFormLayout,QLabel,QLineEdit,
    QTextEdit,QCheckBox,QTableWidget,QTableWidgetItem,QAbstractItemView,QHeaderView,QMessageBox)
from blacklist import Blacklist,Entry
from search_ui import button
from storage import StorageError,VERSION
from window_tint import apply_window_tint

from window_geometry import SafeDialog as QDialog

class EntryDialog(QDialog):
    def __init__(self,store,entry=None,parent=None):
        super().__init__(parent);self.store=store;self.entry=entry;self.saved=False
        self.setWindowTitle('ブラックリスト登録・編集');self.resize(610,390);apply_window_tint(self,'blacklist')
        outer=QVBoxLayout(self);form=QFormLayout();outer.addLayout(form)
        self.call=QLineEdit(entry.call if entry else '');form.addRow('相手コールサイン',self.call)
        self.memo=QTextEdit();self.memo.setPlainText(entry.memo if entry else '');form.addRow('補足メモ',self.memo)
        self.portable=QCheckBox('このコールの /1・/P 等も警告対象にする');self.portable.setChecked(entry.portable if entry else False);outer.addWidget(self.portable)
        note=QLabel('チェックなしは完全一致。チェックありでも、別の局の部分一致や海外プリフィックスを自動推定しません。');note.setWordWrap(True);outer.addWidget(note)
        self.error=QLabel();self.error.setWordWrap(True);outer.addWidget(self.error)
        row=QHBoxLayout();row.addStretch();row.addWidget(button('保存',self.save));row.addWidget(button('キャンセル',self.reject));outer.addLayout(row)
    def save(self):
        try:self.store.update(Entry(self.call.text(),self.memo.toPlainText(),self.portable.isChecked()),self.entry.call if self.entry else None)
        except (ValueError,StorageError,OSError) as e:self.error.setText(str(e));return
        self.saved=True;self.accept()

class BlacklistDialog(QDialog):
    def __init__(self,root,parent=None):
        super().__init__(parent);self.root=root;self.store=None;self.visible=[]
        self.setWindowTitle(f'PSLog Ver{VERSION} — ブラックリスト管理');self.resize(900,570);apply_window_tint(self,'blacklist')
        outer=QVBoxLayout(self);note=QLabel('一致した場合は警告を表示します。OKで閉じた後は、交信入力・記録を続けられます。');note.setWordWrap(True);outer.addWidget(note)
        row=QHBoxLayout();self.filter=QLineEdit();self.filter.setPlaceholderText('コールサイン・メモを検索');row.addWidget(self.filter);row.addWidget(button('再読み込み',self.reload));outer.addLayout(row)
        self.table=QTableWidget(0,3);self.table.setHorizontalHeaderLabels(['コールサイン','移動運用も対象','補足メモ']);self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows);self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection);self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers);self.table.horizontalHeader().setStretchLastSection(True);self.table.setColumnWidth(0,170);self.table.setColumnWidth(1,160);outer.addWidget(self.table,1)
        self.status=QLabel();self.status.setWordWrap(True);outer.addWidget(self.status)
        row=QHBoxLayout();self.add_button=button('新規登録',self.add);self.edit_button=button('選択した登録を編集',self.edit);self.delete_button=button('選択した登録を削除',self.delete)
        for b in (self.add_button,self.edit_button,self.delete_button):row.addWidget(b)
        row.addStretch();row.addWidget(button('閉じる',self.reject));outer.addLayout(row)
        self.filter.textChanged.connect(self.fill);self.table.itemSelectionChanged.connect(self.selected_changed);self.reload()
    def reload(self):
        try:self.store=Blacklist(self.root);self.status.setText('保存先: '+str(self.store.path))
        except (StorageError,OSError) as e:self.store=None;self.status.setText(str(e))
        self.fill()
    def fill(self):
        self.table.setRowCount(0);term=self.filter.text().casefold()
        self.visible=[e for e in self.store.entries if term in (e.call+' '+e.memo).casefold()] if self.store else []
        for e in self.visible:
            row=self.table.rowCount();self.table.insertRow(row)
            for col,value in enumerate([e.call,'はい' if e.portable else '完全一致',e.memo]):
                item=QTableWidgetItem(value);item.setToolTip(value);self.table.setItem(row,col,item)
        self.add_button.setEnabled(self.store is not None);self.selected_changed()
    def selected(self):
        row=self.table.currentRow();return self.visible[row] if 0<=row<len(self.visible) else None
    def selected_changed(self):
        enabled=self.selected() is not None;self.edit_button.setEnabled(enabled);self.delete_button.setEnabled(enabled)
    def show_editor(self,entry=None):
        if not self.store:return
        d=EntryDialog(self.store,entry,self);d.exec()
        if d.saved:self.fill();self.status.setText('登録を保存しました。交信ログは変更していません。')
    def add(self):self.show_editor()
    def edit(self):
        entry=self.selected()
        if entry:self.show_editor(entry)
    def delete(self):
        entry=self.selected()
        if not entry:return
        if QMessageBox.question(self,'登録の削除',entry.call+' をブラックリストから削除しますか？\n交信ログは削除しません。',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:return
        try:self.store.update(original=entry.call)
        except (ValueError,StorageError,OSError) as e:self.status.setText(str(e));return
        self.fill();self.status.setText('ブラックリストの登録を削除しました。')
