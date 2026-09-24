from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout,QHBoxLayout,QLineEdit,QLabel,QTableWidget,QTableWidgetItem,QAbstractItemView,QComboBox,QCheckBox,QMessageBox
from window_geometry import SafeDialog as QDialog
from search_ui import button
from locations import load,find,candidates
from location_overrides import Overrides,qth as validate_qth
from storage import StorageError

class LocationDialog(QDialog):
    def __init__(self,root,query='',parent=None,remember_default=False):
        super().__init__(parent);self.root=root;self.remember_default=bool(remember_default);self.overrides=Overrides(root);self.data=load(root);self.overrides.snapshot.check(self.overrides.path);self.rows=[];self.result_value=None
        self.setWindowTitle('所在地を検索');self.resize(950,650);layout=QVBoxLayout(self)
        self.search=QLineEdit(query);self.search.setPlaceholderText('JCC/JCG番号・日本語地名・ローマ字候補');layout.addWidget(self.search)
        self.table=QTableWidget(0,3);self.table.setHorizontalHeaderLabels(['所在地','元コード','ローマ字確認']);self.table.setColumnWidth(0,430);self.table.setColumnWidth(1,150);self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows);self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection);self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers);layout.addWidget(self.table,1)
        self.info=QLabel();self.info.setWordWrap(True);layout.addWidget(self.info)
        self.qth=QComboBox();self.qth.setEditable(True);layout.addWidget(self.qth)
        # Fast QSO entry: reference candidates are informational, not a gate.
        # Keep the old attribute hidden for compatibility, but do not require it.
        self.confirm=QCheckBox('未確認の表記・町村の対応を確認した');self.confirm.hide()
        self.remember=QCheckBox('この所在地の表記を次回の入力補助にも保存する');self.remember.setChecked(self.remember_default);layout.addWidget(self.remember)
        self.forget_button=button('この所在地の保存した表記を解除',self.forget);layout.addWidget(self.forget_button)
        self.status=QLabel('JCGの郡番号だけで町村は確定できません。gunを含む表記を維持します。');self.status.setWordWrap(True);layout.addWidget(self.status)
        row=QHBoxLayout();row.addStretch();self.apply_button=button('所在地を反映',self.apply);row.addWidget(self.apply_button);row.addWidget(button('キャンセル',self.reject));layout.addLayout(row)
        self.search.textChanged.connect(self.fill);self.table.itemSelectionChanged.connect(self.select);self.qth.currentTextChanged.connect(self.changed);self.confirm.toggled.connect(self.enabled);self.fill()
        if self.data.get('override_notices'):self.status.setText('\n'.join(self.data['override_notices']))
    def fill(self):
        self.table.setRowCount(0);self.rows=find(self.data,self.search.text())
        for r in self.rows:
            i=self.table.rowCount();self.table.insertRow(i)
            for j,v in enumerate([r['name'],r['kind']+' '+r['source_code'],r.get('qth_source','確認済み') if r['verified_qth'] else ('参照候補あり・要確認' if r.get('reference_qth') else '資料要確認')]):self.table.setItem(i,j,QTableWidgetItem(v))
        self.select()
    def selected(self):
        i=self.table.currentRow();return self.rows[i] if 0<=i<len(self.rows) else None
    def select(self):
        self.qth.clear();self.remember.setChecked(self.remember_default);r=self.selected();self.forget_button.setEnabled(bool(r and r.get('qth_source')=='ユーザー確認済み'))
        if r:
            values=candidates(self.data,r)
            for text,label in values:self.qth.addItem(text,label)
            # Selecting the place also selects the best available spelling:
            # verified/user-confirmed first, otherwise the reference/log candidate.
            if values:self.qth.setCurrentIndex(0)
            else:self.qth.setCurrentText('')
            self.status.setText(r.get('reference_notice') or r.get('reference_source') or '表記と交信当時の所在地を確認してください。')
            self.info.setText(r['name']+' ／ 保存する番号: '+r['kind']+' '+r['code']+'\n候補をそのまま反映できます。必要ならローマ字表記を手入力で修正してください。')
        else:self.info.setText('所在地を選択してください。')
        self.enabled()
    def changed(self):
        self.qth.setToolTip(str(self.qth.currentData() or '手入力'))
        self.enabled()
    def enabled(self):
        r=self.selected();qth=self.qth.currentText().strip()
        self.apply_button.setEnabled(bool(r and qth))
    def apply(self):
        r=self.selected();qth=self.qth.currentText().strip()
        if not self.apply_button.isEnabled():return
        try:
            qth=validate_qth(qth)
            if self.remember.isChecked():self.overrides.remember(r,qth)
        except (ValueError,OSError,StorageError) as e:self.status.setText(str(e));return
        self.result_value=(qth,r['code']);self.accept()
    def forget(self):
        r=self.selected()
        if not r or r.get('qth_source')!='ユーザー確認済み':return
        if QMessageBox.question(self,'保存した表記の解除','この所在地の保存した表記を解除しますか？元ログの所在地は変更しません。')!=QMessageBox.Yes:return
        try:self.overrides.forget(r);self.data=load(self.root);self.fill();self.status.setText('保存した表記を解除しました。変更前の設定は履歴に残っています。')
        except (ValueError,OSError,StorageError) as e:self.status.setText(str(e))
