from copy import deepcopy
from PySide6.QtWidgets import (QVBoxLayout,QFormLayout,QComboBox,QDoubleSpinBox,
    QLineEdit,QCheckBox,QHBoxLayout,QLabel,QTabWidget,QWidget,QPlainTextEdit,QScrollArea,
    QGridLayout,QListWidget,QListWidgetItem,QDialogButtonBox,QPushButton,QAbstractItemView,QGroupBox)
from window_geometry import SafeDialog
from search_ui import button
from contest_timing import HISTORY_FLAG,parse_blocks
from category_filters import classify_categories,category_facets,category_compatible
from contest_confirmations import filtered_flags,active_flags


class CategorySelectDialog(SafeDialog):
    """Generic category picker that never drops the source category list."""
    FACETS=(('region','地域区分'),('operation','運用'),('mode','モード'),('power','電力'),('band','バンド'))
    def __init__(self,categories,current='',parent=None,initial_filters=None,predicate=None):
        super().__init__(parent);self.setWindowTitle('参加部門を選択');self.resize(900,650)
        self.entries=classify_categories(categories);self.selected_id=None;self.predicate=predicate or (lambda _source:True)
        outer=QVBoxLayout(self)
        note=QLabel('正式な参加部門一覧を、現在の局種・実運用電力と登録内容から絞り込みます。さらに地域・運用・モード・電力・バンドで候補を絞れます。')
        note.setWordWrap(True);outer.addWidget(note)
        grid=QGridLayout();self.search=QLineEdit();self.search.setPlaceholderText('正式部門名・コードで検索');grid.addWidget(QLabel('検索'),0,0);grid.addWidget(self.search,0,1,1,4)
        self.filters={}
        for col,(key,label) in enumerate(self.FACETS):
            box=QComboBox();box.addItem('すべて','')
            values=[]
            for entry in self.entries:
                value=entry['facets'][key]
                if value not in values:values.append(value)
            for value in values:box.addItem(value,value)
            grid.addWidget(QLabel(label),1,col);grid.addWidget(box,2,col);self.filters[key]=box
        outer.addLayout(grid)
        self.count_label=QLabel();self.count_label.setStyleSheet('font-weight:600; color:#304b3a;');outer.addWidget(self.count_label)
        self.list=QListWidget();self.list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection);outer.addWidget(self.list,1)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel);outer.addWidget(buttons)
        buttons.accepted.connect(self.accept_selected);buttons.rejected.connect(self.reject);self.list.itemDoubleClicked.connect(lambda _item:self.accept_selected())
        self.search.textChanged.connect(self.refilter)
        for box in self.filters.values():box.currentIndexChanged.connect(self.refilter)
        self._initial=current
        for key,value in (initial_filters or {}).items():
            box=self.filters.get(key);index=box.findData(value) if box is not None else -1
            if index>=0:box.setCurrentIndex(index)
        self.refilter()
    def refilter(self,*_args):
        query=self.search.text().strip().casefold();visible=[]
        for entry in self.entries:
            if not self.predicate(entry['source']):continue
            label=entry['name']+' ['+str(entry['submission_code'])+']'
            if query and query not in label.casefold():continue
            if any(box.currentData() and entry['facets'][key]!=box.currentData() for key,box in self.filters.items()):continue
            visible.append(entry)
        self.list.clear()
        for entry in visible:
            facets=' / '.join(v for v in entry['facets'].values() if v not in ('その他／未分類','通常／その他'))
            text=entry['name']+' ['+str(entry['submission_code'])+']'+(('    '+facets) if facets else '')
            item=QListWidgetItem(text);item.setData(256,entry['id']);self.list.addItem(item)
            if entry['id']==self._initial:self.list.setCurrentItem(item)
        self.count_label.setText(f'候補 {len(visible)}件 ／ 登録部門 {len(self.entries)}件')
        if self.list.currentRow()<0 and self.list.count():self.list.setCurrentRow(0)
    def accept_selected(self):
        item=self.list.currentItem()
        if not item:return
        self.selected_id=item.data(256);self.accept()

class EventDialog(SafeDialog):
    def __init__(self,event,context,parent=None):
        super().__init__(parent)
        self.event_spec=event;self.context=deepcopy(context)
        self.setWindowTitle('参加部門と運用条件');self.resize(820,620)
        box=QVBoxLayout(self);self.tabs=QTabWidget();box.addWidget(self.tabs,1)
        basic=QWidget();form=QFormLayout(basic);scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(basic);self.tabs.addTab(scroll,'部門・運用条件')
        self.purpose=QComboBox();self.purpose.addItem('種目へエントリー','entry');self.purpose.addItem('全体をチェックログとして提出','checklog');self.purpose.setCurrentIndex(1 if context.get('submission_mode')=='checklog' else 0);form.addRow('提出目的',self.purpose)
        self.station_type=QComboBox();self.station_type.addItem('選択してください','')
        for label,value in [('個人局','individual'),('社団局','club'),('特別局・特別記念局','special')]:self.station_type.addItem(label,value)
        self.station_type.setCurrentIndex(max(0,self.station_type.findData(context.get('station_type',''))))
        if event.get('entrant',{}).get('station_types'):form.addRow('自局の局種（免許による）',self.station_type)
        self.fd_class=QComboBox();self.fd_class.addItem('選択してください','');self.fd_class.addItem('A：移動・第二マルチ2','A');self.fd_class.addItem('B：その他の移動・第二マルチ1','B');self.fd_class.addItem('ホーム：第二マルチ1','HOME');self.fd_class.setCurrentIndex(max(0,self.fd_class.findData(context.get('fd_class'))))
        self.fd_confirm=QCheckBox('移動目的・既設設備/電源の条件・移動表記を確認し、途中で局種を切り替えていない');self.fd_confirm.setChecked(context.get('fd_confirmed',False))
        if event.get('station_factor')=='jarl_fd':
            form.addRow('FD局種',self.fd_class);form.addRow(self.fd_confirm)
            note=QLabel('Aはコンテスト目的の移動で、既設無線設備・利用できる既設電源がない場所。施設で電池を使うだけではAになりません。ホームで電池を使っても係数1です。');note.setWordWrap(True);form.addRow(note)
        # Keep a hidden combo as the authoritative category value so the
        # existing scoring/event code stays untouched.  The visible picker opens
        # a dedicated dialog and writes the selected id back here.
        self.category=QComboBox(self);self.category.hide()
        for c in event['categories']:self.category.addItem(c['name']+' ['+c.get('submission_code',c['id'])+']',c['id'])
        idx=self.category.findData(context.get('category'));self.category.setCurrentIndex(idx if idx>=0 else -1)
        category_row=QWidget();category_layout=QHBoxLayout(category_row);category_layout.setContentsMargins(0,0,0,0);category_layout.setSpacing(6)
        self.category_display=QLineEdit();self.category_display.setReadOnly(True);self.category_display.setPlaceholderText('参加部門を選択してください')
        self.category_button=QPushButton('選択…');self.category_button.clicked.connect(self.choose_category)
        category_layout.addWidget(self.category_display,1);category_layout.addWidget(self.category_button);form.addRow('参加部門',category_row)
        self.power=QDoubleSpinBox();self.power.setRange(0,100000);self.power.setDecimals(3)
        self.power.setSuffix(' W');self.power.setValue(context.get('power',0));form.addRow('実運用の最大電力',self.power)
        self.operation_kind=QComboBox();self.operation_kind.addItem('選択してください','');self.operation_kind.addItem('移動しない運用','stationary');self.operation_kind.addItem('移動運用','portable');self.operation_kind.setCurrentIndex(max(0,self.operation_kind.findData(context.get('operation_kind',''))))
        if event.get('power_by_operation'):form.addRow('今回の運用形態',self.operation_kind)
        self.locations={}
        for ident,label in event.get('operating_locations',{}).get('groups',{}).items():
            w=QLineEdit(context.get('operating_locations',{}).get(ident,''));w.setPlaceholderText('具体的な運用場所。未運用の部門は空欄');form.addRow(label+'の運用地',w);self.locations[ident]=w
        if self.locations:
            note=QLabel('同一部門内の場所変更は禁止。デジタルは電信・電話のいずれかの運用地と同じにしてください。文字列は本人申告で、実際の同一地点を証明するものではありません。');note.setWordWrap(True);form.addRow(note)
        self.newcomer_requested=QCheckBox('ニューカマー記念品の対象として申告する（任意）');self.newcomer_requested.setChecked(context.get('newcomer_requested',False))
        self.newcomer_date=QLineEdit(context.get('newcomer_licensedate',''));self.newcomer_date.setPlaceholderText('YYYY-MM-DD（実運用者の初開局日）')
        self.newcomer_first=QCheckBox('初開局であり、再開局ではない');self.newcomer_first.setChecked(context.get('newcomer_first_license',False))
        if event.get('newcomer_claim'):
            claim=event['newcomer_claim'];form.addRow(self.newcomer_requested);form.addRow('初開局日',self.newcomer_date);form.addRow(self.newcomer_first)
            note=QLabel(f'対象期間 {claim["license_since"]}～{claim["license_until"]}。SOの個人局・社団局が対象です。部門コードや得点は変わりません。');note.setWordWrap(True);form.addRow(note)
        self.calendar=QPlainTextEdit();self.calendar.setMaximumHeight(115)
        self.calendar.setPlainText('\n'.join(w['start']+' / '+w['end'] for w in context.get('calendar_windows',event['windows'])))
        form.addRow('対象日時（'+event['timezone']+'・終了時刻を含まない）',self.calendar)
        notice=QLabel('初期値は規約の日時です。年度を含め変更できます。枠外の交信は警告のみで採点・出力を継続します。QSO原本の日時は変更しません。');notice.setWordWrap(True);form.addRow(notice)
        self.declarations={}
        for ident,label in event.get('regional',{}).get('declarations',{}).items():
            w=QLineEdit(context.get('declarations',{}).get(ident,''));form.addRow(label,w);self.declarations[ident]=w
        self.entry_categories={}
        if event.get('regional',{}).get('entry_set'):
            policy=event['regional']['entry_set'];note=QLabel(f'今回提出する全種目（最大{policy["max"]}件）を選択してください。出力は現在の種目ごとに独立して作成します。');note.setWordWrap(True);form.addRow(note)
            for c in event['categories']:
                w=QCheckBox(c['name']+' ['+c.get('submission_code',c['id'])+']');w.setChecked(c['id'] in context.get('entry_categories',[]));form.addRow(w);self.entry_categories[c['id']]=w
        self.flags={}
        self.confirm_group=QGroupBox('確認事項（全て確認して要チェック）');self.confirm_group.setStyleSheet('QGroupBox::title { color:#c62828; font-weight:700; }');self.confirm_layout=QVBoxLayout(self.confirm_group);form.addRow(self.confirm_group)
        names=event['required_flags']+[f for c in event['categories'] for f in c['required_flags']]+list(event.get('mode_confirmations',{}).values())
        if any('timing' in c for c in event['categories']):names.append(HISTORY_FLAG)
        from contest_participation import HISTORY as PARTICIPATION_HISTORY
        if any('participation' in c for c in event['categories']):names.append(PARTICIPATION_HISTORY)
        for text in filtered_flags(names):
            w=QCheckBox(text);w.setChecked(context.get('flags',{}).get(text,False));self.confirm_layout.addWidget(w);self.flags[text]=w
        self.summary=QLabel();self.summary.setWordWrap(True);form.addRow(self.summary)
        from contest_qualification_ui import QualificationPane
        self.qualification=QualificationPane(context);self.tabs.addTab(self.qualification,'参加資格・バンド別電力')
        from contest_participation_ui import ParticipationPane
        self.participation=ParticipationPane(context);self.tabs.addTab(self.participation,'担当交信数・家族運用')
        self.participation.ops.textChanged.connect(self.invalidate_participation)
        self.participation.child.textChanged.connect(self.invalidate_participation)
        self.fallback=button('一般種目へ変更',self.use_fallback);form.addRow(self.fallback)
        timing=QWidget();v=QVBoxLayout(timing);self.tabs.addTab(timing,'運用時間・バンド変更')
        self.time_summary=QLabel();self.time_summary.setWordWrap(True);v.addWidget(self.time_summary)
        self.blocks=QPlainTextEdit();self.blocks.setPlaceholderText('2026-08-22 21:00 / 2026-08-23 00:00\n2026-08-23 06:00 / 2026-08-23 12:00')
        self.blocks.setPlainText('\n'.join(b['start']+' / '+b['end'] for b in context.get('operating_blocks',[])))
        v.addWidget(self.blocks,1)
        self.block_help=QLabel('実際の運用開始 / 終了を1行ずつ入力します。終了時刻は含みません。\n例: 最後の交信が12:00なら、その分を含む終了は12:01。\n交信のない時間を自動的に休止扱いにはしません。');self.block_help.setWordWrap(True);v.addWidget(self.block_help)
        self.status=QLabel();self.status.setWordWrap(True);box.addWidget(self.status)
        row=QHBoxLayout();row.addStretch();row.addWidget(button('反映',self.apply));row.addWidget(button('キャンセル',self.reject));box.addLayout(row)
        self.category.currentIndexChanged.connect(self.category_changed)
        self.operation_kind.currentIndexChanged.connect(self.refresh)
        self.blocks.textChanged.connect(self.invalidate_history)
        self.refresh()
    def _sync_category_display(self):
        c=self.selected()
        self.category_display.setText('' if c is None else c['name']+' ['+c.get('submission_code',c['id'])+']')

    def choose_category(self):
        categories=self.event_spec.get('categories',[]);current=self.selected();station=self.station_type.currentData() or '';power=self.power.value()
        compatible=(lambda c:category_compatible(c,station,power))
        initial={}
        current_id=''
        if current is not None and compatible(current):
            initial=category_facets(current);current_id=current.get('id','')
        dialog=CategorySelectDialog(categories,current_id,self,initial_filters=initial,predicate=compatible)
        if dialog.exec() and dialog.selected_id is not None:
            index=self.category.findData(dialog.selected_id)
            if index>=0:self.category.setCurrentIndex(index)

    def selected(self):
        return next((c for c in self.event_spec['categories'] if c['id']==self.category.currentData()),None)
    def invalidate_history(self):
        if HISTORY_FLAG in self.flags:self.flags[HISTORY_FLAG].setChecked(False)
    def invalidate_participation(self):
        from contest_participation import HISTORY
        if HISTORY in self.flags:self.flags[HISTORY].setChecked(False)
    def category_changed(self):
        self.invalidate_history();self.refresh()
    def refresh(self):
        self._sync_category_display();c=self.selected();timing=c.get('timing',{}) if c else {}
        self.qualification.set_category(c)
        self.participation.set_category(c)
        for ident,w in self.declarations.items():w.setEnabled(bool(c and (ident in c.get('regional',{}).get('required_declarations',[]) or ident in ('abuta_locality','postal_confirmation','entry_band_sets','entry_basis','area_basis','kj_history','actual_location','youth_denominator') or ident=='junior_birthdate' and c.get('regional',{}).get('junior_since'))))
        self.fallback.setVisible(bool(c and c.get('fallback_category')))
        extras=([HISTORY_FLAG] if timing else [])
        mode_confirmations=self.event_spec.get('mode_confirmations',{})
        if c:
            allowed=set(c.get('modes',[]))
            extras.extend(text for mode,text in mode_confirmations.items() if '*' in allowed or mode in allowed)
        from contest_participation import HISTORY as PARTICIPATION_HISTORY
        if c and c.get('participation'):extras.append(PARTICIPATION_HISTORY)
        active=active_flags(self.event_spec,c,extras)
        for name,w in self.flags.items():w.setVisible(name in active)
        self.confirm_group.setVisible(bool(active))
        self.summary.setText('部門を選択してください。' if c is None else '対象バンド: '+', '.join(c['bands'])+'\n対象モード: '+', '.join(c['modes'])+f'\n規約の電力上限: {str(c["max_power"])+" W" if c["max_power"] is not None else "個別指定なし（免許範囲内）"}／バンド数 {c["min_bands"]}～{c["max_bands"]}')
        if c and c.get('station_types'):self.summary.setText(self.summary.text()+'\n参加局種: '+', '.join({'individual':'個人局','club':'社団局','special':'特別局'}[x] for x in c['station_types']))
        if self.event_spec.get('power_by_operation'):
            caps=self.event_spec['power_by_operation'];chosen=caps.get(self.operation_kind.currentData())
            self.summary.setText(self.summary.text()+f'\n運用形態別上限: 移動なし {caps["stationary"]}W／移動 {caps["portable"]}W。選択中の上限: {chosen if chosen is not None else "未選択"} W（入力電力は自動変更しません）')
        if c and 'min_power_exclusive' in c:self.summary.setText(self.summary.text()+f'\n電力区分の下限: {c["min_power_exclusive"]} W超')
        if c and c['modes']==['*']:self.summary.setText(self.summary.text().replace('対象モード: *','対象モード: 自局に許可された電波型式（本人確認）'))
        if c and c.get('operation_bands'):self.summary.setText(self.summary.text()+'\n運用可能バンド: '+', '.join(c['operation_bands'])+' MHz（採点外として隠しても参加条件は満たせません）')
        if c and c.get('required_mode_families'):self.summary.setText(self.summary.text()+'\n必要な運用: '+', '.join({'phone':'電話','cw':'電信','digital':'デジタル'}[m] for m in c['required_mode_families']))
        if c and c.get('excluded_band_subsets'):self.summary.setText(self.summary.text()+'\n全帯種目の除外構成: '+' ／ '.join(', '.join(bs)+'MHzだけ' for bs in c['excluded_band_subsets']))
        if self.event_spec.get('entrant',{}).get('checklog_only_types'):self.summary.setText(self.summary.text()+'\n記念局等の指定局種はチェックログで提出します。自動では切り替えません。')
        if self.event_spec.get('entrant',{}).get('guest_policy')=='forbidden':self.summary.setText(self.summary.text()+'\nゲスト運用はできません。SO/MOの可否は種目表に従います。')
        lines=[];o=timing.get('operating');b=timing.get('band_change')
        if c and c.get('scoring_windows'):
            lines.append('種目の採点時間（'+self.event_spec['timezone']+'、終了時刻は含みません）:\n'+'\n'.join(w['start']+' ～ '+w['end'] for w in c['scoring_windows'])+'\n対象日時は部門タブで変更できます。枠外は警告のみで処理を継続します。')
        if o:lines.append(f'入力時刻: {self.event_spec["timezone"]} ／ 運用上限 {o["max_minutes"]}分。\n{o["min_off_minutes"]}分未満の空白は運用時間に算入します。')
        if b:
            limit=f'変更後 {b["min_minutes"]}分以上滞在' if b['kind']=='stay' else f'正時からの1時間に最大 {b["max_changes"]}回変更'
            lines.append('バンド変更: '+limit+'\n系列: '+(', '.join(b['tx_ids']) if b['tx_ids'] else '全体で共通')+'。交信情報のTX欄で指定します。')
            lines.append('違反候補は'+('得点・マルチから除外します。' if b['on_violation']=='exclude' else '出力を停止して確認を求めます。'))
        self.time_summary.setText('\n\n'.join(lines) if lines else 'この部門には、運用時間・バンド変更の追加制限は設定されていません。')
        self.blocks.setEnabled(bool(o));self.block_help.setVisible(bool(o))
    def apply(self):
        try:
            c=self.selected()
            from contest_calendar import parse
            self.context['calendar_windows']=parse(self.calendar.toPlainText(),self.event_spec)
            self.context['calendar_advisory']=True
            if c is None and self.purpose.currentData()!='checklog':raise ValueError('参加部門を選択してください。')
            blocks=parse_blocks(self.blocks.toPlainText()) if c and c.get('timing',{}).get('operating') else self.context.get('operating_blocks',[])
            self.context.update(submission_mode=self.purpose.currentData(),fd_class=self.fd_class.currentData(),fd_confirmed=self.fd_confirm.isChecked(),category=c['id'] if c else '',power=self.power.value(),flags={text:w.isChecked() for text,w in self.flags.items()},operating_blocks=blocks)
            if self.event_spec.get('power_by_operation'):self.context['operation_kind']=self.operation_kind.currentData()
            if self.locations:self.context['operating_locations']={k:w.text().strip() for k,w in self.locations.items()}
            self.context['declarations']={k:w.text().strip() for k,w in self.declarations.items()}
            if self.entry_categories:self.context['entry_categories']=[k for k,w in self.entry_categories.items() if w.isChecked()]
            self.context.update(self.qualification.values())
            self.context.update(self.participation.values())
            if self.event_spec.get('newcomer_claim'):self.context.update(newcomer_requested=self.newcomer_requested.isChecked(),newcomer_licensedate=self.newcomer_date.text().strip(),newcomer_first_license=self.newcomer_first.isChecked())
            if self.event_spec.get('entrant',{}).get('station_types'):self.context['station_type']=self.station_type.currentData()
            self.accept()
        except ValueError as ex:self.status.setText(str(ex))
    def use_fallback(self):
        c=self.selected()
        if c and c.get('fallback_category'):
            self.category.setCurrentIndex(self.category.findData(c['fallback_category']))
            self.status.setText('一般種目へ変更しました。電力・運用者・確認事項を再確認して反映してください。')
