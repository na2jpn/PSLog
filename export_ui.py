from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QVBoxLayout,QHBoxLayout,QFormLayout,QWidget,QLineEdit,QLabel,QComboBox,QCheckBox,QSpinBox,
    QListWidget,QListWidgetItem,QTextEdit,QFileDialog,QMessageBox,QStackedWidget,QTableWidget,QTableWidgetItem,QHeaderView,QGroupBox)
from search import file_identity,hits_to_rows,base_station_call,station_call_candidates
from search_ui import button
from storage import StorageError,VERSION
from window_tint import apply_window_tint
from exporting import prepare,prepare_rows,save
from window_geometry import SafeDialog as QDialog


class ExportDialog(QDialog):
    """Three-stage normal export: source -> field mapping -> confirmation/output."""
    def __init__(self,repo,own='',parent=None,hits=None):
        super().__init__(parent);self.repo=repo;self.plan=None;self.imported_hits=list(hits or []);self.page=0
        self.setWindowTitle(f'PSLog Ver{VERSION} — 通常エクスポート');self.resize(1160,760);apply_window_tint(self,'export')
        outer=QVBoxLayout(self)
        self.step_label=QLabel();self.step_label.setStyleSheet('font-weight:600;');outer.addWidget(self.step_label)
        self.stack=QStackedWidget();outer.addWidget(self.stack,1)
        self._build_source_page(own);self._build_mapping_page();self._build_confirm_page()
        self.status=QLabel();self.status.setWordWrap(True);outer.addWidget(self.status)
        nav=QHBoxLayout();self.back_button=button('戻る',self.back);self.next_button=button('次へ',self.next);self.save_button=button('ファイルへ出力',self.write)
        nav.addWidget(self.back_button);nav.addStretch();nav.addWidget(self.next_button);nav.addWidget(self.save_button);nav.addWidget(button('閉じる',self.reject));outer.addLayout(nav)
        self.own.currentTextChanged.connect(self.find_logs);self.logs.itemChanged.connect(self.invalidate);self.format.currentIndexChanged.connect(self.format_changed)
        for e in (self.start,self.end,self.folder):e.textChanged.connect(self.invalidate)
        self.latest.toggled.connect(self.invalidate)
        self.number.valueChanged.connect(self.invalidate)
        self.rmks1_target.currentIndexChanged.connect(self.invalidate);self.rmks2_target.currentIndexChanged.connect(self.invalidate);self.hamlog_identity.toggled.connect(self.invalidate)
        if self.imported_hits:self._use_search_hits()
        else:self.find_logs()
        self.show_page(0)

    def _build_source_page(self,own):
        page=QWidget();layout=QVBoxLayout(page);self.stack.addWidget(page)
        note=QLabel('出力するログと基本条件を設定してください。設定後［次へ］で、出力項目の対応を確認します。');note.setWordWrap(True);layout.addWidget(note)
        self.source_note=QLabel();self.source_note.setWordWrap(True);self.source_note.hide();layout.addWidget(self.source_note)
        row=QHBoxLayout();row.addWidget(QLabel('自局コール'));self.own=QComboBox();self.own.addItems(station_call_candidates(self.repo,own));self.own.setToolTip('PSLogのログファイル名から抽出した自局コールです。/1・/P 等は候補名から除きます。');row.addWidget(self.own,1);layout.addLayout(row)
        self.logs=QListWidget();layout.addWidget(self.logs,1)
        row=QHBoxLayout();self.check_all_button=button('全て選択',lambda:self.check_all(True));self.uncheck_all_button=button('選択解除',lambda:self.check_all(False));row.addWidget(self.check_all_button);row.addWidget(self.uncheck_all_button);row.addStretch();layout.addLayout(row)
        form=QFormLayout();layout.addLayout(form)
        self.format=QComboBox();self.format.addItems(['ADIF（.adi / ASCII）','ADIF（.adx / 日本語対応）','HAMLOG CSV（CP932）']);form.addRow('出力形式',self.format)
        self.start=QLineEdit();self.start.setPlaceholderText('YYYYMMDDhhmmss・先頭だけでも可（空欄は制限なし）');self.end=QLineEdit();self.end.setPlaceholderText('YYYYMMDDhhmmss・先頭だけでも可（空欄は制限なし）');form.addRow('開始（JST）',self.start);form.addRow('終了（JST・含む）',self.end)
        period_note=QLabel('空欄は制限なし。開始は指定期間の先頭、終了は指定期間の末尾として扱います。例：終了 20260917 → 2026/09/17 23:59:59');period_note.setWordWrap(True);form.addRow(period_note)
        self.latest=QCheckBox('最新N件に絞る');self.number=QSpinBox();self.number.setRange(1,2147483647);self.number.setValue(100);form.addRow(self.latest,self.number)
        default_folder=getattr(self.repo,'export_output',self.repo.root/'output'/'export')
        try:default_folder.mkdir(parents=True,exist_ok=True)
        except OSError:pass
        self.folder=QLineEdit(str(default_folder));r=QHBoxLayout();r.addWidget(self.folder);r.addWidget(button('保存先',self.choose_folder));form.addRow(r)

    def _build_mapping_page(self):
        page=QWidget();layout=QVBoxLayout(page);self.stack.addWidget(page)
        intro=QLabel('PSLog項目を出力形式の項目へ対応付けます。通常項目は標準定義に固定し、RMKS1 / RMKS2など意味のある項目だけ変更できます。');intro.setWordWrap(True);layout.addWidget(intro)
        fixed_box=QGroupBox('固定マッピング');fixed=QVBoxLayout(fixed_box);self.fixed_mapping=QTextEdit();self.fixed_mapping.setReadOnly(True);self.fixed_mapping.setMaximumHeight(250);fixed.addWidget(self.fixed_mapping);layout.addWidget(fixed_box)
        rm=QGroupBox('RMKSの出力先');form=QFormLayout(rm);self.rmks1_target=QComboBox();self.rmks2_target=QComboBox();form.addRow('RMKS1',self.rmks1_target);form.addRow('RMKS2',self.rmks2_target);self.hamlog_identity=QCheckBox('MYCALL / MYQTHをRemarks2へ出力する');self.hamlog_identity.setChecked(True);form.addRow('HAMLOG自局情報',self.hamlog_identity);layout.addWidget(rm)
        self.mapping_note=QLabel();self.mapping_note.setWordWrap(True);layout.addWidget(self.mapping_note);layout.addStretch(1)
        self._refresh_mapping_options()

    def _build_confirm_page(self):
        page=QWidget();layout=QVBoxLayout(page);self.stack.addWidget(page)
        note=QLabel('出力内容を確認してください。問題なければ［ファイルへ出力］を押します。');note.setWordWrap(True);layout.addWidget(note)
        self.details=QTextEdit();self.details.setReadOnly(True);layout.addWidget(self.details,1)

    def show_page(self,index):
        self.page=max(0,min(2,index));self.stack.setCurrentIndex(self.page)
        self.step_label.setText(['1 / 3　出力対象・基本条件','2 / 3　出力項目の対応','3 / 3　確認・出力'][self.page])
        self.back_button.setVisible(self.page>0);self.next_button.setVisible(self.page<2);self.save_button.setVisible(self.page==2);self.save_button.setEnabled(bool(self.plan) and self.page==2)
        if self.page==1:self._refresh_mapping_options()

    def invalidate(self,*args):
        self.plan=None
        if hasattr(self,'save_button'):self.save_button.setEnabled(False)
        if hasattr(self,'details'):self.details.setPlainText('条件または出力項目を変更しました。［次へ］で内容を再確認してください。')

    def _use_search_hits(self):
        self.source_note.setText(f'ログ検索・編集でチェックした {len(self.imported_hits):,}交信をそのまま使用します。\n検索結果一覧でチェック済みの交信だけが対象です。');self.source_note.show()
        for widget in (self.own,self.logs,self.check_all_button,self.uncheck_all_button,self.start,self.end,self.latest,self.number):widget.setEnabled(False)
        self.status.setText(f'検索結果 {len(self.imported_hits):,}交信を使用します。出力形式と保存先を確認して［次へ］へ進んでください。')

    def find_logs(self,*args):
        self.logs.clear();self.invalidate();selected=base_station_call(self.own.currentText())
        for p in sorted(self.repo.book.glob('*.txt')):
            identity=file_identity(p)
            if identity and base_station_call(identity[1])==selected:
                item=QListWidgetItem(p.name);item.setData(Qt.ItemDataRole.UserRole,str(p));item.setToolTip(str(p));item.setFlags(item.flags()|Qt.ItemFlag.ItemIsUserCheckable);item.setCheckState(Qt.CheckState.Unchecked);self.logs.addItem(item)
        self.status.setText(f'{self.logs.count()}件の候補。出力するログにチェックしてください。')

    def check_all(self,on):
        for i in range(self.logs.count()):self.logs.item(i).setCheckState(Qt.CheckState.Checked if on else Qt.CheckState.Unchecked)

    def choose_folder(self):
        p=QFileDialog.getExistingDirectory(self,'出力先フォルダー',self.folder.text())
        if p:self.folder.setText(p)

    def format_key(self):return ['adi','adx','csv'][self.format.currentIndex()]

    def format_changed(self,*_):
        self.invalidate();self._refresh_mapping_options()

    def _refresh_mapping_options(self):
        if not hasattr(self,'rmks1_target'):return
        fmt=self.format_key()
        r1=self.rmks1_target.currentText();r2=self.rmks2_target.currentText()
        self.rmks1_target.blockSignals(True);self.rmks2_target.blockSignals(True);self.rmks1_target.clear();self.rmks2_target.clear()
        self.hamlog_identity.setVisible(fmt=='csv')
        if fmt in ('adi','adx'):
            options=['COMMENT','QSLMSG','APP_PSLOG_RMKS1','APP_PSLOG_RMKS2','出力しない']
            self.rmks1_target.addItems(options);self.rmks2_target.addItems(options)
            self.rmks1_target.setCurrentText(r1 if r1 in options else 'COMMENT');self.rmks2_target.setCurrentText(r2 if r2 in options else 'APP_PSLOG_RMKS2')
            self.fixed_mapping.setPlainText('DATE/TIME → QSO_DATE/TIME_ON（UTC）\nHIS CALLSIGN → CALL\n自局コール → STATION_CALLSIGN\nBAND → BAND\nMODE → MODE / SUBMODE\nRSTs/RSTr → RST_SENT / RST_RCVD\nHIS QTH → QTH\nMY QTH → APP_PSLOG_MY_QTH\nJCC/JCG → APP_PSLOG_JCCJCG')
            self.mapping_note.setText('ADIFは標準フィールド名を使用します。独自情報はAPP_PSLOG_*で保持できます。同じ出力先をRMKS1/RMKS2の両方に選ぶと「 / 」で連結します。')
        else:
            options=['Remarks1','Remarks2','出力しない']
            self.rmks1_target.addItems(options);self.rmks2_target.addItems(options)
            self.rmks1_target.setCurrentText(r1 if r1 in options else 'Remarks1');self.rmks2_target.setCurrentText(r2 if r2 in options else 'Remarks2')
            self.fixed_mapping.setPlainText('HAMLOG 15列定義に従って固定変換します。\nCALL/DATE/TIME/RST/BAND/MODE/JCCJCG/HIS QTHは既定列へ出力。\nQSL欄・Name欄はRMKS1の判別可能な情報から補助。')
            self.mapping_note.setText('HAMLOGの列定義は固定です。RMKS1/RMKS2の出力先と、MYCALL/MYQTHをRemarks2へ出力するかを選べます。全て「出力しない」相当にすればRemarks1/Remarks2を空欄にできます。')
        self.rmks1_target.blockSignals(False);self.rmks2_target.blockSignals(False)

    def remark_mapping(self):return {'rmks1':self.rmks1_target.currentText(),'rmks2':self.rmks2_target.currentText(),'hamlog_identity':self.hamlog_identity.isChecked()}

    def _validate_source(self):
        if not Path(self.folder.text()).is_dir():raise ValueError('存在する出力先フォルダーを指定してください。')
        if not self.imported_hits and not any(self.logs.item(i).checkState()==Qt.CheckState.Checked for i in range(self.logs.count())):raise ValueError('出力するログにチェックしてください。')

    def next(self):
        self.status.clear()
        try:
            if self.page==0:
                self._validate_source();self.show_page(1);return
            if self.page==1:
                self.preview();return
        except (ValueError,StorageError,OSError) as e:self.status.setText(str(e))

    def back(self):
        if self.page>0:self.show_page(self.page-1)

    def preview(self):
        self.invalidate();self.status.clear()
        try:
            self._validate_source();fmt=self.format_key();mapping=self.remark_mapping()
            if self.imported_hits:
                if any(not h.editable for h in self.imported_hits):raise ValueError('検索結果に要確認行を含むログがあります。原本を確認・修正してから再検索してください。')
                sessions,rows=hits_to_rows(self.imported_hits);self.plan=prepare_rows(sessions,rows,fmt,remark_mapping=mapping)
            else:
                paths=[self.logs.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.logs.count()) if self.logs.item(i).checkState()==Qt.CheckState.Checked]
                self.plan=prepare(self.repo,paths,fmt,self.start.text(),self.end.text(),self.number.value() if self.latest.isChecked() else None,remark_mapping=mapping)
            p=self.plan;notes=['QSL状態は自動変換せずRMKSの判別可能な情報だけ補助します。','並び順：日時の古い順。同時刻は元ログパス・原本行番号順。','同名ファイルがあれば連番を付けます。原本は変更しません。']
            mapping_text=f'RMKS1 → {mapping["rmks1"]}\nRMKS2 → {mapping["rmks2"]}\n'
            if fmt=='csv':mapping_text+=f'MYCALL/MYQTH → {"Remarks2" if mapping["hamlog_identity"] else "出力しない"}\n'
            self.details.setPlainText(f'{len(p.sessions)}ログ / {len(p.rows):,}交信\n保存先: {Path(self.folder.text()).resolve()}\n形式: {p.extension}\n'+mapping_text+'\n'+'\n'.join(notes+p.warnings)+'\n\n先頭5件（原本JST）\n'+'\n'.join(f'{q.date} {q.time} {own} → {q.call} {q.band} {q.mode}' for own,q,_,_ in p.rows[:5]))
            self.show_page(2);self.save_button.setEnabled(True)
        except (ValueError,StorageError,OSError) as e:self.status.setText(str(e));self.plan=None;self.save_button.setEnabled(False)

    def write(self):
        if not self.plan:return
        if self.plan.warnings and QMessageBox.question(self,'出力内容の確認','表示された注意事項を確認して出力しますか？',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:return
        try:p=save(self.plan,self.folder.text())
        except (ValueError,StorageError,OSError) as e:self.status.setText(str(e));self.plan=None;self.save_button.setEnabled(False);return
        self.status.setText('出力しました: '+str(p));self.plan=None;self.save_button.setEnabled(False)
