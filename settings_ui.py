from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QTabWidget,QWidget,QCheckBox,QLabel,QComboBox,QFormLayout,QLineEdit
from preferences import DEFAULTS,validate
from search_ui import button
from storage import StorageError, VERSION

from window_geometry import SafeDialog as QDialog

class SettingsDialog(QDialog):
    def __init__(self,values,apply,parent=None,repo=None):
        super().__init__(parent);self.values=validate(values);self.apply_callback=apply;self.repo=repo
        self.setWindowTitle(f'PSLog {VERSION} — 設定');self.resize(760,540)
        outer=QVBoxLayout(self);tabs=QTabWidget();outer.addWidget(tabs,1);self.checks={}
        input_page=QWidget();form=QVBoxLayout(input_page);tabs.addTab(input_page,'入力補助')
        for key,label in [('keep_band','新しい交信でもBANDを維持する'),('keep_mode','新しい交信でもMODEを維持する'),('auto_rst','モードに応じてRSTを自動入力する'),('confirm_record','記録前の確認を表示する'),('location_assist','所在地の入力補助を使う')]:
            cb=QCheckBox(label);cb.setChecked(self.values[key]);self.checks[key]=cb;form.addWidget(cb)
        text=QLabel('SSB / FM / AM：59　　CW / RTTY：599\nSSTV：595　　FT8 / FT4 / FT2：-01　　FreeDV：+00\nサブモードを含む表記にも適用します。\n\nコールサイン・MY QTHは直近の入力値を引き継ぎます。\n所在地は確認済みの表記と、ログ由来の未確認候補を区別します。');text.setWordWrap(True);form.addWidget(text);form.addStretch()
        backup_page=QWidget();form=QFormLayout(backup_page);form.setVerticalSpacing(9);tabs.addTab(backup_page,'バックアップ')
        text=QLabel('自動バックアップ：有効\nログを書き換える前、編集・削除・復元の前、変更がある状態で終了するときに、元のログを自動で保護します。\n前回と内容が同じ場合は、同じバックアップを重複して作成しません。');text.setWordWrap(True);form.addRow(text)
        self.keep=QComboBox();self.keep.addItems(['10','30','60','100']);self.keep.setCurrentText(str(self.values['backup_keep']))
        keep_row=QWidget();kr=QHBoxLayout(keep_row);kr.setContentsMargins(0,0,0,0);kr.addWidget(self.keep);kr.addWidget(QLabel('件'));kr.addStretch();form.addRow('バックアップ保持数（ログファイルごと）',keep_row)
        keep_help=QLabel('各ログファイルについて、古い世代を含め最大この件数まで保持します。保持数を減らしても、この画面を保存しただけでは削除せず、そのログを次回正常に保存・整理したときに新しい上限を適用します。');keep_help.setWordWrap(True);keep_help.setStyleSheet('color:#55636c;');form.addRow('',keep_help)
        if self.repo is not None:
            path=QLineEdit(str(self.repo.bak));path.setReadOnly(True);path.setToolTip(str(self.repo.bak));form.addRow('自動バックアップ保存先',path)
            files=sorted(self.repo.bak.glob('*.bak')) if self.repo.bak.exists() else []
            sources={f.name.split('.',1)[0] for f in files}
            latest='なし'
            if files:
                try: latest=max(files,key=lambda x:x.stat().st_mtime).stat().st_mtime
                except OSError: latest=None
                if latest is not None:
                    from datetime import datetime
                    latest=datetime.fromtimestamp(latest).strftime('%Y/%m/%d %H:%M:%S')
                else: latest='確認できません'
            current=QLabel(f'現在の自動ログバックアップ：{len(files)}件（{len(sources)}ログ）\n最新バックアップ：{latest}')
            current.setWordWrap(True);form.addRow('現在の状態',current)
        cb=QCheckBox('月が替わったら全体バックアップを案内する');cb.setChecked(self.values['monthly_backup']);self.checks['monthly_backup']=cb;form.addRow(cb)
        text=QLabel('月替わりの案内は、自動で全体バックアップを作る機能ではありません。\n案内から「今すぐ作成」を選ぶと、logbook と config を1つのZIPにまとめ、別ドライブやUSBメモリーなど、任意の場所へ保存できます。');text.setWordWrap(True);form.addRow(text)
        self.error=QLabel();self.error.setWordWrap(True);outer.addWidget(self.error)
        row=QHBoxLayout();row.addStretch();row.addWidget(button('保存',self.save));row.addWidget(button('キャンセル',self.reject));outer.addLayout(row)
    def save(self):
        values=dict(self.values);values.update({k:cb.isChecked() for k,cb in self.checks.items()});values['backup_keep']=int(self.keep.currentText())
        try:self.apply_callback(validate(values))
        except (ValueError,StorageError,OSError) as e:self.error.setText(str(e));return
        self.accept()
