"""Edit optional eligibility and timing on existing event categories."""
from copy import deepcopy
from PySide6.QtCore import QSignalBlocker
from PySide6.QtWidgets import (QVBoxLayout,QFormLayout,QHBoxLayout,QComboBox,
    QLabel,QCheckBox,QSpinBox,QLineEdit)
from window_geometry import SafeDialog
from search_ui import button
from contest_timing import validate_timing

class CategoryRulesDialog(SafeDialog):
    def __init__(self,event,parent=None):
        super().__init__(parent);self.value=deepcopy(event);self.current=-1;self.eligible=None
        self.setWindowTitle('部門別の交信相手条件・時間制限');self.resize(820,640)
        v=QVBoxLayout(self);f=QFormLayout();v.addLayout(f);self.category=QComboBox()
        for c in event['categories']:self.category.addItem(c['name']+' ['+c['id']+']')
        f.addRow('設定する部門',self.category)
        self.eligible_label=QLabel();self.eligible_label.setWordWrap(True);self.eligible_label.setMaximumHeight(95)
        f.addRow('交信相手条件',self.eligible_label);f.addRow(button('交信相手条件を編集…',self.edit_eligible))
        self.operating=QCheckBox('運用時間を制限する');f.addRow(self.operating)
        self.max_minutes=QSpinBox();self.max_minutes.setRange(1,100000);self.max_minutes.setSuffix(' 分')
        self.min_off=QSpinBox();self.min_off.setRange(0,100000);self.min_off.setSuffix(' 分')
        f.addRow('運用時間の上限',self.max_minutes);f.addRow('休止として除く最低時間',self.min_off)
        self.band_change=QCheckBox('バンド変更を制限する');f.addRow(self.band_change)
        self.kind=QComboBox();self.kind.addItem('変更後に一定時間留まる','stay');self.kind.addItem('正時からの毎時変更回数','hourly');f.addRow('制限方式',self.kind)
        self.limit=QSpinBox();self.limit.setRange(0,100000);f.addRow('最低滞在分数／毎時最大回数',self.limit)
        self.ids=QLineEdit();self.ids.setPlaceholderText('例: 1,2 ／ 全体で共通なら空欄');f.addRow('送信系列ID（カンマ区切り）',self.ids)
        self.action=QComboBox();self.action.addItem('確認が済むまで出力を停止','block');self.action.addItem('該当交信を0点・マルチ対象外','exclude');f.addRow('違反候補の扱い',self.action)
        hint=QLabel('運用時間・バンド履歴は開催時間内の対象ログ全体で確認します（種目外バンドや重複も含む）。\n実運用の区間と系列は提出作業時に入力します。同時送信や設備配置はログだけでは確認できません。\n0点処理では違反行によって適法な滞在開始時刻を進めません。適用する規約を確認してください。')
        hint.setWordWrap(True);v.addWidget(hint)
        self.status=QLabel();self.status.setWordWrap(True);v.addWidget(self.status);v.addStretch()
        row=QHBoxLayout();row.addStretch();row.addWidget(button('反映',self.apply));row.addWidget(button('キャンセル',self.reject));v.addLayout(row)
        self.category.currentIndexChanged.connect(self.change_category)
        self.operating.toggled.connect(self.enabled);self.band_change.toggled.connect(self.enabled);self.kind.currentIndexChanged.connect(self.enabled)
        self.load(0)
    def enabled(self):
        for w in (self.max_minutes,self.min_off):w.setEnabled(self.operating.isChecked())
        for w in (self.kind,self.limit,self.ids,self.action):w.setEnabled(self.band_change.isChecked())
        if self.kind.currentData()=='hourly':self.action.setCurrentIndex(0);self.action.setEnabled(False)
        self.limit.setMinimum(1 if self.kind.currentData()=='stay' else 0)
    def load(self,index):
        from contest_rule_ui import describe
        self.current=index;c=self.value['categories'][index];self.eligible=deepcopy(c.get('eligible'))
        self.eligible_label.setText(describe(self.eligible or {'all':[]}));self.eligible_label.setToolTip(self.eligible_label.text())
        t=c.get('timing',{});o=t.get('operating',{});b=t.get('band_change',{})
        self.operating.setChecked(bool(o));self.max_minutes.setValue(o.get('max_minutes',2160));self.min_off.setValue(o.get('min_off_minutes',60))
        self.band_change.setChecked(bool(b));self.kind.setCurrentIndex(self.kind.findData(b.get('kind','stay')))
        self.limit.setValue(b.get('min_minutes',b.get('max_changes',10)));self.ids.setText(','.join(b.get('tx_ids',[])))
        self.action.setCurrentIndex(self.action.findData(b.get('on_violation','block')));self.enabled()
    def collect(self):
        c=self.value['categories'][self.current];t={}
        if self.operating.isChecked():t['operating']=dict(max_minutes=self.max_minutes.value(),min_off_minutes=self.min_off.value())
        if self.band_change.isChecked():
            b=dict(kind=self.kind.currentData(),tx_ids=[x.strip() for x in self.ids.text().split(',')] if self.ids.text().strip() else [],on_violation=self.action.currentData())
            b['min_minutes' if b['kind']=='stay' else 'max_changes']=self.limit.value();t['band_change']=b
        if t:validate_timing(t)
        if self.eligible is not None:c['eligible']=deepcopy(self.eligible)
        if t:c['timing']=t
        else:c.pop('timing',None)
    def change_category(self,index):
        try:self.collect();self.load(index);self.status.clear()
        except ValueError as ex:
            self.status.setText(str(ex))
            with QSignalBlocker(self.category):self.category.setCurrentIndex(self.current)
    def edit_eligible(self):
        from contest_rule_ui import ConditionDialog,describe
        d=ConditionDialog(self.eligible or {'all':[]},self)
        if d.exec()==d.Accepted:self.eligible=d.result_value;self.eligible_label.setText(describe(self.eligible));self.eligible_label.setToolTip(self.eligible_label.text())
    def apply(self):
        from contest_event import validate_event
        try:self.collect();validate_event(self.value);self.accept()
        except ValueError as ex:self.status.setText(str(ex))
