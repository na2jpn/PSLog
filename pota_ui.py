from pathlib import Path
from PySide6.QtCore import Qt,QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QVBoxLayout,QHBoxLayout,QFormLayout,QWidget,QSplitter,
    QLineEdit,QLabel,QComboBox,QCheckBox,QListWidget,QListWidgetItem,QFileDialog)
from window_geometry import SafeDialog
from search import file_identity,hits_to_rows
from search_ui import button
from storage import StorageError,VERSION
from pota_export import prepare,prepare_selected,save,PotaSaveFailure,normalize

class PotaDialog(SafeDialog):
    def __init__(self,repo,own='',parent=None,hits=None):
        super().__init__(parent);self.repo=repo;self.imported_hits=list(hits or []);self.imported_sessions=[];self.imported_rows=[]
        self.setWindowTitle(f'PSLog Ver{VERSION} — POTA提出用ADIFファイル');self.resize(1160,660)
        layout=QVBoxLayout(self)
        self.source_note=QLabel();self.source_note.setWordWrap(True);self.source_note.hide();layout.addWidget(self.source_note)
        split=QSplitter(Qt.Orientation.Horizontal);layout.addWidget(split,1)
        left=QWidget();self.source_panel=left;box=QVBoxLayout(left);split.addWidget(left)
        form=QFormLayout();box.addLayout(form)
        self.search=QLineEdit(own);form.addRow('自局コールで検索',self.search)
        self.own=QComboBox();form.addRow('出力元の自局',self.own)
        label=QLabel(str(repo.book));label.setWordWrap(True);label.setToolTip(str(repo.book));box.addWidget(label)
        self.logs=QListWidget();box.addWidget(self.logs,1)
        row=QHBoxLayout();self.all_button=button('全て選択',lambda:self.check_all(True));self.none_button=button('選択解除',lambda:self.check_all(False));row.addWidget(self.all_button);row.addWidget(self.none_button);box.addLayout(row)
        form=QFormLayout();box.addLayout(form)
        self.start=QLineEdit();self.end=QLineEdit()
        for e in (self.start,self.end):e.setPlaceholderText('YYYYMMDDhhmmss・先頭だけでも可（空欄は制限なし）')
        form.addRow('開始',self.start);form.addRow('終了',self.end);period_note=QLabel('空欄は制限なし。開始は指定期間の先頭、終了は指定期間の末尾として扱います。例：終了 20260917 → 2026/09/17 23:59:59');period_note.setWordWrap(True);form.addRow(period_note)
        self.rmks=QCheckBox('RMKSの内容で絞り込む');form.addRow(self.rmks)
        self.word=QLineEdit();self.word.setPlaceholderText('部分一致・大文字小文字を区別しない');form.addRow('含まれる文字列',self.word)
        right=QWidget();form=QFormLayout(right);split.addWidget(right);split.setSizes([580,580])
        self.parks=QLineEdit();self.parks.setPlaceholderText('JA-1222 または JA-1222 JA-1234');form.addRow('自局の公園番号',self.parks)
        note=QLabel('2ferなど複数の公園は空白・カンマで区切ります。\n指定した全公園に、抽出した同じ交信を出力します。\n公園・UTC日ごとにファイルを分けます。');note.setWordWrap(True);form.addRow(note)
        self.station=QLineEdit();form.addRow('運用コールサイン',self.station)
        self.operator=QLineEdit(own.split('/')[0]);form.addRow('OPERATOR',self.operator)
        self.state=QLineEdit();self.state.setPlaceholderText('必要な場合のみ');form.addRow('MY_STATE（任意）',self.state)
        note=QLabel('複数の地域にまたがる公園では、運用した地域の\nコードを指定するか、POTAへの提出時に選択します。');note.setWordWrap(True);form.addRow(note)
        default_folder=getattr(repo,'pota_output',repo.root/'output'/'pota')
        try:default_folder.mkdir(parents=True,exist_ok=True)
        except OSError:pass
        self.folder=QLineEdit(str(default_folder));row=QHBoxLayout();row.addWidget(self.folder);row.addWidget(button('変更…',self.choose_folder));form.addRow('保存先',row)
        note=QLabel('ファイル名：自局@公園番号-UTC日.adi\n同名があれば _001 から連番を付けます。\n\n元ログは変更しません。時刻はJSTからUTCへ変換。\n2ferでも交信時刻はずらしません。\n\n相手公園のP2P情報は、この版では出力しません。');note.setWordWrap(True);form.addRow(note)
        form.addRow(button('保存先フォルダーを開く',self.open_folder))
        self.status=QLabel();self.status.setWordWrap(True);layout.addWidget(self.status)
        row=QHBoxLayout();row.addStretch();self.save_button=button('POTA用ADIFを出力',self.write);row.addWidget(self.save_button);row.addWidget(button('閉じる',self.reject));layout.addLayout(row)
        self.search.textChanged.connect(self.find_calls);self.own.currentTextChanged.connect(self.find_logs)
        self.rmks.toggled.connect(self.controls)
        for edit in (self.start,self.end,self.word,self.parks,self.station,self.operator,self.state,self.folder):edit.textChanged.connect(self.changed)
        self.folder.textChanged.connect(self.folder.setToolTip);self.folder.setToolTip(self.folder.text())
        self.logs.itemChanged.connect(self.changed);self.find_calls();self.controls();self.apply_imported_hits()
    def apply_imported_hits(self):
        if not self.imported_hits:return
        self.source_note.show()
        self.source_note.setStyleSheet('color:#b00020;font-weight:bold;background:#fff0f0;border:1px solid #e2a4ac;padding:7px')
        self.source_panel.hide()
        self.imported_sessions,self.imported_rows=hits_to_rows(self.imported_hits)
        owns=sorted({r[0] for r in self.imported_rows})
        own=owns[0] if len(owns)==1 else ''
        if own:
            self.search.blockSignals(True);self.search.setText(own);self.search.blockSignals(False)
            self.own.blockSignals(True);self.own.clear();self.own.addItem(own);self.own.blockSignals(False)
            self.station.setText(own);self.operator.setText(own.split('/')[0])
        files=[]
        for _,_,path,_ in self.imported_rows:
            if str(path) not in files:files.append(str(path))
        self.logs.blockSignals(True);self.logs.clear()
        for path in files:
            item=QListWidgetItem(Path(path).name);item.setToolTip(path);item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled);self.logs.addItem(item)
        self.logs.blockSignals(False)
        for widget in (self.search,self.own,self.logs,self.all_button,self.none_button,self.start,self.end,self.rmks,self.word):widget.setEnabled(False)
        if len(owns)==1:
            self.source_note.setText(f'【ログ検索結果を使用中】 チェック済み {len(self.imported_rows):,}交信をそのまま使用します。\nログ・期間・RMKSの再指定は行いません。検索結果一覧でチェックした交信だけが対象です。')
        else:
            self.source_note.setText('検索結果に複数の自局コールが含まれています。POTA用はログ検索で1つの運用コールに絞ってください。')
        self.changed()
    def changed(self,*args):self.status.clear();self.save_button.setEnabled(True)
    def controls(self):
        self.start.setEnabled(True);self.end.setEnabled(True);self.word.setEnabled(self.rmks.isChecked());self.changed()
    def find_calls(self):
        self.own.clear();calls=set()
        for path in self.repo.book.glob('*.txt'):
            ident=file_identity(path)
            if ident and normalize(self.search.text()) in ident[1]:calls.add(ident[1])
        self.own.addItems(sorted(calls));self.find_logs()
    def find_logs(self):
        self.logs.clear();own=self.own.currentText()
        if own:
            for p in self.repo.files(own):
                item=QListWidgetItem(p.name);item.setData(Qt.ItemDataRole.UserRole,str(p));item.setToolTip(str(p));item.setFlags(item.flags()|Qt.ItemFlag.ItemIsUserCheckable);item.setCheckState(Qt.CheckState.Unchecked);self.logs.addItem(item)
        self.station.setText(own);self.changed()
    def check_all(self,on):
        for i in range(self.logs.count()):self.logs.item(i).setCheckState(Qt.CheckState.Checked if on else Qt.CheckState.Unchecked)
    def choose_folder(self):
        p=QFileDialog.getExistingDirectory(self,'出力先フォルダー',self.folder.text())
        if p:self.folder.setText(p)
    def open_folder(self):
        p=Path(self.folder.text()).resolve()
        if p.is_dir():QDesktopServices.openUrl(QUrl.fromLocalFile(str(p)))
    def write(self):
        self.status.clear();self.save_button.setEnabled(False)
        try:
            if self.rmks.isChecked() and not self.word.text().strip():raise ValueError('RMKSの検索文字列を入力してください。')
            if self.imported_hits:
                if len({r[0] for r in self.imported_rows})!=1:raise ValueError('検索結果に複数の自局コールが含まれています。POTA用は1つの運用コールに絞ってください。')
                plan=prepare_selected(self.imported_sessions,self.imported_rows,self.imported_rows[0][0],self.station.text(),self.operator.text(),self.parks.text(),self.state.text())
            else:
                paths=[self.logs.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.logs.count()) if self.logs.item(i).checkState()==Qt.CheckState.Checked]
                plan=prepare(self.repo,paths,self.own.currentText(),self.station.text(),self.operator.text(),self.parks.text(),self.start.text(),self.end.text(),self.word.text().strip() if self.rmks.isChecked() else '',self.state.text())
            saved=save(plan,self.folder.text())
            self.status.setText(f'{plan.qsos:,}交信を {len(saved)}ファイルへ出力しました。\n保存先: {Path(self.folder.text()).resolve()}\n'+saved[0].name+(' ほか' if len(saved)>1 else '')+('\n'+'\n'.join(plan.warnings) if plan.warnings else ''))
        except PotaSaveFailure as e:
            self.status.setText(str(e)+'\n作成済み: '+(', '.join(p.name for p in e.saved[:3]) or 'なし')+(' ほか' if len(e.saved)>3 else ''))
        except (StorageError,OSError,ValueError) as e:self.status.setText(str(e));self.save_button.setEnabled(True)
