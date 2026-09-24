from copy import deepcopy
import unicodedata
from PySide6.QtWidgets import QWidget,QVBoxLayout,QFormLayout,QLabel,QLineEdit,QSpinBox,QPlainTextEdit,QTableWidget,QTableWidgetItem,QDoubleSpinBox,QComboBox
from PySide6.QtCore import Qt
from contest_qualification import operators

class QualificationPane(QWidget):
    def __init__(self,context,parent=None):
        super().__init__(parent);self.context=deepcopy(context);self.category={};v=QVBoxLayout(self)
        self.note=QLabel();self.note.setWordWrap(True);v.addWidget(self.note);self.form=QFormLayout();v.addLayout(self.form)
        self.age=QSpinBox();self.age.setRange(-1,150);self.age.setSpecialValueText('未入力');self.age.setSuffix(' 歳');self.age.setValue(context.get('age',-1))
        self.license=QLineEdit(context.get('licensedate',''));self.license.setPlaceholderText('YYYY-MM-DD（最初の局免許年月日）')
        self.ops=QPlainTextEdit();self.ops.setPlaceholderText('コール又は氏名 / 年齢\nJA1AAA / 18\n試験 太郎 / 17');self.ops.setMaximumHeight(140)
        self.ops.setPlainText('\n'.join(f'{x["name"]} / {x["age"]}' for x in context.get('operators',[])))
        self.form.addRow('実運用者の運用時年齢',self.age);self.form.addRow('最初の局免許年月日',self.license);self.form.addRow('全運用者と運用時年齢',self.ops)
        self.basis=QComboBox();self.basis.addItem('選択してください','');self.basis.addItem('YL（女性）','yl');self.basis.addItem('規約年齢未満','young');self.basis.setCurrentIndex(max(0,self.basis.findData(context.get('qualification_basis',''))))
        self.birth=QLineEdit(context.get('birthdate',''));self.birth.setPlaceholderText('YYYY-MM-DD（若年資格で参加する場合）');self.form.addRow('YL／若年の参加資格',self.basis);self.form.addRow('実運用者の生年月日',self.birth)
        self.powers=QTableWidget(0,3);self.powers.setHorizontalHeaderLabels(['バンド MHz','規約上限 W','実運用の最大 W']);self.powers.setMaximumHeight(235);v.addWidget(self.powers,1)
        self.power_note=QLabel('全体の最大電力が各バンドの上限以下なら、バンド別入力は省略できます。\nHF10W／50MHz20Wのように上限が違い、全体では10Wを超えた場合に入力します。');self.power_note.setWordWrap(True);v.addWidget(self.power_note);v.addStretch()
        self.power_values=deepcopy(context.get('power_by_band',{}));self.widgets={}
    def set_category(self,c):
        for band,w in self.widgets.items():
            if w.value()>0:self.power_values[band]=w.value()
            else:self.power_values.pop(band,None)
        self.category=c or {};q=self.category.get('qualification',{});caps=self.category.get('power_by_band',{})
        self.form.setRowVisible(self.age,'min_age' in q or 'max_age' in q);self.form.setRowVisible(self.license,'license_since' in q);self.form.setRowVisible(self.ops,'operators_max_age' in q)
        self.form.setRowVisible(self.basis,'yl_or_younger_than' in q);self.form.setRowVisible(self.birth,'yl_or_younger_than' in q)
        lines=[]
        if 'yl_or_younger_than' in q:lines.append(f'YL、又は{q["reference_date"]}時点で{q["yl_or_younger_than"]}歳未満。資格は意見欄へ記載します。')
        if 'min_age' in q:lines.append(f'実運用者が{q["min_age"]}歳以上。')
        if 'max_age' in q:lines.append(f'実運用者が{q["max_age"]}歳以下。')
        if 'license_since' in q:
            self.form.labelForField(self.license).setText(q.get('license_label','初回局免許年月日'));self.license.setPlaceholderText('YYYY-MM-DD（'+q.get('license_label','初回局免許年月日')+'）')
        if 'license_since' in q:lines.append(f'{q.get("license_label","初回局免許年月日")}: {q["license_since"]}～{q["license_until"]}（両端を含む）。')
        if 'operators_max_age' in q:lines.append(f'全運用者が{q["operators_max_age"]}歳以下。1行に1名ずつ入力してください。')
        self.note.setText('\n'.join(lines) if lines else 'この部門には年齢・開局日の追加条件はありません。')
        self.powers.setRowCount(len(caps));self.widgets={}
        for row,(band,limit) in enumerate(caps.items()):
            for col,text in enumerate((band,str(limit))):
                item=QTableWidgetItem(text);item.setFlags(item.flags()&~Qt.ItemIsEditable);self.powers.setItem(row,col,item)
            w=QDoubleSpinBox();w.setRange(0,100000);w.setDecimals(3);w.setSpecialValueText('未入力');w.setValue(self.power_values.get(band,0));self.powers.setCellWidget(row,2,w);self.widgets[band]=w
        self.powers.setVisible(bool(caps));self.power_note.setVisible(bool(caps))
    def values(self):
        result={};q=self.category.get('qualification',{})
        if 'yl_or_younger_than' in q:result.update(qualification_basis=self.basis.currentData(),birthdate=unicodedata.normalize('NFKC',self.birth.text()).strip())
        if 'min_age' in q or 'max_age' in q:result['age']=self.age.value()
        if 'license_since' in q:result['licensedate']=unicodedata.normalize('NFKC',self.license.text()).strip()
        if 'operators_max_age' in q:result['operators']=operators(self.ops.toPlainText())
        for band,w in self.widgets.items():
            if w.value()>0:self.power_values[band]=w.value()
            else:self.power_values.pop(band,None)
        result['power_by_band']=deepcopy(self.power_values)
        return result
