from copy import deepcopy
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QVBoxLayout,QHBoxLayout,QFormLayout,QWidget,QSplitter,QLineEdit,QLabel,QComboBox,QCheckBox,QListWidget,QListWidgetItem,QTabWidget,QPlainTextEdit,QDoubleSpinBox,QSpinBox,QTableWidget,QTableWidgetItem,QTreeWidget,QTreeWidgetItem,QMessageBox,QAbstractItemView)
from window_geometry import SafeDialog
from search_ui import button
from contest_rules import RuleStore,default_rule,validate,loads,dumps,condition,FIELDS,OPS,rule_sort_key,management_rule_label
from storage import StorageError
from rule_source_ui import source_label,source_text

FIELD_LABELS=['モード','バンド','相手コール','受信ナンバー','プリフィックス（別途指定）','ナンバー文字数','数字群の桁数','地域（別途指定）','国・地域名（確認済み作業値）','大陸（AF/AN/AS/EU/NA/OC/SA）']
OP_LABELS=['等しい','等しくない','先頭一致','候補のいずれか（カンマ区切り）','以上','以下']

def describe(c):
    if 'all' in c or 'any' in c:
        k=next(iter(c));items=c[k]
        if not items:return '全件' if k=='all' else '該当なし'
        return (' かつ ' if k=='all' else ' または ').join('（'+describe(x)+'）' for x in items)
    return f"{FIELD_LABELS[FIELDS.index(c['field'])]} {OP_LABELS[OPS.index(c['op'])]} {c['value']}"

def combo(labels):
    w=QComboBox();w.addItems(labels);return w
def spin(value=0,decimal=False):
    w=QDoubleSpinBox() if decimal else QSpinBox();w.setRange(0,100000000)
    if decimal:w.setDecimals(6)
    w.setValue(value);return w

class ConditionDialog(SafeDialog):
    def __init__(self,value,parent=None):
        super().__init__(parent);self.result_value=None;self.setWindowTitle('条件を編集 — AND / OR');self.resize(780,620);box=QVBoxLayout(self)
        box.addWidget(QLabel('グループを選んで条件を追加します。空のANDは全件、空のORは該当なしです。'))
        self.tree=QTreeWidget();self.tree.setHeaderLabels(['条件']);box.addWidget(self.tree,1)
        def add(c,parent):
            if 'all' in c or 'any' in c:
                k=next(iter(c));item=QTreeWidgetItem(parent,['すべて一致（AND）' if k=='all' else 'いずれか一致（OR）']);item.setData(0,Qt.UserRole,k)
                for child in c[k]:add(child,item)
            else:
                item=QTreeWidgetItem(parent);item.setData(0,Qt.UserRole,deepcopy(c));self.label(item)
            item.setExpanded(True);return item
        root=add(value,self.tree);self.tree.setCurrentItem(root)
        row=QHBoxLayout();row.addWidget(button('ANDグループ追加',lambda:self.group('all')));row.addWidget(button('ORグループ追加',lambda:self.group('any')));row.addWidget(button('選択条件を削除',self.remove));box.addLayout(row)
        form=QFormLayout();self.field=combo(FIELD_LABELS);self.op=combo(OP_LABELS);self.value=QLineEdit();form.addRow('項目',self.field);form.addRow('比較',self.op);form.addRow('値',self.value);box.addLayout(form)
        row=QHBoxLayout();row.addWidget(button('条件を追加',self.add_leaf));row.addWidget(button('選択条件を変更',self.update_leaf));box.addLayout(row)
        self.status=QLabel();self.status.setWordWrap(True);box.addWidget(self.status);row=QHBoxLayout();row.addStretch();row.addWidget(button('反映',self.apply));row.addWidget(button('キャンセル',self.reject));box.addLayout(row);self.tree.currentItemChanged.connect(self.selected)
    def label(self,item):
        c=item.data(0,Qt.UserRole);item.setText(0,f"{FIELD_LABELS[FIELDS.index(c['field'])]} / {OP_LABELS[OPS.index(c['op'])]} / {c['value']}")
    def selected(self,item,*args):
        if item and isinstance(item.data(0,Qt.UserRole),dict):
            c=item.data(0,Qt.UserRole);self.field.setCurrentIndex(FIELDS.index(c['field']));self.op.setCurrentIndex(OPS.index(c['op']));self.value.setText(str(c['value']))
    def parent_group(self):
        item=self.tree.currentItem() or self.tree.topLevelItem(0)
        if isinstance(item.data(0,Qt.UserRole),dict):item=item.parent()
        if item is None:raise ValueError('最上位の単独条件には追加できません。JSONでANDグループにしてください。')
        return item
    def group(self,kind):
        try:
            item=QTreeWidgetItem(self.parent_group(),['すべて一致（AND）' if kind=='all' else 'いずれか一致（OR）']);item.setData(0,Qt.UserRole,kind);self.tree.expandAll()
        except ValueError as e:self.status.setText(str(e))
    def leaf(self):
        f=FIELDS[self.field.currentIndex()];value=self.value.text()
        if f in ('length','digits_length'):
            try:value=int(value)
            except ValueError:raise ValueError('桁数は整数を入力してください。')
        c={'field':f,'op':OPS[self.op.currentIndex()],'value':value};condition(c);return c
    def add_leaf(self):
        try:
            c=self.leaf();item=QTreeWidgetItem(self.parent_group());item.setData(0,Qt.UserRole,c);self.label(item);self.tree.expandAll()
        except ValueError as e:self.status.setText(str(e))
    def update_leaf(self):
        try:
            c=self.leaf();item=self.tree.currentItem()
            if item is None or not isinstance(item.data(0,Qt.UserRole),dict):raise ValueError('変更する単独条件を選んでください。')
            item.setData(0,Qt.UserRole,c);self.label(item)
        except ValueError as e:self.status.setText(str(e))
    def remove(self):
        item=self.tree.currentItem()
        if item and item.parent():item.parent().removeChild(item)
    def apply(self):
        def read(item):
            c=item.data(0,Qt.UserRole)
            return c if isinstance(c,dict) else {c:[read(item.child(i)) for i in range(item.childCount())]}
        try:self.result_value=read(self.tree.topLevelItem(0));condition(self.result_value);self.accept()
        except ValueError as e:self.status.setText(str(e))

class RuleEditor(SafeDialog):
    def __init__(self,store,rule=None,path=None,snapshot=None,parent=None):
        super().__init__(parent);self.store=store;self.path=path;self.snapshot=snapshot;self.saved_path=None;self.rule=deepcopy(rule or default_rule());self.baseline=deepcopy(self.rule);self.setWindowTitle('コンテストルール編集');self.resize(1040,710)
        box=QVBoxLayout(self);warning=QLabel('コンテスト規約は毎年改定される可能性があります。参照年と公式規約を確認してください。');warning.setStyleSheet('color:#b32020');warning.setWordWrap(True);box.addWidget(warning)
        self.tabs=QTabWidget();box.addWidget(self.tabs,1);basic=QWidget();f=QFormLayout(basic);self.tabs.addTab(basic,'基本・通常点')
        self.ident=QLineEdit();self.name=QLineEdit();self.sort_name=QLineEdit();self.sort_name.setPlaceholderText("例：しがコンテスト／ALL JA（空欄は名称順）");self.year=spin(2026);self.url=QLineEdit();self.organizer=QLineEdit()
        for label,w in [('識別子',self.ident),('名称',self.name),('並び順用の読み',self.sort_name),('参照年',self.year),('主催',self.organizer),('参照規約URL',self.url)]:f.addRow(label,w)
        self.points={k:spin(1,True) for k in ('phone','cw','digital')}
        for label,k in [('電話','phone'),('電信','cw'),('デジタル','digital')]:f.addRow(label+'の通常点',self.points[k])
        self.dup=QCheckBox('重複交信を0点');self.by_mode=QCheckBox('モードが異なれば重複としない');f.addRow(self.dup);f.addRow(self.by_mode)
        self.duplicate_note=QLabel();self.duplicate_note.setWordWrap(True);f.addRow(self.duplicate_note)
        w=QWidget();v=QVBoxLayout(w);self.tabs.addTab(w,'条件別得点');v.addWidget(QLabel('上から最初に一致した条件を採用。重複0点が優先します。'))
        self.table=QTableWidget(0,2);self.table.setHorizontalHeaderLabels(['条件','得点']);self.table.setColumnWidth(0,570);self.table.setSelectionBehavior(QAbstractItemView.SelectRows);self.table.setEditTriggers(QAbstractItemView.NoEditTriggers);v.addWidget(self.table,1)
        row=QHBoxLayout()
        for label,cb in [('追加',self.add_condition),('条件を編集',self.edit_condition),('削除',self.remove_condition),('上へ',lambda:self.move_condition(-1)),('下へ',lambda:self.move_condition(1))]:row.addWidget(button(label,cb))
        v.addLayout(row)
        w=QWidget();f=QFormLayout(w);self.multi_form=f;self.tabs.addTab(w,'マルチ・集計')
        self.multi_schema_note=QLabel();self.multi_schema_note.setWordWrap(True);f.addRow(self.multi_schema_note)
        self.m1=combo(['使用しない','ナンバー全体','単一の数字群','位置と文字数','登録した抽出ルール']);self.start=spin();self.length=spin(2);self.per_band=QCheckBox('第一マルチをバンド別に数える');f.addRow('第一マルチ（旧形式）',self.m1);self.extraction_button=button('マルチ抽出ルールを編集…',self.edit_extraction);f.addRow(self.extraction_button);f.addRow('開始位置（0＝先頭）',self.start);f.addRow('文字数',self.length);f.addRow(self.per_band)
        self.m2=combo(['使用しない','固定値','条件一致の有効交信バンド数','条件一致の有効交信数']);self.factor=spin(1,True);f.addRow('第二マルチ（FD係数など）',self.m2);f.addRow('固定値（0も有効）',self.factor);self.m2_label=QLabel();self.m2_label.setWordWrap(True);f.addRow(self.m2_label);f.addRow(button('第二マルチの条件を編集',self.edit_second))
        self.formula=combo(['総交信得点 × 第一マルチ × 第二マルチ','バンドごとの（得点 × 第一マルチ）の合計 × 第二マルチ']);f.addRow('集計方式',self.formula);self.scoring_button=button('実際のマルチ・採点定義を確認・編集…',self.edit_scoring);f.addRow(self.scoring_button)
        f.addRow(QLabel('第二マルチの交信数・バンド数＝重複を除き、得点が0より大きい交信。\n未設定の地域・プリフィックスは推測せず要確認になります。'))
        w=QWidget();v=QVBoxLayout(w);self.tabs.addTab(w,'JSON直接編集');self.raw=QPlainTextEdit();v.addWidget(self.raw);row=QHBoxLayout();row.addWidget(button('画面の値をJSONへ',self.to_json));row.addWidget(button('JSONを検証して画面へ反映',self.from_json));v.addLayout(row)
        self.status=QLabel();self.status.setWordWrap(True);box.addWidget(self.status);row=QHBoxLayout();row.addWidget(button('部門別の相手条件・時間制限…',self.edit_category_rules));row.addStretch();row.addWidget(button('保存',self.save));row.addWidget(button('別名保存',lambda:self.save(True)));row.addWidget(button('閉じる',self.reject));box.addLayout(row);self.populate()
    def populate(self):
        r=self.rule
        schema2=r['schema']==2
        if schema2:
            multipliers=r.get('scoring',{}).get('multipliers',[])
            source_label={'exchange':'受信ナンバー','area':'地域','prefix':'プリフィックス','country':'国・地域','continent':'大陸'}
            parts=[]
            for m in multipliers:
                text=f"{m.get('id','multi')}：{source_label.get(m.get('source'),m.get('source'))}"
                if m.get('per_band'):text+='（バンド別）'
                parts.append(text)
            self.multi_schema_note.setText('このルールは拡張形式2です。実際の第一マルチ相当は下の「実際のマルチ・採点定義」で管理します。\n現在のマルチ：'+(' / '.join(parts) if parts else 'なし'))
            self.status.setText('形式2では旧「第一マルチ」欄は使用しません。')
        else:
            self.multi_schema_note.setText('旧形式1：第一マルチ欄と第二マルチ欄を使用します。')
        for w in (self.m1,self.start,self.length,self.per_band,self.extraction_button):
            w.setVisible(not schema2);w.setEnabled(not schema2)
            label=self.multi_form.labelForField(w)
            if label:label.setVisible(not schema2)
        if schema2:
            fields=r.get('event',{}).get('duplicate_fields',[])
            names={'call':'相手コール','band':'バンド','mode':'モード','mode_group':'モード区分','exchange':'受信ナンバー'}
            self.by_mode.setVisible(False)
            text='実際の重複判定キー：'+' + '.join(names.get(x,x) for x in fields)
            if 'mode_group' in fields or 'mode' in fields:
                text+='。モード区分が異なる交信は別交信として扱います。'
            self.duplicate_note.setText(text)
        else:
            self.by_mode.setVisible(True)
            self.duplicate_note.setText('旧形式1では上のチェックでモード別の重複判定を指定します。')
        self.ident.setText(r['id']);self.name.setText(r['name']);self.sort_name.setText(r.get('sort_name',''));self.year.setValue(r['year']);self.url.setText(r['url']);self.organizer.setText(r.get('organizer',''))
        for k,w in self.points.items():w.setValue(r['points'][k])
        self.dup.setChecked(r['duplicate']['enabled']);self.by_mode.setChecked(r['duplicate']['by_mode']);m=r['multi1'];self.m1.setCurrentIndex(['off','whole','digits','slice','registered'].index(m['kind']));self.start.setValue(m['start']);self.length.setValue(m['length']);self.per_band.setChecked(m['per_band']);m=r['multi2'];self.m2.setCurrentIndex(['off','fixed','bands','qsos'].index(m['kind']));self.factor.setValue(m['value']);self.formula.setCurrentIndex(['total','band_sum'].index(r['formula']));self.draw_conditions();self.raw.setPlainText(dumps(r));self.raw.document().setModified(False)
    def collect(self):
        r=deepcopy(self.rule);r.update(id=self.ident.text().strip(),name=self.name.text().strip(),sort_name=self.sort_name.text().strip(),year=self.year.value(),url=self.url.text().strip(),organizer=self.organizer.text().strip());r['points']={k:w.value() for k,w in self.points.items()};r['duplicate']={'enabled':self.dup.isChecked(),'by_mode':(self.rule['duplicate']['by_mode'] if self.rule.get('schema')==2 else self.by_mode.isChecked())};r['multi1']={'kind':['off','whole','digits','slice','registered'][self.m1.currentIndex()],'start':self.start.value(),'length':self.length.value(),'per_band':self.per_band.isChecked()};r['multi2'].update(kind=['off','fixed','bands','qsos'][self.m2.currentIndex()],value=self.factor.value());r['formula']=['total','band_sum'][self.formula.currentIndex()]
        if 'rules' in self.rule['multi1']:r['multi1']['rules']=deepcopy(self.rule['multi1']['rules'])
        for i,c in enumerate(r['conditions']):c['points']=self.table.cellWidget(i,1).value()
        for k in ('sort_name','organizer'):
            if not r[k] and k not in self.rule:r.pop(k)
        return validate(r)
    def draw_conditions(self):
        import json
        self.table.setRowCount(len(self.rule['conditions']))
        for i,c in enumerate(self.rule['conditions']):self.table.setItem(i,0,QTableWidgetItem(describe(c['when'])));self.table.setCellWidget(i,1,spin(c['points'],True))
        self.m2_label.setText('条件: '+describe(self.rule['multi2']['condition']))
    def sync_points(self):
        for i,c in enumerate(self.rule['conditions']):c['points']=self.table.cellWidget(i,1).value()
    def add_condition(self):
        self.sync_points();d=ConditionDialog({'all':[]},self)
        if d.exec()==self.DialogCode.Accepted:self.rule['conditions'].append({'when':d.result_value,'points':1});self.draw_conditions()
    def edit_condition(self):
        i=self.table.currentRow()
        if i<0:return
        self.sync_points();d=ConditionDialog(self.rule['conditions'][i]['when'],self)
        if d.exec()==self.DialogCode.Accepted:self.rule['conditions'][i]['when']=d.result_value;self.draw_conditions()
    def remove_condition(self):
        i=self.table.currentRow()
        if i>=0:self.sync_points();self.rule['conditions'].pop(i);self.draw_conditions()
    def move_condition(self,delta):
        i=self.table.currentRow();j=i+delta
        if i>=0 and 0<=j<len(self.rule['conditions']):self.sync_points();a=self.rule['conditions'];a[i],a[j]=a[j],a[i];self.draw_conditions();self.table.selectRow(j)
    def edit_scoring(self):
        from contest_scoring_ui import ScoringDialog
        try:
            if self.raw.document().isModified():raise ValueError('先にJSONの変更を画面へ反映してください。')
            r=self.collect()
            if r['schema']==1:
                m=r['multi1']
                if m['kind']=='off':raise ValueError('拡張採点には1種類以上のマルチを指定します。先に第一マルチを設定してください。')
                if m['kind']=='registered':raise ValueError('登録抽出ルールからの自動変換には未対応です。既存ルールを保存し、JSONで形式2を作成してください。')
                if QMessageBox.question(self,'拡張形式へ変更','形式2に変更します。対象条件に合う0点交信もマルチ対象になります。続けますか？')!=QMessageBox.Yes:return
                value={'eligible':{'all':[]},'bonus':0,'multipliers':[dict(id='multi',source='exchange',kind=m['kind'],start=m['start'],length=m['length'],per_band=m['per_band'],when={'all':[]})]}
            else:value=r['scoring']
            d=ScoringDialog(value,self)
            if d.exec()==d.Accepted:
                r['schema']=2;r['multi1']['kind']='off';r['scoring']=d.value
                validate(r);self.rule=r;self.populate()
        except ValueError as e:self.status.setText(str(e))
    def edit_extraction(self):
        from multi_extract_ui import ExtractionDialog
        d=ExtractionDialog(self.rule['multi1'].get('rules',[]),self)
        if d.exec()==d.Accepted:self.rule['multi1']['rules']=d.rules
    def edit_category_rules(self):
        from contest_timing_ui import CategoryRulesDialog
        try:
            if self.raw.document().isModified():raise ValueError('先にJSONの変更を画面へ反映してください。')
            r=self.collect()
            if 'event' not in r:raise ValueError('大会・部門定義がありません。先にJSONで開催区間と部門を設定してください。')
            d=CategoryRulesDialog(r['event'],self)
            if d.exec()==d.Accepted:r['event']=d.value;validate(r);self.rule=r;self.populate()
        except ValueError as e:self.status.setText(str(e))
    def edit_second(self):
        d=ConditionDialog(self.rule['multi2']['condition'],self)
        if d.exec()==self.DialogCode.Accepted:self.sync_points();self.rule['multi2']['condition']=d.result_value;self.draw_conditions()
    def to_json(self):
        try:
            if self.raw.document().isModified():raise ValueError('JSONが変更されています。先に「JSONを検証して画面へ反映」してください。')
            self.rule=self.collect();self.raw.setPlainText(dumps(self.rule));self.raw.document().setModified(False);self.status.setText('画面の値をJSONへ反映しました。')
        except ValueError as e:self.status.setText(str(e))
    def from_json(self):
        try:self.rule=loads(self.raw.toPlainText());self.populate();self.status.setText('JSONを検証し、画面に反映しました。')
        except ValueError as e:self.status.setText(str(e))
    def save(self,as_new=False):
        try:
            if self.raw.document().isModified():raise ValueError('JSONの変更を先に画面へ反映してください。')
            r=self.collect();self.saved_path,self.snapshot=self.store.save(r,None if as_new else self.path,None if as_new else self.snapshot);self.path=self.saved_path;self.rule=r;self.baseline=deepcopy(r);self.populate();self.status.setText(self.store.catalog_warning or '保存しました: '+str(self.path))
        except (ValueError,StorageError,OSError) as e:self.status.setText(str(e))
    def reject(self):
        try:dirty=self.raw.document().isModified() or self.collect()!=self.baseline
        except ValueError:dirty=True
        if dirty and QMessageBox.question(self,'変更を破棄','未保存の変更を破棄して閉じますか？')!=QMessageBox.Yes:return
        super().reject()

class RulesDialog(SafeDialog):
    def __init__(self,root,parent=None):
        super().__init__(parent)
        self.store=RuleStore(root)
        self.records=[]
        self.records_by_year={}
        self.load_errors=[]
        self.setWindowTitle('コンテストルール管理・編集')
        self.resize(1120,650)
        box=QVBoxLayout(self)

        year_row=QHBoxLayout()
        year_row.addWidget(QLabel('参照年'))
        self.year=QComboBox()
        self.year.setMinimumWidth(110)
        year_row.addWidget(self.year)
        year_row.addStretch()
        box.addLayout(year_row)

        search_row=QHBoxLayout()
        search_row.addWidget(QLabel('文字フィルター'))
        self.search=QLineEdit()
        self.search.setPlaceholderText('選択した年の中を、名称・読み・識別子・主催で絞り込み')
        search_row.addWidget(self.search,1)
        box.addLayout(search_row)

        splitter=QSplitter(Qt.Horizontal)
        left=QWidget();left_box=QVBoxLayout(left);left_box.setContentsMargins(0,0,0,0)
        self.current_title=QLabel();self.current_title.setStyleSheet('font-weight:bold')
        left_box.addWidget(self.current_title)
        self.list=QListWidget();left_box.addWidget(self.list,1)
        self.source=source_label();left_box.addWidget(self.source)

        right=QWidget();right_box=QVBoxLayout(right);right_box.setContentsMargins(0,0,0,0)
        self.missing_title=QLabel();self.missing_title.setStyleSheet('font-weight:bold');self.missing_title.setWordWrap(True)
        right_box.addWidget(self.missing_title)
        self.missing_note=QLabel('右側は表示専用です。同じ識別子（ID）で比較し、前年から次年度へ用意し忘れたルールを確認するための一覧です。')
        self.missing_note.setWordWrap(True)
        right_box.addWidget(self.missing_note)
        self.previous_missing=QListWidget()
        self.previous_missing.setSelectionMode(QAbstractItemView.NoSelection)
        self.previous_missing.setFocusPolicy(Qt.NoFocus)
        right_box.addWidget(self.previous_missing,1)

        splitter.addWidget(left);splitter.addWidget(right)
        splitter.setStretchFactor(0,3);splitter.setStretchFactor(1,2)
        box.addWidget(splitter,1)

        self.list.currentItemChanged.connect(self.show_source)
        self.status=QLabel();self.status.setWordWrap(True);box.addWidget(self.status)
        row=QHBoxLayout()
        for label,cb in [('新規',self.new),('編集',self.edit),('複製',self.copy),('ルールパックを取り込む…',self.import_pack),('再読込',self.reload_rules),('閉じる',self.reject)]:
            row.addWidget(button(label,cb))
        box.addLayout(row)

        self.search.textChanged.connect(self.apply_filter)
        self.year.currentIndexChanged.connect(self.year_changed)
        self.list.itemDoubleClicked.connect(self.edit)
        self.reload_rules()

    def selected_year(self):
        value=self.year.currentData()
        try:return int(value)
        except (TypeError,ValueError):return None

    def reload_rules(self,*args,preferred_year=None):
        old_year=preferred_year if preferred_year is not None else self.selected_year()
        self.records=[];self.records_by_year={};self.load_errors=[]
        try:self.store.recover_pack()
        except (ValueError,OSError,StorageError) as e:self.load_errors.append('ルールパック復旧: '+str(e))
        try:paths=sorted(self.store.folder.glob('*.txt'))
        except OSError as e:
            paths=[];self.load_errors.append('ルール一覧: '+str(e))
        for path in paths:
            try:
                r,_=self.store.read(path)
                self.records.append({'path':str(path),'rule':r})
            except (ValueError,OSError,StorageError) as e:self.load_errors.append(path.name+': '+str(e))
        self.records.sort(key=lambda x:rule_sort_key(x['rule']))
        for record in self.records:self.records_by_year.setdefault(record['rule']['year'],[]).append(record)
        years=sorted(self.records_by_year,reverse=True)
        self.year.blockSignals(True)
        self.year.clear()
        for value in years:self.year.addItem(str(value),value)
        if old_year in years:self.year.setCurrentIndex(years.index(old_year))
        elif years:self.year.setCurrentIndex(0)
        self.year.blockSignals(False)
        self.year_changed()

    def year_changed(self,*args):
        self.apply_filter()
        self.refresh_previous_missing()

    def year_records(self,year):
        if year is None:return []
        return self.records_by_year.get(year,[])

    def apply_filter(self,*args):
        year=self.selected_year();needle=self.search.text().strip().casefold()
        current_path=self.list.currentItem().data(Qt.UserRole) if self.list.currentItem() else None
        records=self.year_records(year)
        visible=[]
        for record in records:
            r=record['rule']
            haystack=' '.join((r.get('name',''),r.get('sort_name',''),r.get('id',''),r.get('organizer',''))).casefold()
            if needle and needle not in haystack:continue
            visible.append(record)
        self.list.setUpdatesEnabled(False);self.list.clear()
        selected=None
        for record in visible:
            r=record['rule'];label=management_rule_label(r,self.store.display_label(r,record['path']))+f" [{r['id']}]"
            item=QListWidgetItem(label);item.setData(Qt.UserRole,record['path']);item.setToolTip(record['path']);item.setData(Qt.UserRole+1,r);self.list.addItem(item)
            if record['path']==current_path:selected=item
        self.list.setUpdatesEnabled(True)
        if selected:self.list.setCurrentItem(selected)
        self.current_title.setText(f'{year}年のルール — {len(visible)}件表示 / {len(records)}件' if year is not None else 'ルールがありません')
        self.update_status()

    def refresh_previous_missing(self):
        self.previous_missing.clear()
        year=self.selected_year()
        if year is None:
            self.missing_title.setText('前年比較')
            self.update_status();return
        previous=year-1
        current_ids={x['rule']['id'] for x in self.year_records(year)}
        previous_records=self.year_records(previous)
        missing=[x for x in previous_records if x['rule']['id'] not in current_ids]
        self.missing_title.setText(f'{previous}年にはあるが、{year}年にはないルール — {len(missing)}件')
        for record in missing:
            r=record['rule'];item=QListWidgetItem(management_rule_label(r,self.store.display_label(r,record['path']))+f" [{r['id']}]")
            item.setToolTip(record['path']);self.previous_missing.addItem(item)
        self.update_status()

    def update_status(self):
        year=self.selected_year()
        if year is None:
            text='有効なルールがありません。'
        else:
            previous=year-1
            current_count=len(self.year_records(year));previous_records=self.year_records(previous)
            current_ids={x['rule']['id'] for x in self.year_records(year)}
            missing_count=sum(1 for x in previous_records if x['rule']['id'] not in current_ids)
            text=(f'{year}年: {current_count}件。{previous}年: {len(previous_records)}件。'
                  f'前年にあり{year}年に同じ識別子がないもの: {missing_count}件。'
                  ' 左側の文字フィルターは読み込み済みデータだけを検索します。')
        if self.load_errors:text+='\n読込エラー:\n'+'\n'.join(self.load_errors)
        self.status.setText(text)

    def import_pack(self):
        from PySide6.QtWidgets import QFileDialog
        from rule_pack_ui import RulePackDialog
        path,_=QFileDialog.getOpenFileName(self,'ルールパックを選択','','ルールパック (*.zip)')
        if not path:return
        try:
            RulePackDialog(self.store,path,self).exec();self.reload_rules()
        except (ValueError,OSError,StorageError) as e:self.status.setText(str(e))

    def show_source(self,item,*args):self.source.setText(source_text(item.data(Qt.UserRole+1) if item else None))

    def new(self):
        r=default_rule();year=self.selected_year()
        if year is not None:r['year']=year
        d=RuleEditor(self.store,r,parent=self);d.exec()
        if d.saved_path:self.reload_rules(preferred_year=d.rule['year'])

    def edit(self,*args):self.open(False)
    def copy(self):self.open(True)

    def open(self,copy):
        item=self.list.currentItem()
        if not item:return
        try:
            path=item.data(Qt.UserRole);r,s=self.store.read(path)
            if copy:r['id']=r['id'][:70]+'-copy';r['name']+='（複製）';path=None;s=None
            d=RuleEditor(self.store,r,path,s,self);d.exec()
            if d.saved_path:self.reload_rules(preferred_year=d.rule['year'])
        except (ValueError,OSError,StorageError) as e:self.status.setText(str(e))

