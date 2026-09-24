"""PS TXT / ADIF / HAMLOG CSV import preview and explicit commit."""
from pathlib import Path
from PySide6.QtCore import Signal,Qt
from PySide6.QtWidgets import (QDialog,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,
    QFileDialog,QCheckBox,QComboBox,QTextEdit,QSplitter,QWidget,QFormLayout,QMessageBox,QScrollArea)
from importing import prepare,commit,ImportFailure,qsl_markers
from storage import StorageError
from search_ui import button
from window_tint import apply_window_tint

from window_geometry import SafeDialog as QDialog

class ImportDialog(QDialog):
    logs_changed=Signal()
    def __init__(self,repo,own='',parent=None):
        super().__init__(parent);self.repo=repo;self.plan=None
        self.setWindowTitle('PSLog — ログインポート');self.resize(1100,650);apply_window_tint(self,'import')
        layout=QVBoxLayout(self);split=QSplitter(Qt.Orientation.Horizontal);layout.addWidget(split,1)
        left=QWidget();self.form=QFormLayout(left);form=self.form;scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(left);split.addWidget(scroll)
        self.source=QLineEdit();row=QHBoxLayout();row.addWidget(self.source);row.addWidget(button('ファイル選択',self.browse))
        form.addRow('ログファイル',row)
        self.format_label=QLabel('未判定');self.format_label.setStyleSheet('font-weight:600;');form.addRow('ファイル形式',self.format_label)
        self.own=QLineEdit(own);form.addRow('取り込み先の自局',self.own)
        self.suffix=QLineEdit();form.addRow('ファイル名付与文字（任意）',self.suffix)
        self.duplicates=QComboBox();self.duplicates.addItems(['重複は無視する（初期値）','全て追加で扱う']);form.addRow('重複の扱い',self.duplicates)
        self.exclude=QCheckBox('要確認行を除外する');form.addRow(self.exclude)
        self.sections=QCheckBox('運用区切りがあっても全件を指定自局へ取り込む');form.addRow(self.sections)
        self.override=QCheckBox('ADIF内の自局と異なっても画面の自局を使う');form.addRow(self.override)
        self.csv_encoding=QComboBox();self.csv_encoding.addItems(['CP932（標準）','UTF-8']);form.addRow('CSV文字コード',self.csv_encoding)
        self.csv_timezone=QComboBox();self.csv_timezone.addItems(['J/Uなしの時刻は要確認','J/UなしはJST','J/UなしはUTC']);form.addRow('CSV時刻',self.csv_timezone)
        self.csv_century=QComboBox();self.csv_century.addItems(['2桁年は2000年代','2桁年は1900年代']);form.addRow('CSVの2桁年',self.csv_century)
        self.conversions=QCheckBox('変換内容・秒の扱いを確認した');form.addRow(self.conversions)
        self.note=QLabel();self.note.setWordWrap(True);form.addRow(self.note)
        form.addRow(button('読み込み・件数を確認',self.preview))
        self.details=QTextEdit();self.details.setReadOnly(True);split.addWidget(self.details);split.setSizes([500,600])
        self.status=QLabel();self.status.setWordWrap(True);layout.addWidget(self.status)
        row=QHBoxLayout();row.addStretch();self.save_button=button('確認した内容を取り込む…',self.save);row.addWidget(self.save_button);row.addWidget(button('閉じる',self.reject));layout.addLayout(row)
        self.source.textChanged.connect(self.source_changed)
        for e in (self.own,self.suffix):e.textChanged.connect(self.invalidate)
        self.duplicates.currentIndexChanged.connect(self.invalidate);self.exclude.toggled.connect(self.invalidate);self.sections.toggled.connect(self.invalidate);self.override.toggled.connect(self.invalidate);self.conversions.toggled.connect(self.update_enabled)
        for combo in (self.csv_encoding,self.csv_timezone,self.csv_century):combo.currentIndexChanged.connect(self.invalidate)
        self.update_format_ui();self.invalidate()
    def source_format(self):
        ext=Path(self.source.text().strip()).suffix.lower()
        if ext=='.txt':return 'pslog','PSログTXT'
        if ext in ('.adi','.adif','.adx'):return 'adif','ADIF'+(' (ADX)' if ext=='.adx' else '')
        if ext=='.csv':return 'csv','HAMLOG CSV'
        return '','未判定'
    def set_row_visible(self,widget,visible):
        widget.setVisible(visible);label=self.form.labelForField(widget)
        if label is not None:label.setVisible(visible)
    def update_format_ui(self):
        kind,name=self.source_format();self.format_label.setText(name)
        self.sections.setVisible(kind=='pslog')
        self.override.setVisible(kind=='adif')
        for w in (self.csv_encoding,self.csv_timezone,self.csv_century):self.set_row_visible(w,kind=='csv')
        self.conversions.setVisible(kind in ('adif','csv'))
        if kind=='pslog':
            text='PSログTXTとして読み込みます。DATEの年で保存先を振り分けます。日時はJSTです。\n自局は交信行にないため、画面の「取り込み先の自局」を使います。'
        elif kind=='adif':
            text='ADIFとして読み込みます。UTC日時はJSTへ変換します。ADIF内の自局と画面指定が異なる場合は確認します。'
        elif kind=='csv':
            text='HAMLOG CSVとして読み込みます。CSV文字コード・J/Uなし時刻・2桁年の扱いを指定してください。'
        else:
            text='対応形式：PSログTXT (.txt)、ADIF (.adi / .adif / .adx)、HAMLOG CSV (.csv)。'
        self.note.setText(text+'\n重複判定：日付・時刻・相手コール・BAND・MODE。')
    def source_changed(self):
        self.update_format_ui();self.invalidate()
    def invalidate(self):
        had_plan=self.plan is not None;self.plan=None;self.conversions.setChecked(False);self.save_button.setEnabled(False)
        _,name=self.source_format();self.details.setPlainText(f'ファイル形式: {name}\nファイルと取り込み条件を指定し、件数を確認してください。')
        if had_plan:self.status.setStyleSheet('color:#9b4a00;');self.status.setText('取り込み条件を変更しました。「読み込み・件数を確認」をもう一度押してください。')
    def browse(self):
        p,_=QFileDialog.getOpenFileName(self,'ログファイルを選択','','PSログ形式 (*.txt);;ADIF (*.adi *.adif *.adx);;HAMLOG CSV (*.csv);;すべての対応ログ (*.txt *.adi *.adif *.adx *.csv)')
        if p:self.source.setText(p)
    def preview(self):
        self.invalidate();self.status.clear()
        try:self.plan=prepare(self.repo,self.source.text(),self.own.text(),self.suffix.text(),self.duplicates.currentIndex()==1,self.exclude.isChecked(),self.override.isChecked(),['cp932','utf-8-sig'][self.csv_encoding.currentIndex()],['','JST','UTC'][self.csv_timezone.currentIndex()],[2000,1900][self.csv_century.currentIndex()])
        except (StorageError,OSError,ValueError) as e:self.status.setText(str(e));return
        p=self.plan;count=sum(len(t['records']) for t in p.targets.values());skipped=sum(t['skipped'] for t in p.targets.values());dupes=sum(len(t.get('duplicates',[])) for t in p.targets.values());qsl_merges=sum(len(t.get('merges',{})) for t in p.targets.values())
        _,detected=self.source_format();fmt=p.metadata.get('format',detected) if p.metadata else detected
        duplicate_action=(f'{skipped:,}件を除外' if not p.all_add else f'{dupes:,}件も追加対象')
        lines=[f'形式: {fmt}',f'入力: {p.source}',f'自局: {p.call}',f'読取: {len(p.log.records):,}交信 / 追加予定: {count:,} / 重複候補: {dupes:,}（{duplicate_action}） / 既存QSLマージ予定: {qsl_merges:,}',f'要確認行: {len(p.log.issues)}','']
        for path,t in sorted(p.targets.items()):
            lines.extend([str(path),f"  追加予定 {len(t['records']):,} / 重複候補 {len(t.get('duplicates',[])):,} / 重複除外 {t['skipped']:,} / 既存QSLマージ {len(t.get('merges',{})):,}"])
        duplicate_rows=[]
        for path,t in sorted(p.targets.items()):
            for d in t.get('duplicate_details',[]):duplicate_rows.append((d,path))
        if duplicate_rows:
            mode='除外される重複（QSL情報だけ安全に補完）' if not p.all_add else '全て追加指定だが重複する交信'
            lines+=['',f'重複候補の詳細（{len(duplicate_rows):,}件）— {mode}']
            limit=500
            for d,path in duplicate_rows[:limit]:
                q=d['q'];before=', '.join(d.get('existing_qsl') or []) or 'なし';incoming=', '.join(d.get('incoming_qsl') or []) or 'なし';merged=', '.join(d.get('merged_qsl') or []) or 'なし'
                lines.append(f"{q.date} {q.time} {q.call}  {q.band}MHz {q.mode}  [{d['reason']}] → {path.name}")
                lines.append(f"    QSL 既存/先行: {before} / 入力: {incoming} / マージ追加: {merged} — {d.get('merge_note','')}")
            if len(duplicate_rows)>limit:lines.append(f'... 残り {len(duplicate_rows)-limit:,}件（表示は先頭{limit}件まで）')
        lines+=['','要確認箇所（TXTは行番号、ADIF/CSVは交信番号）']+[f'{i.line}: {i.reason}' for i in p.log.issues]
        markers=[n for n in p.log.notices if '年・運用' in n.reason]
        if markers:lines+=['','運用区切り：自局を自動判定しません。']+[f'{n.line}: {n.raw}' for n in markers]
        if p.metadata:
            lines+=['',p.metadata['format']+'の変換内容']+[f'{n.line}: {n.reason} {n.raw}' for n in p.log.notices]
            lines+=['','先頭5交信（変換後）']+[f'{q.date} {q.time} JST {q.call} {q.band} {q.mode}  {q.remarks}' for _,q in p.log.records[:5]]
        self.details.setPlainText('\n'.join(lines));self.update_enabled()
    def update_enabled(self):
        p=self.plan;reasons=[]
        actionable=bool(p and any(t['records'] or t.get('merges') for t in p.targets.values()))
        if p and not actionable:reasons.append('追加予定の交信も、既存ログへ補完できるQSL情報もありません。')
        if p and p.log.issues and not p.exclude_invalid:reasons.append('要確認行があります。「要確認行を除外する」を選び、もう一度「読み込み・件数を確認」を押してください。')
        if p and any('年・運用' in n.reason for n in p.log.notices) and not self.sections.isChecked():reasons.append('運用区切りがあります。内容を確認し、「運用区切りがあっても全件を指定自局へ取り込む」を選んでから、もう一度「読み込み・件数を確認」を押してください。')
        if p and p.metadata and not self.conversions.isChecked():reasons.append('ADIF/CSVの変換内容を確認し、「変換内容・秒の扱いを確認した」にチェックしてください。')
        enabled=bool(p and actionable and not reasons);self.save_button.setEnabled(enabled)
        if p:
            if reasons:self.status.setStyleSheet('color:#a33; font-weight:600;');self.status.setText('取り込みできません：'+'\n'.join(reasons))
            else:
                add=sum(len(t['records']) for t in p.targets.values());merged=sum(len(t.get('merges',{})) for t in p.targets.values())
                self.status.setStyleSheet('color:#275d2a;');self.status.setText(f'取り込み可能です。新規追加 {add:,}件 / 既存ログへのQSLマージ {merged:,}件。')
    def save(self):
        if not self.plan or not self.save_button.isEnabled():return
        if QMessageBox.question(self,'インポート確認','表示した内容を取り込みますか？\n重複交信は既存ログを残し、入力側にだけある既知のQSL情報をRMKSへ補完します。\n既存ログは先にバックアップします。',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:return
        try:
            report,saved=commit(self.repo,self.plan,self.sections.isChecked(),self.conversions.isChecked())
            message=f'{len(saved)}ファイルを更新しました。\n結果: {report}'
        except ImportFailure as e:
            message=str(e)+'\n結果: '+str(e.report)
        except (StorageError,OSError) as e:
            self.status.setText(str(e));self.plan=None;self.save_button.setEnabled(False);return
        self.plan=None;self.save_button.setEnabled(False);self.logs_changed.emit();self.status.setText(message)
