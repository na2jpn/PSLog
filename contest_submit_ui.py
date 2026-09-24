from copy import deepcopy
from contest_task_ui import run_task
from pathlib import Path
from rule_source_ui import source_label,source_text
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QVBoxLayout,QHBoxLayout,QFormLayout,QWidget,QSplitter,QLineEdit,QLabel,QComboBox,QCheckBox,QTabWidget,QPlainTextEdit,QFileDialog,QTableWidget,QTableWidgetItem,QScrollArea,QMessageBox)
from window_geometry import SafeDialog
from search_ui import button
from model import now_jst
from storage import StorageError,Snapshot
from cabrillo_templates import TemplateStore
from cabrillo_template_ui import TemplatesDialog
from contest_export import plan,save,SubmitProfiles,key,OATH,check_jarl_official_required,submission_band_sort_default

class DetailsDialog(SafeDialog):
    FIELDS=('rst_sent','rst_received','frequency','tx','my_grid','his_grid')
    def __init__(self,selection,draft,parent=None,event=None):
        self.event_spec=event or {}
        super().__init__(parent);self.selection=selection;self.draft=deepcopy(draft);self.page=0;self.loading=False;self.setWindowTitle('提出用の交信情報を補完');self.resize(1060,650);v=QVBoxLayout(self);label=QLabel('周波数は実際に運用した値（kHz）。RST・周波数・GL等の補完は元ログを変更しません。チェックログXは得点・マルチから除外し、JARL提出の行頭にXを付けます。');label.setWordWrap(True);v.addWidget(label);self.table=QTableWidget(0,9);self.table.setHorizontalHeaderLabels(['日時 JST','相手コール','送信RST','受信RST','実周波数 kHz','TX・送信系列','自局GL','相手GL','チェックログ X']);v.addWidget(self.table,1)
        for i,width in enumerate([145,110,85,85,120,80,95,95]):self.table.setColumnWidth(i,width)
        if self.event_spec.get('band_choices'):
            self.table.setColumnCount(10);self.table.setHorizontalHeaderItem(9,QTableWidgetItem('元BAND → 提出用実バンド'));self.table.setColumnWidth(9,235)
            label.setText(label.text()+' 10G等の区分不明な行は右端で実バンドを指定します。周波数・運用記録を確認し、推測で選ばないでください。')
        self.operator_start=None
        if self.event_spec.get('exchange',{}).get('kind')=='tagged_region' or any((c.get('regional',{}).get('min_operators') or c.get('regional',{}).get('operator_assignments')) for c in self.event_spec.get('categories',[])):
            tagged=self.event_spec.get('exchange',{}).get('kind')=='tagged_region';self.operator_columns=3 if tagged else 1
            self.operator_start=self.table.columnCount();self.table.setColumnCount(self.operator_start+self.operator_columns)
            for i,title in enumerate(['実際の交信担当者（コール・氏名）','生年月日 YYYY-MM-DD','YL（女性）'][:self.operator_columns]):self.table.setHorizontalHeaderItem(self.operator_start+i,QTableWidgetItem(title));self.table.setColumnWidth(self.operator_start+i,210 if i<2 else 100)
            label.setText(label.text()+(' Yを送った交信には実際の担当者と生年月日又はYLを入力します。Xは年度指定局と照合します。' if tagged else ' 各交信の実際の担当者を入力します。名簿への登録だけでは実交信人数の条件を満たしません。'))
        self.remote_mode_column=None
        if self.event_spec.get('regional',{}).get('profile')=='saitama':
            self.remote_mode_column=self.table.columnCount();self.table.setColumnCount(self.remote_mode_column+1);self.table.setHorizontalHeaderItem(self.remote_mode_column,QTableWidgetItem('相手の通信方式 CW / SSB / FM / AM'));self.table.setColumnWidth(self.remote_mode_column,250)
        self.entity_column=None
        if self.event_spec.get('regional',{}).get('profile') in ('cq160','cq_ww','cq_ww_rtty','cq_wpx','cq_wpx_rtty'):
            self.entity_column=self.table.columnCount();self.table.setColumnCount(self.entity_column+1);self.table.setHorizontalHeaderItem(self.entity_column,QTableWidgetItem('CQカントリー識別子（本土米K・加VE）'));self.table.setColumnWidth(self.entity_column,250)
        self.extra_columns={}
        fields={'toyama':[('qso_power','実交信出力 W（空欄は申告最大出力）')],'iburi':[('own_location','自局地点 fixed / portable'),('island','48の相手 小笠原OG / 南鳥島MT')],'kcwa':[('other_station','相手の局種 individual（国内個人局）')],'hiroshima':[('communication','通信区分 phone / digital（音声/データ）')],'shizuoka':[('qso_power','実交信の出力 W（空欄は申告最大出力）')]}.get(self.event_spec.get('regional',{}).get('profile'),[])
        for key,title in fields:
            col=self.table.columnCount();self.table.setColumnCount(col+1);self.table.setHorizontalHeaderItem(col,QTableWidgetItem(title));self.table.setColumnWidth(col,250);self.extra_columns[col]=key
        self.table.itemChanged.connect(self.changed);row=QHBoxLayout();self.prev=button('前の100件',lambda:self.move(-1));self.next=button('次の100件',lambda:self.move(1));self.count=QLabel();row.addWidget(self.prev);row.addWidget(self.count);row.addWidget(self.next);v.addLayout(row);row=QHBoxLayout();row.addStretch();row.addWidget(button('反映',self.accept));row.addWidget(button('キャンセル',self.reject));v.addLayout(row);self.draw()
    def draw(self):
        self.loading=True;rows=self.selection.rows;self.table.setRowCount(0)
        for i,r in enumerate(rows[self.page*100:(self.page+1)*100]):
            q=r[1];d=self.draft.get(key(r),{});values=[q.date+' '+q.time,q.call]+[d.get(f,getattr(q,'sent' if f=='rst_sent' else 'received','') if f in ('rst_sent','rst_received') else '') for f in self.FIELDS];self.table.insertRow(i)
            for j,value in enumerate(values):
                item=QTableWidgetItem(value)
                if j<2:item.setFlags(item.flags()&~Qt.ItemIsEditable)
                self.table.setItem(i,j,item)
            item=QTableWidgetItem();item.setFlags(Qt.ItemIsEnabled|Qt.ItemIsSelectable|Qt.ItemIsUserCheckable);item.setCheckState(Qt.Checked if d.get('checklog',False) else Qt.Unchecked);self.table.setItem(i,8,item)
            if self.event_spec.get('band_choices'):
                from contest_normalization import values
                band,_=values(self.event_spec,q.band,q.mode);choices=self.event_spec['band_choices'].get(band)
                if choices:
                    combo=QComboBox();combo.addItem(q.band+' → 選択してください','')
                    for value in choices:combo.addItem(q.band+' → '+value+' MHz',value)
                    combo.setCurrentIndex(max(0,combo.findData(d.get('contest_band',''))));combo.currentIndexChanged.connect(lambda _,w=combo,k=key(r):self.band_changed(k,w.currentData()));self.table.setCellWidget(i,9,combo)
                else:
                    item=QTableWidgetItem(q.band+' → '+band);item.setFlags(item.flags()&~Qt.ItemIsEditable);self.table.setItem(i,9,item)
            for col,field in self.extra_columns.items():self.table.setItem(i,col,QTableWidgetItem(d.get(field,'')))
            if self.entity_column is not None:self.table.setItem(i,self.entity_column,QTableWidgetItem(d.get('cq_entity','')))
            if self.remote_mode_column is not None:self.table.setItem(i,self.remote_mode_column,QTableWidgetItem(d.get('remote_mode','')))
            if self.operator_start is not None:
                for offset,field in enumerate(['operator_name','operator_birthdate'][:self.operator_columns]):self.table.setItem(i,self.operator_start+offset,QTableWidgetItem(d.get(field,'')))
                if self.operator_columns==3:
                    item=QTableWidgetItem();item.setFlags(Qt.ItemIsEnabled|Qt.ItemIsSelectable|Qt.ItemIsUserCheckable);item.setCheckState(Qt.Checked if d.get('operator_yl') is True else Qt.Unchecked);self.table.setItem(i,self.operator_start+2,item)
        pages=max(1,(len(rows)+99)//100);self.prev.setEnabled(self.page>0);self.next.setEnabled(self.page+1<pages);self.count.setText(f'{self.page+1}/{pages}ページ・全{len(rows):,}件');self.loading=False
    def changed(self,item):
        if self.loading:return
        if item.column() in self.extra_columns:
            self.draft.setdefault(key(self.selection.rows[self.page*100+item.row()]),{})[self.extra_columns[item.column()]]=item.text().strip();return
        if self.entity_column is not None and item.column()==self.entity_column:
            self.draft.setdefault(key(self.selection.rows[self.page*100+item.row()]),{})['cq_entity']=item.text().strip().upper();return
        if self.remote_mode_column is not None and item.column()==self.remote_mode_column:
            self.draft.setdefault(key(self.selection.rows[self.page*100+item.row()]),{})['remote_mode']=item.text().strip().upper();return
        if self.operator_start is not None and self.operator_start<=item.column()<self.operator_start+self.operator_columns:
            d=self.draft.setdefault(key(self.selection.rows[self.page*100+item.row()]),{});offset=item.column()-self.operator_start
            if offset==2:d['operator_yl']=item.checkState()==Qt.Checked
            else:d[['operator_name','operator_birthdate'][offset]]=item.text().strip()
            return
        if item.column()<2 or item.column()>8:return
        d=self.draft.setdefault(key(self.selection.rows[self.page*100+item.row()]),{})
        if item.column()==8:d['checklog']=item.checkState()==Qt.Checked
        else:d[self.FIELDS[item.column()-2]]=item.text().strip()
    def move(self,delta):self.page+=delta;self.draw()
    def band_changed(self,k,value):self.draft.setdefault(k,{})['contest_band']=value

class SubmissionPane(QWidget):
    def __init__(self,wizard):
        super().__init__();self.wizard=wizard;self.repo=wizard.repo;self.prepared=None;self.current_format=None;self.cab_fields={};self.template=None;self.template_snapshot=None;self.template_path=None;self.cache={};self.loading=False;self.last_context=None;self.bundle_items=[];self.club_master=None;self.club_match=None;self.club_auto='';self.categoryname_auto='';self.callsign_auto=''
        self.profiles=None;profile_error=''
        try:self.profiles=SubmitProfiles(self.repo.root)
        except (ValueError,OSError,StorageError) as e:profile_error=str(e)
        box=QVBoxLayout(self);split=QSplitter(Qt.Horizontal);box.addWidget(split,1);left=QWidget();self.left=QVBoxLayout(left);split.addWidget(left);self.forms=QTabWidget();self.left.addWidget(self.forms,1);right=QWidget();rv=QVBoxLayout(right);split.addWidget(right);split.setSizes([560,520])
        self.overview=QLabel();self.overview.setWordWrap(True);self.overview.setStyleSheet('font-size:12px; color:#3f4b52;');rv.addWidget(self.overview)
        self.score_overview=QLabel();self.score_overview.setWordWrap(True);self.score_overview.setStyleSheet('font-size:14px; font-weight:700; color:#c62828;');rv.addWidget(self.score_overview)
        self.rule_source=source_label();self.rule_source.setStyleSheet('font-size:11px; color:#65727b;');rv.addWidget(self.rule_source)
        back_note=QLabel('RST・周波数・GL・TXなど交信内容を直す場合は「戻る」で前の確認画面へ戻ってください。');back_note.setWordWrap(True);back_note.setStyleSheet('font-size:12px; color:#55636c;');rv.addWidget(back_note)
        self.preview=QPlainTextEdit();self.preview.setReadOnly(True);self.preview.setPlaceholderText('「入力内容を確認」で出力テキストを表示します。');self.preview.setLineWrapMode(QPlainTextEdit.NoWrap);self.preview.setMinimumHeight(170);self.preview.setMaximumHeight(300);rv.addWidget(self.preview)
        from contest_award_ui import AwardPane
        self.awards=AwardPane(self.invalidate);rv.insertWidget(rv.indexOf(self.preview),self.awards)
        output_error=''
        default_folder=getattr(self.repo,'contest_output',self.repo.root/'output'/'contest')
        try:default_folder.mkdir(parents=True,exist_ok=True)
        except OSError as e:output_error='コンテスト出力フォルダーを作成できません: '+str(e);default_folder=self.repo.root
        self.folder=QLineEdit(str(default_folder));row=QHBoxLayout();row.addWidget(self.folder);row.addWidget(button('保存先…',self.browse));rv.addLayout(row);self.folder.textChanged.connect(self.invalidate);self.folder.textChanged.connect(self.folder.setToolTip);self.folder.setToolTip(self.folder.text());rv.addWidget(QLabel('標準保存先: output/contest　同名時は _001 などを付けて保存します。'))
        # Final-stage actions live in the wizard footer so they remain visible
        # even when this page is vertically scrolled. ContestDialog owns their
        # placement; SubmissionPane owns their behavior/state.
        self.prepare_button=button('入力内容を確認',self.prepare)
        self.save_button=button('ファイルを保存',self.write);self.save_button.setEnabled(False)
        self.status=QLabel();self.status.setWordWrap(True);box.addWidget(self.status)
        initial_error='\n'.join(x for x in (profile_error,output_error) if x)
        if initial_error:self.set_status(initial_error,error=True)
        else:self.set_status('「入力内容を確認」を押してください。確認後にファイルを保存できます。')
        self.bundle_widget=QWidget();row=QHBoxLayout(self.bundle_widget);row.setContentsMargins(0,0,0,0);row.setSpacing(6)
        row.addWidget(button('広島WAS：現在の部門をセットへ追加',self.add_bundle));row.addWidget(button('セットを確認',self.preview_bundle));row.addWidget(button('セットを空にする',self.clear_bundle))
        self.bundle_widget.setVisible(False);rv.addWidget(self.bundle_widget)
    def set_status(self,text,error=False):
        self.status.setText(str(text))
        self.status.setStyleSheet('color:#c62828; font-weight:700;' if error else 'color:#455a64;')

    def add_bundle(self):
        try:
            if self.wizard.rule.get('id')!='hiroshima_was':raise ValueError('広島WASの2サマリー1本文用です。')
            self.prepare()
            if self.prepared is None:return
            from contest_bundle import item
            value=item(self.wizard.rule,self.wizard.event_context(),self.wizard.selection.rows[0][0],self.prepared)
            self.bundle_items=[x for x in self.bundle_items if x['category']!=value['category']]+[value]
            self.set_status('セットへ追加: '+', '.join(x['category'] for x in self.bundle_items))
        except (ValueError,StorageError) as ex:self.set_status(str(ex),error=True)
    def preview_bundle(self):
        try:
            from contest_bundle import combine
            self.prepared=combine(self.bundle_items);self.preview.setPlainText(self.prepared.preview());self.save_button.setEnabled(True);self.set_status('セット全体を確認し、ファイルを保存してください。')
        except (ValueError,StorageError) as ex:self.prepared=None;self.save_button.setEnabled(False);self.set_status(str(ex),error=True)
    def clear_bundle(self):self.bundle_items=[];self.invalidate();self.set_status('提出セットを空にしました。')
    def tab(self,name):
        w=QWidget();f=QFormLayout(w);f.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow);f.setRowWrapPolicy(QFormLayout.WrapLongRows);scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(w);self.forms.addTab(scroll,name);return f
    def form_label(self,label):
        required=str(label).rstrip().endswith('*')
        text=str(label).rstrip()
        if required:text=text[:-1].rstrip()+' <span style="color:#c62828;font-weight:700;">＊</span>'
        q=QLabel(text);q.setTextFormat(Qt.RichText);return q
    def field(self,form,key,label,values=None,multiline=False):
        w=QPlainTextEdit() if multiline else QLineEdit()
        if multiline:w.setMaximumHeight(110)
        self.fields[key]=w;form.addRow(self.form_label(label),w);value=(values or {}).get(key,'')
        if multiline:w.setPlainText(value)
        else:w.setText(value)
        w.textChanged.connect(self.invalidate);return w
    def checkbox(self,form,key,label):
        w=QCheckBox(label);self.fields[key]=w;form.addRow(w);w.toggled.connect(self.invalidate);return w
    def select(self,form,key,label,choices,editable=False,value=''):
        w=QComboBox();w.addItems(choices);w.setEditable(bool(editable));self.fields[key]=w;form.addRow(self.form_label(label),w)
        if value:w.setCurrentText(str(value))
        w.currentIndexChanged.connect(self.invalidate)
        if w.isEditable() and w.lineEdit():w.lineEdit().textChanged.connect(self.invalidate)
        return w
    def info(self):
        result={}
        for k,w in self.fields.items():
            if isinstance(w,QCheckBox):result[k]=w.isChecked()
            elif isinstance(w,QPlainTextEdit):result[k]=w.toPlainText()
            elif isinstance(w,QComboBox):result[k]=w.currentText()
            else:result[k]=w.text()
        if self.current_format and self.current_format.startswith('JARL'):result['award_requests']=self.awards.requests()
        return result
    def set_context(self):
        format=self.wizard.format.currentText()
        if format!=self.current_format:
            if self.current_format:
                self.cache[self.current_format]=self.info()
                if self.current_format=='Cabrillo' and self.template_path:self.cache[self.template_path]=self.info();self.template_path=None
            self.loading=True
            while self.forms.count():
                w=self.forms.widget(0);self.forms.removeTab(0);w.deleteLater()
            self.fields={};self.current_format=format
            if format.startswith('JARL') or format=='所定様式PDF':self.build_jarl('JARL R1.0' if format=='所定様式PDF' else format)
            elif format=='Cabrillo':self.build_cabrillo()
            else:self.build_zlog()
            self.loading=False
        context=(format,self.wizard.loaded_scope)
        if context!=self.last_context and 'oath' in self.fields:self.fields['oath'].setChecked(False)
        self.last_context=context
        manual=self.wizard.rule.get('id')=='manual_other';self.rule_source.setText('その他のコンテスト：手動設定・自動採点なし' if manual else source_text(self.wizard.rule))
        self.bundle_widget.setVisible(self.wizard.rule.get('id')=='hiroshima_was')
        score_text='自動採点なし（出力上0扱い）' if manual else (self.wizard.result.total if (self.wizard.result.total is not None or getattr(self.wizard.result,'unscored_submission',False)) else '未確定')
        self.overview.setText(f'{format}\n対象ログの自局: {self.wizard.loaded_scope[0]} ／ {len(self.wizard.selection.rows):,}交信\n'+(('手動コンテスト: '+self.wizard.rule['name']+f'（{self.wizard.rule["year"]}年）') if manual else f'参照ルール: {self.wizard.rule["name"]}（{self.wizard.rule["year"]}年版）'))
        self.score_overview.setText(f'総得点: {score_text}')
        if 'callsign' in self.fields:
            desired=self.wizard.loaded_scope[0]
            current=self.fields['callsign'].text().strip()
            if not current or current==self.callsign_auto:
                self.fields['callsign'].setText(desired);self.callsign_auto=desired
        if 'event' in self.wizard.rule and 'category' in self.fields:
            self.fields['category'].setText(self.wizard.rule['event'].get('regional',{}).get('checklog_code','CHECKLOG') if self.wizard.event_context().get('submission_mode')=='checklog' else self.wizard.event_context().get('category',''))
            submit=self.wizard.rule['event'].get('submission')
            if submit:
                self.fields['contest'].setText(submit['contest']);self.fields['zone'].setCurrentText(submit['zone'])
                self.overview.setText(self.overview.text()+'\n'+submit['instructions'])
                if submit.get('row_scope')=='category':self.overview.setText(self.overview.text()+'\n出力は選択した部門の日時・バンド・モードに絞ります。部門内の重複・0点交信は残します。')
                if len(submit.get('allowed_zones',[]))>1:self.overview.setText(self.overview.text()+'\nJST/UTCを選べます。受付画面でも同じ時刻基準を選んでください。')
                required=submit.get('required_fields',[])
                if required:
                    labels=dict(email='メールアドレス',opplace='運用地',multioplist='運用者一覧',licensedate='免許年月日',age='年齢')
                    self.overview.setText(self.overview.text()+'\n大会指定の必須項目: '+', '.join(labels[k] for k in required))
            self.fields['power'].setText(str(self.wizard.event_context().get('power','')))
            category=next((c for c in self.wizard.rule['event']['categories'] if c['id']==self.wizard.event_context().get('category')),{})
            whole=self.wizard.event_context().get('submission_mode')=='checklog'
            if not whole:
                self.fields['category'].setText(category.get('submission_code',category.get('id','')))
                if 'categoryname' in self.fields:
                    desired_name=category.get('name','')
                    current_name=self.fields['categoryname'].text().strip()
                    if not current_name or current_name==self.categoryname_auto:
                        self.fields['categoryname'].setText(desired_name);self.categoryname_auto=desired_name
            if category.get('mo_operators_in_comments'):self.overview.setText(self.overview.text()+'\nMOの場合は運用者一覧へ全員のコール・氏名・従事者資格を入力します。意見欄にも記載します。')
            if category.get('operator_list_format')=='calls':self.overview.setText(self.overview.text()+'\n運用者一覧には全員のコールのみをカンマ又は空白で区切って入力します。意見欄へ記載します。')
            if category.get('operators_in_comments') and category.get('operator_list_format')!='calls':self.overview.setText(self.overview.text()+'\n運用者一覧に全員の姓名・無線従事者資格を入力してください。SOの社団局も必要で、意見欄へ記載します。')
            self.fields['multiop'].setChecked(not whole and category.get('operator')=='MO')
            if whole:category={}
            self.fields['fd'].setChecked(not whole and self.wizard.rule['event'].get('station_factor')=='jarl_fd')
            if self.wizard.rule['event'].get('station_factor')=='jarl_fd':
                self.overview.setText(self.overview.text()+'\nFD局種: '+str(self.wizard.event_context().get('fd_class',''))+' ／ 第二マルチ: '+str(self.wizard.result.multi2))
            q=category.get('qualification',{});ctx=self.wizard.event_context()
            if self.wizard.rule['event'].get('newcomer_claim') and ctx.get('newcomer_requested'):self.overview.setText(self.overview.text()+'\nニューカマー申告（初開局日 '+ctx.get('newcomer_licensedate','')+'）を意見欄へ記載します。得点は変わりません。')
            if self.wizard.rule['event'].get('power_by_operation'):
                self.fields['portable'].setChecked(ctx.get('operation_kind')=='portable')
                self.overview.setText(self.overview.text()+'\n電力条件の運用形態と提出の移動指定を照合します。')
            if category.get('location_group'):
                self.fields['opplace'].setText(ctx.get('operating_locations',{}).get(category['location_group'],''))
                self.overview.setText(self.overview.text()+'\n運用地は部門別の確認値と一致する必要があります。')
            if 'yl_or_younger_than' in q:self.overview.setText(self.overview.text()+'\nYL／若年資格を意見欄に記載します。Y送信行は交信情報補完で実運用者を確認してください。')
            if ('min_age' in q or 'max_age' in q) and 'age' in self.fields:self.fields['age'].setText(str(ctx.get('age','')))
            if 'license_since' in q and 'licensedate' in self.fields:self.fields['licensedate'].setText(ctx.get('licensedate',''))
            if 'operators_max_age' in q:
                from contest_qualification import operator_text
                self.fields['multioplist'].setText(operator_text(ctx.get('operators',[])))
            if (('min_age' in q or 'max_age' in q) and q.get('age_output','field')=='field' or ('license_since' in q and q.get('license_output','field')=='field')) and format!='JARL R2.1':self.overview.setText(self.overview.text()+'\nこの種目は資格欄を出力できるJARL R2.1を選択してください。')
            if q.get('license_output')=='comments':self.overview.setText(self.overview.text()+f'\n意見欄へ初回局免許年月日 {ctx.get("licensedate","")}を記載します。')
            if q.get('age_output')=='comments':self.overview.setText(self.overview.text()+f'\n意見欄へ運用者年齢 {ctx.get("age","")}歳を記載します。')
            self.fields['multioplist'].setReadOnly(bool(category.get('participation')))
            if category.get('participation'):
                from contest_participation import operator_text
                if category.get('operator')=='MO':self.fields['multioplist'].setText(operator_text(ctx))
                self.overview.setText(self.overview.text()+'\n担当者の年齢・交信数'+('・続柄' if category['participation']['family_pair'] else '')+'を意見欄へ追加します。プレビューで確認してください。')
        if format.startswith('JARL'):self.awards.refresh(self.wizard.rule,self.wizard.selection,self.wizard.draft,self.wizard.event_context(),self.wizard.loaded_scope)
        else:self.awards.setVisible(False)
        self.invalidate()
    def apply_imported_info(self,values):
        """Restore fields from a previously generated JARL submission."""
        self.loading=True
        try:
            for key,value in (values or {}).items():
                w=self.fields.get(key)
                if w is None:continue
                if isinstance(w,QCheckBox):w.setChecked(bool(value))
                elif isinstance(w,QPlainTextEdit):w.setPlainText(str(value))
                elif isinstance(w,QComboBox):w.setCurrentText(str(value))
                else:w.setText(str(value))
            if 'oath' in self.fields:self.fields['oath'].setChecked(True)
        finally:self.loading=False
        self.invalidate();self.set_status('既存の提出TXTの提出情報を復元しました。必要な修正後、「入力内容を確認」を押してください。')

    def build_jarl(self,format):
        values=dict(self.profiles.values.get('jarl',{}) if self.profiles else {});values.update(self.cache.get(format,{}));values.setdefault('date',now_jst().strftime('%Y-%m-%d'));values['callsign']=self.wizard.loaded_scope[0];values['categoryname']='';self.callsign_auto=values['callsign'];self.categoryname_auto='';f=self.tab('提出情報')
        required_note=QLabel('<span style="color:#c62828;font-weight:700;">＊</span> 必須項目');required_note.setTextFormat(Qt.RichText);f.addRow(required_note)
        self.field(f,'callsign','提出コールサイン *',values)
        for k,label in [('contest',f'{self.wizard.activity_name}名 *'),('category','部門コード *')]:self.field(f,k,label,values)
        if format=='JARL R1.0':self.field(f,'categoryname','部門名称',values)
        for k,label in [('name','氏名・クラブ局名称 *'),('address','連絡先住所 *'),('power','最大空中線電力 W *')]:self.field(f,k,label,values)
        if format=='JARL R1.0':
            self.select(f,'powertype','出力の記載区分 *',['','定格出力','実測出力'],value=values.get('powertype',''))
            self.field(f,'equipment','使用無線設備（機種名など）',values)
            self.field(f,'powersupply','使用電源（電池・発電機・商用電源など）',values)
            self.select(f,'licenseclass','従事者資格 *',[
                '',
                '第1級アマチュア無線技士',
                '第2級アマチュア無線技士',
                '第3級アマチュア無線技士',
                '第4級アマチュア無線技士'
            ],editable=True,value=values.get('licenseclass',''))
        else:
            fd_required=self.wizard.rule.get('event',{}).get('station_factor')=='jarl_fd' and self.wizard.event_context().get('submission_mode','entry')!='checklog'
            self.field(f,'powersupply','使用電源（電池・発電機・商用電源など）'+(' *' if fd_required else ''),values)
        self.select(f,'zone','ログ時刻',['JST','UTC'],value=values.get('zone','JST'));f.addRow(QLabel('JARL国内はJST、ALL ASIAN DXはUTCを選択。'))
        rule_band_sort=submission_band_sort_default(self.wizard.rule)
        self.checkbox(f,'sort_band_time','ログをバンド順に並べる（同一バンド内は時刻順）').setChecked(bool(values.get('sort_band_time',rule_band_sort)))
        self.checkbox(f,'fd','フィールドデー（第二マルチをFDCOEFFへ記載）').setChecked(values.get('fd',False));self.checkbox(f,'multiop','マルチオペ部門').setChecked(values.get('multiop',False));self.checkbox(f,'portable','移動運用（運用地の記載が必須）');self.checkbox(f,'guest','ゲストSO（運用者コールの記載が必須）')
        f=self.tab('任意・部門別情報')
        for k,label in [('opcall','ゲストOPコール'),('tel','電話'),('email','メールアドレス *'),('opplace','運用地'),('multioplist','マルチOP一覧'),('clubnumber','登録クラブ番号')]:self.field(f,k,label,values)
        if format=='JARL R1.0':self.field(f,'clubname','登録クラブ名',values)
        self.setup_clubs(f)
        # Keep comments as QLineEdit for compatibility with the existing
        # submission/profile code and tests.  Long text can still be entered;
        # multiline editing is not required by the JARL output format.
        self.field(f,'comments','意見',values)
        if format!='JARL R1.0':
            self.field(f,'licensedate','局免許年月日（YYYY-MM-DD）',values);self.field(f,'age','年齢',values)
        f=self.tab('宣誓');label=QLabel(OATH);label.setWordWrap(True);f.addRow(label);self.checkbox(f,'oath','宣誓内容を確認しました ＊');self.field(f,'date','宣誓日（YYYY-MM-DD） *',values);self.field(f,'signature','署名 *',values)
    def setup_clubs(self,form):
        from clubs import load
        self.club_auto='';self.club_match=None;self.club_master=None
        self.club_label=QLabel();self.club_label.setWordWrap(True);form.addRow(self.club_label)
        row=QHBoxLayout();self.club_search_button=button('登録クラブを検索…',self.search_clubs);self.club_use_button=button('検索結果のクラブ名を使用',self.use_club);row.addWidget(self.club_search_button);row.addWidget(self.club_use_button);row.addStretch();form.addRow('クラブ検索',row)
        try:self.club_master=load(self.repo.root)
        except (OSError,StorageError) as e:self.club_label.setText(str(e)+'\n番号・名称は手入力できます。')
        self.club_search_button.setEnabled(self.club_master is not None);self.club_use_button.setVisible('clubname' in self.fields)
        self.fields['clubnumber'].textChanged.connect(self.update_club);self.update_club()
    def update_club(self,*args):
        self.club_match=None;self.club_use_button.setEnabled(False)
        if self.club_master is None:return
        try:self.club_match=self.club_master.lookup(self.fields['clubnumber'].text())
        except ValueError as e:self.club_label.setText(str(e));return
        name=self.club_match['name'] if self.club_match else ''
        if 'clubname' in self.fields:
            field=self.fields['clubname']
            if not field.text() or field.text()==self.club_auto or field.text()==name:field.setText(name);self.club_auto=name
            self.club_use_button.setEnabled(bool(name))
        caption=name if name else ('DBに未掲載です。手入力した番号で出力できます。' if self.fields['clubnumber'].text().strip() else 'クラブ番号を入れると名称を表示します。')
        self.club_label.setText(caption+'\n'+self.club_master.label())
        dates=[r[1].date for r in self.wizard.selection.rows] if self.wizard.selection else []
        if dates and (min(dates)<self.club_master.meta['valid_from'] or max(dates)>self.club_master.meta['valid_to']):self.club_label.setText(self.club_label.text()+'\n交信期間はDBの参照期間外です。当時の登録情報を確認してください。')
    def use_club(self):
        if self.club_match and 'clubname' in self.fields:self.fields['clubname'].setText(self.club_match['name']);self.club_auto=self.club_match['name']
    def search_clubs(self):
        from club_ui import ClubDialog
        if self.club_master is None:return
        d=ClubDialog(self.club_master,self.fields['clubnumber'].text(),self)
        if d.exec()==SafeDialog.DialogCode.Accepted:self.fields['clubnumber'].setText(d.result_value['number']);self.use_club()
    def build_zlog(self):
        f=self.tab('zLogへの引継ぎ');self.select(f,'zone','時刻基準',['JST','UTC']);self.select(f,'power_code','電力コード',['','P','L','M','H']);self.checkbox(f,'split_power','送信番号末尾の電力コードを分離（zLog定義の $P 用）');self.field(f,'operator','運用者（任意）');self.checkbox(f,'memo','RMKSをメモへ引き継ぐ').setChecked(True);label=QLabel('34列のzLog令和版CSVを出力します。\nzLogで対象コンテスト・自局を設定して読み込み、得点とマルチを再計算してください。\n未対応のMODEやBANDは出力前に停止します。');label.setWordWrap(True);f.addRow(label)
    def build_cabrillo(self):
        f=self.tab('テンプレート');self.template_search=QLineEdit();self.template_search.setPlaceholderText('名称・CONTEST・参照年で検索');f.addRow(self.template_search);self.templates=QComboBox();f.addRow('出力テンプレート',self.templates);f.addRow(button('テンプレート管理・編集…',self.manage_templates));self.cab_note=QLabel();self.cab_note.setWordWrap(True);f.addRow(self.cab_note);self.cab_form=self.tab('提出情報');self.template_search.textChanged.connect(self.refresh_templates);self.templates.currentIndexChanged.connect(self.load_template);self.refresh_templates()
    def refresh_templates(self,*args):
        previous=self.templates.currentData();self.templates.blockSignals(True);self.templates.clear();self.templates.addItem('テンプレートを選択',None);errors=[]
        for path in TemplateStore(self.repo.root).files():
            try:
                t,s=TemplateStore(self.repo.root).read(path);name=f"{t['name']} / {t['contest']} / {t['year']}年版"
                if self.template_search.text().casefold() in name.casefold():self.templates.addItem(name,str(path))
            except (ValueError,OSError,StorageError,TypeError) as e:errors.append(path.name+': '+str(e))
        i=self.templates.findData(previous)
        if i>=0:self.templates.setCurrentIndex(i)
        self.templates.blockSignals(False);self.load_template();
        if errors:self.set_status('\n'.join(errors), error=True)
    def load_template(self,*args):
        if self.template_path:self.cache[self.template_path]=self.info()
        self.template=None;self.template_snapshot=None;self.template_path=None;self.fields={}
        while self.cab_form.rowCount():self.cab_form.removeRow(0)
        path=self.templates.currentData()
        if not path:self.cab_note.setText('出力日時はUTC。テンプレートを選ぶと提出項目が表示されます。');self.invalidate();return
        try:
            t,s=TemplateStore(self.repo.root).read(path);self.template=t;self.template_snapshot=s;self.template_path=path;values=dict(self.profiles.values.get('cabrillo',{}) if self.profiles else {});values.update(self.cache.get(path,{}));values.setdefault('CONTEST',t['contest']);self.field(self.cab_form,'CONTEST','CONTEST *',values)
            if t.get('rule_id')=='jarl_world_wide_rtty':
                from contest_international import expected_headers
                rule=self.wizard.rule;ctx=self.wizard.event_context();c=next((c for c in rule['event']['categories'] if c['id']==ctx.get('category')),None)
                if c:
                    for k,value in expected_headers(rule,c,ctx).items():values.setdefault(k,value)
            for h in t['headers']:
                tag=h['tag'];label=tag+(' *' if h['required'] else '');values.setdefault(tag,h['default'])
                if h['choices']:
                    w=self.select(self.cab_form,tag,label,['']+h['choices']);w.setCurrentText(values.get(tag,''))
                else:self.field(self.cab_form,tag,label,values,tag in ('ADDRESS','SOAPBOX','OPERATORS'))
            self.cab_note.setText(f"Cabrillo {t['version']} / {t['encoding']} / UTC\n参照年: {t['year']}\n周波数: "+('HF実周波数が必須（VHF以上はバンド）' if t['frequency']=='actual' else '空欄時はバンド識別値')+f"\n出典: {t['url']}")
        except (ValueError,OSError,StorageError,TypeError,OverflowError) as e:self.set_status(str(e), error=True)
        self.invalidate()
    def manage_templates(self):TemplatesDialog(self.repo.root,self).exec();self.refresh_templates()
    def details(self):
        d=DetailsDialog(self.wizard.selection,self.wizard.draft,self,event=self.wizard.rule.get('event',{}))
        if d.exec()==SafeDialog.DialogCode.Accepted:
            self.wizard.update_details_draft(d.draft);self.invalidate();self.wizard.calculate()
            if self.wizard.result is not None and (self.wizard.result.total is not None or getattr(self.wizard.result,'unscored_submission',False)):self.set_context()
            else:self.overview.setText('補完内容の変更により採点を再確認してください。')
    def invalidate(self,*args):
        self.prepared=None;self.save_button.setEnabled(False)
        if not self.loading:
            self.preview.clear()
            self.set_status('「入力内容を確認」を押してください。確認後にファイルを保存できます。')
    def browse(self):
        path=QFileDialog.getExistingDirectory(self,'保存先',self.folder.text())
        if path:self.folder.setText(path)
    def prepare(self):
        self.invalidate()
        try:
            guards=[]
            if self.wizard.rule_path is not None and self.wizard.rule_snapshot is not None:guards.append((self.wizard.rule_path,self.wizard.rule_snapshot))
            if self.current_format.startswith('JARL') and self.club_match and self.club_master:guards.extend(self.club_master.guards)
            for path,snapshot in guards:snapshot.check(Path(path))
            if self.current_format=='Cabrillo':
                if self.template_path is None:raise ValueError('テンプレートを選択してください。')
                self.template_snapshot.check(Path(self.template_path));guards.append((self.template_path,self.template_snapshot))
            info=self.info()
            # Match the official JARL summary-maker required fields in the
            # interactive workflow.  Keep this at the UI boundary so old R1.0
            # files that omitted fields can still be reopened/read by the
            # low-level exporter.
            if self.current_format in ('JARL R1.0','JARL R2.1'):
                check_jarl_official_required(self.current_format,info)
            def prepare_output():
                p=plan(self.wizard.selection,self.wizard.rule,self.wizard.draft,self.current_format,info,self.template,guards,context=self.wizard.event_context())
                from itertools import islice
                from io import StringIO
                lines=list(islice(StringIO(p.preview()),1501))
                preview=''.join(lines[:1500])+('\n（先頭1500行のみ表示・出力は全件）' if len(lines)>1500 else '')
                return p,preview
            p,preview=run_task(self,'提出ファイルを準備しています',prepare_output);self.prepared=p;self.preview.setPlainText(preview);self.save_button.setEnabled(True);self.set_status(f'{p.qsos:,}交信の出力内容を確認しました。\n'+'\n'.join(p.warnings))
        except (ValueError,OSError,StorageError,TypeError,OverflowError) as e:self.set_status(str(e),error=True)
    def write(self):
        if self.prepared is None:return
        self.save_button.setEnabled(False)
        try:
            prepared=self.prepared;folder=self.folder.text()
            path=run_task(self,'提出ファイルを保存しています',lambda:save(prepared,folder));self.set_status('保存しました: '+str(path));
            if self.isVisible():QMessageBox.information(self,'保存完了','コンテスト提出ログを保存しました。\n\n'+str(path))
            self.prepared=None
        except (ValueError,OSError,StorageError) as e:self.set_status(str(e),error=True);return
        kind='jarl' if self.current_format.startswith('JARL') else 'cabrillo' if self.current_format=='Cabrillo' else None
        if kind:
            if self.profiles:
                try:self.profiles.remember(kind,self.info())
                except (ValueError,OSError,StorageError) as e:self.set_status(f'出力ファイルは保存済み: {path}\n次回用の提出者設定は保存できませんでした: {e}',error=True)
            else:self.set_status(f'出力ファイルは保存済み: {path}\n提出者設定が読めないため、次回用の記憶は行いませんでした。',error=True)
