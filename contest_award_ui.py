from PySide6.QtWidgets import QScrollArea,QWidget,QVBoxLayout,QCheckBox,QLabel
from contest_awards import candidates
from contest import entries

class AwardPane(QScrollArea):
    def __init__(self,changed,parent=None):
        super().__init__(parent);self.changed=changed;self.checks={};self.scope=None
        self.setWidgetResizable(True);self.setMaximumHeight(180);self.setMinimumHeight(110)
        self.setVisible(False)
    def requests(self):return [ident for ident,w in self.checks.items() if w.isChecked()]
    def refresh(self,rule,selection,draft,context,scope):
        current=(rule['id'],rule['year'],scope,context.get('category'),context.get('submission_mode'))
        previous=set(self.requests()) if current==self.scope else set();self.scope=current;self.checks={}
        old=self.takeWidget()
        if old:old.deleteLater()
        self.setVisible(bool(rule.get('event',{}).get('awards')))
        if not rule.get('event',{}).get('awards'):return
        body=QWidget();layout=QVBoxLayout(body);self.setWidget(body)
        note=QLabel('大会内アワード（任意）\n選択ログの全対象バンドで判定。希望した賞だけ意見欄へ申請文を追加します。');note.setWordWrap(True);layout.addWidget(note)
        results=candidates(rule,entries(selection,draft),context)
        for a in results:
            count=' + '.join(f'{n}/{m}' for n,m in zip(a['counts'],a['required']))
            w=QCheckBox(a['name']+' — '+count+(' 達成候補' if a['eligible'] else '未達・未確認'));w.setEnabled(a['eligible']);w.setChecked(a['eligible'] and a['id'] in previous);w.toggled.connect(self.changed);layout.addWidget(w);self.checks[a['id']]=w
        if results and results[0]['problems']:
            label=QLabel('判定できません: '+results[0]['problems'][0]);label.setWordWrap(True);layout.addWidget(label)
