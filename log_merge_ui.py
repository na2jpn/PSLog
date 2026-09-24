"""Yellow edit-family dialog for safe PSLog log-file consolidation."""
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (QVBoxLayout,QHBoxLayout,QFormLayout,QLineEdit,QPushButton,
    QLabel,QTextEdit,QFileDialog,QMessageBox,QGroupBox)

from storage import StorageError, ExternalChange, VERSION
from log_merge import check, execute
from window_tint import apply_window_tint
from window_geometry import SafeDialog as QDialog


def button(text, slot):
    b=QPushButton(text);b.setAutoDefault(False);b.clicked.connect(slot);return b


class LogMergeDialog(QDialog):
    logs_changed=Signal()
    def __init__(self,repo,parent=None):
        super().__init__(parent);self.repo=repo;self.plan=None
        self.setWindowTitle(f'PSLog {VERSION} — ログファイル統合');self.resize(860,650);apply_window_tint(self,'edit')
        outer=QVBoxLayout(self)

        guide=QGroupBox('ログファイル統合')
        gl=QVBoxLayout(guide)
        note=QLabel(
            '同じ年・同じ自局コールサイン系統のPSLogログ2ファイルを1つに統合します。\n'
            '統合先は残り、統合元は成功後にバックアップして削除します。\n'
            '必ず「ファイルチェック」に合格してから実行します。'
        );note.setWordWrap(True);gl.addWidget(note);outer.addWidget(guide)

        form=QFormLayout();outer.addLayout(form)
        self.target=QLineEdit();self.target.setReadOnly(True);self.target.setPlaceholderText('統合後に残すログファイル')
        tr=QHBoxLayout();tr.addWidget(self.target,1);tr.addWidget(button('選択…',lambda:self.choose(self.target,'統合先ログを選択')))
        form.addRow('統合先ログ（残す）',tr)
        self.source=QLineEdit();self.source.setReadOnly(True);self.source.setPlaceholderText('統合後に削除するログファイル')
        sr=QHBoxLayout();sr.addWidget(self.source,1);sr.addWidget(button('選択…',lambda:self.choose(self.source,'統合元ログを選択')))
        form.addRow('統合元ログ（削除）',sr)

        filename_note=QLabel('対象例: 2026_JX1XXX_.txt と 2026_JX1XXX-1_.txt。付与文字が異なる同一コール系統のログもチェック対象にできます。')
        filename_note.setWordWrap(True);outer.addWidget(filename_note)

        check_row=QHBoxLayout();self.check_button=button('ファイルチェック',self.run_check);check_row.addWidget(self.check_button);check_row.addStretch();outer.addLayout(check_row)
        self.result=QTextEdit();self.result.setReadOnly(True);self.result.setPlaceholderText('ファイルチェック結果をここに表示します。');outer.addWidget(self.result,1)
        self.status=QLabel('統合先と統合元を選択し、「ファイルチェック」を実行してください。');self.status.setWordWrap(True);outer.addWidget(self.status)

        actions=QHBoxLayout();actions.addStretch();self.execute_button=button('統合を実行',self.run_execute);self.execute_button.setEnabled(False)
        actions.addWidget(self.execute_button);actions.addWidget(button('閉じる',self.reject));outer.addLayout(actions)

    def invalidate(self):
        self.plan=None;self.execute_button.setEnabled(False)
        self.status.setText('ファイルを選び直しました。「ファイルチェック」を再実行してください。')

    def choose(self,field,title):
        path,_=QFileDialog.getOpenFileName(self,title,str(self.repo.book),'PSLogログ (*.txt)')
        if not path:return
        field.setText(str(Path(path).resolve()));self.invalidate()

    def run_check(self):
        self.plan=None;self.execute_button.setEnabled(False);self.result.clear()
        if not self.target.text().strip() or not self.source.text().strip():
            self.status.setStyleSheet('color:#b32020;font-weight:bold');self.status.setText('統合先と統合元の2ファイルを選択してください。');return
        try:plan=check(self.repo,self.target.text(),self.source.text())
        except (StorageError,ExternalChange,OSError,ValueError) as e:
            self.status.setStyleSheet('color:#b32020;font-weight:bold');self.status.setText('ファイルチェックで問題が見つかりました。統合は実行できません。')
            self.result.setPlainText(str(e));return
        self.plan=plan;self.execute_button.setEnabled(True);self.status.setStyleSheet('color:#176b34;font-weight:bold');self.status.setText('ファイルチェックOKです。「統合を実行」が使用できます。')
        lines=[
            '【ファイルチェック OK】',
            f'年: {plan.target_year}',
            f'統合先コール系統: {plan.target_call}',
            f'統合元コール系統: {plan.source_call}',
            '',
            f'統合先: {plan.target_records:,}交信',
            f'統合元: {plan.source_records:,}交信',
            f'重複スキップ（統合先優先）: {plan.duplicate_skipped:,}交信',
            f'新規追加: {plan.added_records:,}交信',
            f'統合後: {plan.merged_records:,}交信',
            '',
            '統合後はDATE・TIME順に並べ替えます。',
            '実行直前に両ファイルを bak/logbook_bak へバックアップします。',
            '統合先の保存・再検査に成功した後だけ統合元を削除します。',
        ]
        if plan.warnings:lines+=['','【注意】',*plan.warnings]
        self.result.setPlainText('\n'.join(lines))

    def run_execute(self):
        if self.plan is None:
            self.execute_button.setEnabled(False);self.status.setText('先に「ファイルチェック」を実行してください。');return
        text=(f'統合先: {self.plan.target.name}\n統合元: {self.plan.source.name}\n\n'
              f'新規追加 {self.plan.added_records:,}交信 / 重複スキップ {self.plan.duplicate_skipped:,}交信\n'
              f'統合後 {self.plan.merged_records:,}交信\n\n'
              '両方をバックアップした後、統合先を書き換え、成功時に統合元を削除します。\n実行しますか？')
        if QMessageBox.question(self,'ログファイル統合の最終確認',text,QMessageBox.Yes|QMessageBox.No,QMessageBox.No)!=QMessageBox.Yes:return
        try:result=execute(self.repo,self.plan)
        except (StorageError,ExternalChange,OSError,ValueError) as e:
            self.execute_button.setEnabled(False);self.plan=None;self.status.setStyleSheet('color:#b32020;font-weight:bold');self.status.setText('統合を完了できませんでした。再チェックしてください。')
            self.result.append('\n\n【実行エラー】\n'+str(e));return
        self.execute_button.setEnabled(False);self.plan=None;self.status.setStyleSheet('color:#176b34;font-weight:bold');self.status.setText('ログファイル統合が完了しました。')
        self.result.append(
            f'\n\n【統合完了】\n保存先: {result.target}\n削除した統合元: {result.removed_source}\n'
            f'統合先バックアップ: {result.target_backup}\n統合元バックアップ: {result.source_backup}'
        )
        self.logs_changed.emit()
        QMessageBox.information(self,'ログファイル統合','ログファイル統合が完了しました。\n\n'+str(result.target))
