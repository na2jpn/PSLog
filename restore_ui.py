"""Restore a selected backup with preview snapshots of both source and target."""
import re
from PySide6.QtCore import Qt,Signal
from PySide6.QtWidgets import (QDialog,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,
    QTableWidget,QTableWidgetItem,QAbstractItemView,QHeaderView,QSplitter,QTextEdit,QMessageBox)
from storage import Snapshot,parse,StorageError,InvalidLog,VERSION
from search import file_identity
from search_ui import button

from window_geometry import SafeDialog as QDialog

class RestoreDialog(QDialog):
    logs_changed=Signal()
    def __init__(self,repo,parent=None):
        super().__init__(parent);self.repo=repo;self.pending=None;self.entries=[]
        self.setWindowTitle(f'PSLog {VERSION} — ログバックアップから復元');self.resize(1120,660)
        layout=QVBoxLayout(self)
        text=QLabel('復元すると対象ログ全体が置き換わります。置き換え前の内容もバックアップに残します。');text.setWordWrap(True);layout.addWidget(text)
        row=QHBoxLayout();row.addWidget(QLabel('ログ名で絞り込み'))
        self.filter=QLineEdit();self.filter.setPlaceholderText('年・自局コール（ファイル名の / は -）など');row.addWidget(self.filter,1)
        row.addWidget(button('一覧を再読み込み',self.reload));layout.addLayout(row)
        split=QSplitter(Qt.Orientation.Horizontal);layout.addWidget(split,1)
        self.table=QTableWidget(0,3);self.table.setHorizontalHeaderLabels(['元ログ','バックアップ日時（PC時刻）','バイト数'])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().hide();self.table.setWordWrap(False)
        self.table.setColumnWidth(0,250);self.table.setColumnWidth(1,210)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        split.addWidget(self.table);self.details=QTextEdit();self.details.setReadOnly(True);split.addWidget(self.details);split.setSizes([600,500])
        self.status=QLabel();self.status.setWordWrap(True);layout.addWidget(self.status)
        row=QHBoxLayout();row.addStretch();self.restore_button=button('選択したバックアップから復元…',self.restore)
        row.addWidget(self.restore_button);close=button('閉じる',self.reject);row.addWidget(close);layout.addLayout(row)
        self.table.itemSelectionChanged.connect(self.preview);self.filter.textChanged.connect(self.reload)
        self.reload()
    def reload(self):
        self.pending=None;self.restore_button.setEnabled(False);self.entries=[]
        self.table.setRowCount(0);self.details.setPlainText('バックアップを選ぶと復元先と交信件数を表示します。')
        errors=[]
        for p in sorted(self.repo.bak.glob('*.bak'),reverse=True):
            match=re.fullmatch(r'(.+\.txt)\.(\d{8})-(\d{6})-(\d{6})-[0-9a-f]{8}\.bak',p.name)
            if not match or not file_identity(match[1]):continue
            if self.filter.text().strip().casefold() not in match[1].casefold():continue
            try: size=p.stat().st_size
            except OSError as e:errors.append(str(e));continue
            day,t=match[2],match[3];stamp=f'{day[:4]}-{day[4:6]}-{day[6:]} {t[:2]}:{t[2:4]}:{t[4:]}'
            self.entries.append((p,self.repo.book/match[1],stamp,size))
        self.entries.sort(key=lambda e:e[0].name.rsplit('.txt.',1)[1],reverse=True)
        for p,target,stamp,size in self.entries:
            i=self.table.rowCount();self.table.insertRow(i)
            for col,value in enumerate([target.name,stamp,f'{size:,}']):
                item=QTableWidgetItem(value);item.setToolTip(str(p));self.table.setItem(i,col,item)
        self.status.setText(f'{len(self.entries)}件のバックアップ。'+(' 一部の読み込みに失敗しました。'+'; '.join(errors) if errors else ''))
    def preview(self):
        self.pending=None;self.restore_button.setEnabled(False)
        rows=self.table.selectionModel().selectedRows()
        if not rows:return
        p,target,stamp,size=self.entries[rows[0].row()]
        try:
            source=Snapshot.read(p)
            if source.data is None:raise StorageError('バックアップが見つかりません。')
            log=parse(source.data)
            if log.issues:raise InvalidLog('バックアップに要確認行があります。復元できません。')
            session=self.repo.open(target,for_restore=True)
            current='存在しません（新規に復元）' if session.snapshot.data is None else ('読取不可・要確認行あり' if session.log.issues else f'{len(session.log.records):,}交信')
            self.details.setPlainText(f'復元元\n{p}\n\nバックアップ日時（PC時刻）\n{stamp}\n\n復元先（ログ全体を置き換え）\n{target}\n\n現在のログ: {current}\n復元後: {len(log.records):,}交信\n\n現在のログがある場合、その内容を先にbakへ保存します。復元を取り消したいときは、そのバックアップを選んで復元できます。')
            self.pending=(session,p,source);self.restore_button.setEnabled(True)
        except (StorageError,OSError) as e:self.details.setPlainText(f'復元元: {p}\n復元先: {target}\n\n{e}')
    def restore(self):
        if not self.pending:return
        session,p,source=self.pending
        answer=QMessageBox.question(self,'ログ全体の復元確認',
            f'復元先: {session.path}\n\nこのログ全体を選択したバックアップに置き換えますか？\n置き換え前の内容もバックアップに残します。',
            QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)
        if answer!=QMessageBox.StandardButton.Yes:return
        try:session.restore(p,expected_backup=source)
        except (StorageError,OSError) as e:
            self.pending=None;self.restore_button.setEnabled(False);self.status.setText(str(e)+' 一覧を再読み込みしてください。');return
        self.logs_changed.emit();self.reload();self.status.setText('復元しました。置き換え前のログがあれば、バックアップ一覧から戻せます。')
