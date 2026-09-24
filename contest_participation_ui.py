from PySide6.QtWidgets import QWidget,QVBoxLayout,QLabel,QPlainTextEdit,QLineEdit
from contest_participation import parse

class ParticipationPane(QWidget):
    def __init__(self,ctx):
        super().__init__();v=QVBoxLayout(self);self.category={}
        self.note=QLabel();self.note.setWordWrap(True);v.addWidget(self.note)
        self.ops=QPlainTextEdit();self.ops.setMaximumHeight(220);self.ops.setPlaceholderText('コール又は氏名 / 年齢 / 交信数 / 続柄\nJA1AAA / 20 / 80 / 子\nJA1BBB / 50 / 20 / 父')
        self.ops.setPlainText('\n'.join(f'{o["name"]} / {o["age"]} / {o["qsos"]}'+(' / '+o['role'] if o.get('role') else '') for o in ctx.get('qso_operators',[])));v.addWidget(self.ops)
        self.label=QLabel('子のコールサイン（PMMK）');v.addWidget(self.label);self.child=QLineEdit(ctx.get('child_call',''));v.addWidget(self.child)
        self.summary=QLabel();self.summary.setWordWrap(True);v.addWidget(self.summary);v.addStretch();self.ops.textChanged.connect(self.summarize)
    def set_category(self,c):
        self.category=c or {};s=self.category.get('participation');self.ops.setVisible(bool(s));self.label.setVisible(bool(s and s['family_pair']));self.child.setVisible(bool(s and s['family_pair']))
        self.note.setText(f'{s["max_age"]}歳以下の担当交信が全体の{s["min_percent"]}％以上必要です。人数比ではありません。\n開催中の全交信（重複・無得点を含む）の担当数を記録から入力します。続柄はPMMKだけ子／父／母／祖父／祖母を指定。' if s else 'この部門に担当交信割合の条件はありません。');
        if s and s.get('manual_claim'):self.note.setText(f'{s["max_age"]}歳以下が{s["min_percent"]}％以上という規約です。担当数は申告値を入力してください。集計方法と参加資格は本人判断で、原ログ件数との一致を強制しません。')
        self.summarize()
    def summarize(self):
        s=self.category.get('participation')
        if not s:self.summary.clear();return
        try:
            ops=parse(self.ops.toPlainText());total=sum(o['qsos'] for o in ops);young=sum(o['qsos'] for o in ops if o['age']<=s['max_age']);self.summary.setText(f'担当数合計: {total}件／若年者担当: {young}件'+(f'（{young/total*100:.1f}％）' if total else '')+('\n参考計算。申告値で提出し、参加資格は本人判断です。' if s.get('manual_claim') else '\nログ件数との一致は採点時に確認します。'))
        except ValueError as ex:self.summary.setText(str(ex))
    def values(self):
        if not self.category.get('participation'):return {}
        return dict(qso_operators=parse(self.ops.toPlainText()),child_call=self.child.text().strip().upper())
