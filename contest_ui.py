from pathlib import Path
import html
from rule_source_ui import source_label,source_text
from contest_task_ui import run_task
from PySide6.QtCore import Qt,QTimer
from PySide6.QtWidgets import (QVBoxLayout,QHBoxLayout,QFormLayout,QWidget,QLineEdit,QLabel,QComboBox,QCheckBox,QListWidget,QListWidgetItem,QStackedWidget,QTableWidget,QTableWidgetItem,QAbstractItemView,QMessageBox,QScrollArea,QFrame,QGroupBox,QSizePolicy)
from window_geometry import SafeDialog
from window_tint import apply_window_tint
from search_ui import button
from search import file_identity,hits_to_rows
from remarks_sections import primary
from storage import StorageError,VERSION
from contest import FORMATS,select_logs,candidates,entries
from contest_rules import RuleStore,score,score_steps,default_rule,manual_score
from rule_view_data import is_contest_rule
from contest_rule_ui import RulesDialog,RuleEditor

def rule_number_candidates(rule,remarks,filter_text=''):
    found=candidates(remarks,filter_text)
    spec=(rule or {}).get('event',{}).get('exchange',{})
    if spec.get('kind') in ('numbered_region','literal_region'):
        allowed=set(spec.get('codes',[]))
        return [value for value in found if value in allowed],found
    return found,found

def sync_rule_exchange_fields(rule,draft):
    spec=(rule or {}).get('event',{}).get('exchange',{})
    received=str(draft.get('received','')).strip()
    if not received:return
    if spec.get('kind') in ('numbered_region','literal_region') and received in set(spec.get('codes',[])):
        draft['area']=spec.get('region_map',{}).get(received,received)

def uses_iburi_hidaka_joint(rule):
    return bool(rule and rule.get('id')=='iburi_hidaka')

def key(row):return (str(row[2]),row[3])
MANUAL_CONTEST="__manual_contest__"
class ContestDialog(SafeDialog):
    def __init__(self,repo,own='',parent=None,*,activity_name='コンテスト',hits=None):
        super().__init__(parent);self.repo=repo;self.imported_hits=list(hits or []);self.selection=None;self.draft={};self.loaded_scope=None;self.page=0;self.loading=False;self.result=None;self.rule=None;self.rule_snapshot=None;self.rule_path=None
        self.event_contexts={};self.activity_name=activity_name;self._contest_match_count=0;self._own_scroll_area=True;self.setWindowTitle(f'{activity_name}提出ログ作成 — PSLog Ver{VERSION}');self.resize(1130,710);apply_window_tint(self,'contest')
        outer=QVBoxLayout(self);outer.setContentsMargins(6,6,6,6)
        body=QWidget();box=QVBoxLayout(body);box.setContentsMargins(0,0,0,0)
        self.heading=QLabel();box.addWidget(self.heading);self.stack=QStackedWidget();box.addWidget(self.stack,1)
        self.workflow_scroll=QScrollArea();self.workflow_scroll.setWidgetResizable(True);self.workflow_scroll.setFrameShape(QFrame.NoFrame);self.workflow_scroll.setWidget(body);outer.addWidget(self.workflow_scroll,1)
        w=QWidget();f=QFormLayout(w);self.stack.addWidget(w)
        self.contest_search=QLineEdit();self.contest_search.setPlaceholderText('コンテスト名・参照年で検索（スペース区切りAND）');f.addRow('コンテスト検索',self.contest_search)
        self.early_rules=QComboBox();f.addRow('コンテスト・年度',self.early_rules)
        self.manual_name=QLineEdit();self.manual_name.setPlaceholderText('コンテスト名を入力');f.addRow('コンテスト名（手入力）',self.manual_name)
        self.manual_year=QLineEdit();self.manual_year.setMaxLength(4);self.manual_year.setText(str(__import__('datetime').datetime.now().year));self.manual_year.setPlaceholderText('YYYY');f.addRow('参照年',self.manual_year)
        self.format=QComboBox();self.format.addItems(FORMATS);f.addRow('提出形式',self.format)
        self.format_note=QLabel(f'まず{activity_name}を選択してください。登録済み大会では規約に登録された提出形式だけを表示します。');self.format_note.setWordWrap(True);f.addRow(self.format_note)
        self.early_event_button=button('参加部門・運用条件を設定…',self.event_details);f.addRow('参加部門・運用条件',self.early_event_button)
        self.early_event_summary=QLabel();self.early_event_summary.setWordWrap(True);f.addRow(self.early_event_summary)
        self.overview_group=QGroupBox('コンテスト概要');overview_layout=QVBoxLayout(self.overview_group);overview_layout.setContentsMargins(8,8,8,8)
        self.overview_scroll=QScrollArea();self.overview_scroll.setWidgetResizable(True);self.overview_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff);self.overview_scroll.setFrameShape(QFrame.StyledPanel)
        self.overview_label=QLabel();self.overview_label.setWordWrap(True);self.overview_label.setAlignment(Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignTop);self.overview_label.setTextFormat(Qt.TextFormat.RichText);self.overview_label.setMargin(7);self.overview_label.setStyleSheet('color:#202020; background:#ffffff;')
        overview_font=self.overview_label.font();overview_font.setPointSize(max(7,overview_font.pointSize()-1));self.overview_label.setFont(overview_font)
        self.overview_scroll.setWidget(self.overview_label);overview_layout.addWidget(self.overview_scroll);self.overview_group.setMinimumHeight(285);self.overview_group.setVisible(False);f.addRow(self.overview_group)
        self._set_stage1_rows(False,False)
        w=QWidget();v=QVBoxLayout(w);self.stack.addWidget(w);source_form=QWidget();source_form.setSizePolicy(QSizePolicy.Policy.Preferred,QSizePolicy.Policy.Fixed);f=QFormLayout(source_form);f.setContentsMargins(0,0,0,0);v.addWidget(source_form,0,Qt.AlignmentFlag.AlignTop);self.search=QLineEdit(own);self.own=QComboBox();f.addRow('自局コールで検索',self.search);f.addRow('対象の自局（運用サフィックスを区別）',self.own)
        self.joint=QCheckBox('胆振日高：常置と同じ基本コール/8のログを一緒に選ぶ');f.addRow(self.joint);self.joint.setVisible(False);self.joint.toggled.connect(self.find_logs)
        self.logs=QListWidget();self.logs.setMinimumHeight(120);self.logs.setMaximumHeight(180);v.addWidget(self.logs)
        row=QHBoxLayout();row.addWidget(button('すべて選択',lambda:self.check_all(True)));row.addWidget(button('選択解除',lambda:self.check_all(False)));row.addWidget(button('対象を再読込',self.reload_target));v.addLayout(row)
        f=QFormLayout();v.addLayout(f);self.start=QLineEdit();self.end=QLineEdit()
        for e in (self.start,self.end):e.setPlaceholderText('YYYYMMDDhhmm・先頭だけでも可（空欄は制限なし）')
        f.addRow('開始（JST）',self.start);f.addRow('終了（JST・含む）',self.end)
        period_note=QLabel('空欄は制限なし。開始は指定期間の先頭、終了は指定期間の末尾として扱います。例：終了 20260917 → 2026/09/17 23:59');period_note.setWordWrap(True);f.addRow(period_note)
        self.rmks=QLineEdit();f.addRow('RMKSに含む文字（任意）',self.rmks);from activity_filters import FilterPane;self.filters=FilterPane();v.addWidget(self.filters)
        self.imported_note=QLabel();self.imported_note.setWordWrap(True);v.addWidget(self.imported_note);self.imported_note.setVisible(bool(self.imported_hits))
        if self.imported_hits:self.imported_note.setText(f'【ログ検索結果を使用中】 チェック済み {len(self.imported_hits):,}交信をそのまま提出候補に使用します。対象ログ・期間・RMKS・バンド/モードの再指定は行いません。')
        w=QWidget();v=QVBoxLayout(w);self.stack.addWidget(w)
        send_note=QLabel('同じ送信ナンバーを全交信で使うコンテストは、ここへ入力して一括設定します。\n交信ごとに送信ナンバーが変わる場合は、下の「送信番号」を個別に確認・修正してください。')
        send_note.setWordWrap(True);send_note.setStyleSheet('color:#44515a; padding-bottom:1px;');v.addWidget(send_note)
        send_arrow=QLabel('↓↓↓');send_arrow.setSizePolicy(QSizePolicy.Policy.Preferred,QSizePolicy.Policy.Fixed);send_arrow.setStyleSheet('color:#44515a; padding:0 0 0 2px;');v.addWidget(send_arrow)
        send_form=QFormLayout();self.sent=QLineEdit();self.sent.setPlaceholderText('例：09009 / PM95 / 001A')
        send_row=QWidget();send_layout=QHBoxLayout(send_row);send_layout.setContentsMargins(0,0,0,0);send_layout.setSpacing(6)
        send_layout.addWidget(self.sent,1);send_layout.addWidget(button('空欄の送信番号へ一括設定',self.fill_sent))
        send_form.addRow('自局のコンテストナンバー（共通送信番号）',send_row);v.addLayout(send_form)
        rmks_actions=QHBoxLayout()
        self.reextract_button=button('受信ナンバー候補をRMKSから再抽出',self.extract)
        self.rmks_all_button=button('RMKSを受信ナンバーとして全て入れる',self.fill_received_from_rmks)
        rmks_actions.addWidget(self.reextract_button,1);rmks_actions.addWidget(self.rmks_all_button,1);v.addLayout(rmks_actions)
        confirm_note=QLabel('受信ナンバーは規約に合う候補を自動抽出済みです。一覧は10件ずつ切り替えて確認できます。\n自動抽出された候補をまとめて承認する場合は、右下の「全件を確認済みにする」を押してください。候補なし・複数候補・規約外候補は個別修正が必要です。地域・マルチ抽出元は規約から自動補完します。元ログは変更しません。')
        confirm_note.setWordWrap(True);confirm_note.setStyleSheet('background:#fff2cf; border:1px solid #ddc77f; padding:6px; color:#4c4226;');v.addWidget(confirm_note)
        self.review_page_size=10
        self.table=QTableWidget(0,12);self.table.setHorizontalHeaderLabels(['日時 JST','相手コール','BAND / MODE','RMKS','送信番号','受信番号','地域','プリフィックス','確認状態','国・地域名','大陸','提出対象'])
        self.table.verticalHeader().setDefaultSectionSize(26);self.table.setMinimumHeight(250);self.table.setMaximumHeight(320);v.addWidget(self.table)
        for i,width in enumerate([145,95,100,170,85,85,70,85,125]):self.table.setColumnWidth(i,width)
        self.table.itemChanged.connect(self.changed)
        row=QHBoxLayout();self.prev_page=button('前の10件',lambda:self.move_page(-1));self.next_page=button('次の10件',lambda:self.move_page(1));self.page_label=QLabel()
        row.addWidget(self.prev_page);row.addWidget(self.page_label);row.addWidget(self.next_page);row.addStretch();row.addWidget(button('提出対象を全選択',lambda:self.select_review(True)));row.addWidget(button('提出対象を全解除',lambda:self.select_review(False)));v.addLayout(row)
        hints=QHBoxLayout();hints.addWidget(button('JCC/JCGから県コードを補助入力…',self.area_hints));hints.addWidget(button('国・地域／大陸の候補を参照…',self.country_hints));hints.addStretch();v.addLayout(hints)
        w=QWidget();v=QVBoxLayout(w);self.stack.addWidget(w)
        guide=QLabel('ここは選択したコンテスト規約による自動採点結果の確認画面です。通常は得点・マルチを確認して「確認して次へ」で進みます。\n未確認が残っている場合は、下の案内に従って「参加部門・運用条件を変更…」または「戻る」で修正してください。規約ファイル自体をここで編集する必要はありません。')
        guide.setWordWrap(True);guide.setStyleSheet('background:#e7f0f7; border:1px solid #b8cad8; padding:7px; color:#243746;')
        v.addWidget(guide)
        warning=QLabel(f'{activity_name}規約は毎年改定される可能性があります。参照年と公式規約を確認してください。');warning.setStyleSheet('color:#b32020');v.addWidget(warning)
        row=QHBoxLayout();self.rules=QComboBox();self.rules.setEnabled(False);self.rules.setToolTip('段階1で選択したコンテストルールです。ここでは参照のみです。');row.addWidget(self.rules,1)
        self.event_change_button=button('参加部門・運用条件を変更…',self.event_details);row.addWidget(self.event_change_button)
        self.qso_detail_button=button('不足情報（GL・TX等）を補完…',self.qso_details);row.addWidget(self.qso_detail_button);v.addLayout(row)
        self.rule_source=source_label();v.addWidget(self.rule_source);self.result_label=QLabel();self.result_label.setWordWrap(True);v.addWidget(self.result_label);
        from contest_score_ui import ScoreView
        self.score_view=ScoreView();self.score_table=self.score_view.table;v.addWidget(self.score_view,1)
        from contest_submit_ui import SubmissionPane
        self.submission=SubmissionPane(self);self.stack.addWidget(self.submission)
        self.status=QLabel();self.status.setWordWrap(True);outer.addWidget(self.status)
        row=QHBoxLayout();self.back=button('戻る',self.go_back);self.confirm_page_button=button('全件を確認済みにする',self.confirm_page);self.confirm_page_button.setVisible(False);self.next=button('次へ',self.advance)
        self.submit_prepare_button=self.submission.prepare_button;self.submit_save_button=self.submission.save_button
        self.submit_prepare_button.setVisible(False);self.submit_save_button.setVisible(False)
        row.addWidget(self.back);row.addStretch();row.addWidget(self.confirm_page_button);row.addWidget(self.submit_prepare_button);row.addWidget(self.submit_save_button);row.addWidget(self.next);row.addWidget(button('閉じる',self.reject));outer.addLayout(row)
        self.timer=QTimer(self);self.timer.setSingleShot(True);self.timer.timeout.connect(self.calculate);self.rules.currentIndexChanged.connect(self.schedule);self.search.textChanged.connect(self.find_calls);self.own.currentTextChanged.connect(self.find_logs)
        self.contest_search.textChanged.connect(self.filter_contests);self.early_rules.currentIndexChanged.connect(self.choose_early_rule);self.manual_name.textChanged.connect(self.manual_changed);self.manual_year.textChanged.connect(self.manual_changed);self.format.currentIndexChanged.connect(self.navigate)
        self.score_job=None;self.chunk_timer=QTimer(self);self.chunk_timer.setInterval(0);self.chunk_timer.timeout.connect(self.score_chunk)
        self.find_calls();self.refresh_rules();self.navigate()
        if self.imported_hits:
            for widget in (self.search,self.own,self.logs,self.joint,self.start,self.end,self.rmks,self.filters):widget.setEnabled(False)
        for label in self.findChildren(QLabel):label.setWordWrap(True)
    def _set_stage1_rows(self,manual,show_format):
        form=self.stack.widget(0).layout()
        for field,visible in ((self.manual_name,manual),(self.manual_year,manual),(self.format,show_format)):
            field.setVisible(visible)
            label=form.labelForField(field)
            if label:label.setVisible(visible)
    def _search_value(self,text):
        import unicodedata
        text=unicodedata.normalize('NFKC',str(text)).strip().casefold()
        return ''.join(chr(ord(c)-0x60) if 'ァ'<=c<='ヶ' else c for c in text)
    def filter_contests(self,*args,preferred=None):
        if not hasattr(self,'early_rules'):return
        current=self.early_rules.currentData() if preferred is None else preferred
        tokens=[self._search_value(x) for x in self.contest_search.text().split() if x.strip()]
        self.early_rules.blockSignals(True);self.early_rules.clear();self.early_rules.addItem('コンテストを選択してください',None)
        matches=[item for item in getattr(self,'rule_catalog',[]) if all(t in item['search'] for t in tokens)]
        self._contest_match_count=len(matches)
        for item in matches:self.early_rules.addItem(item['label'],item['path'])
        self.early_rules.insertSeparator(self.early_rules.count());self.early_rules.addItem('その他のコンテスト（手動）',MANUAL_CONTEST)
        i=self.early_rules.findData(current)
        self.early_rules.setCurrentIndex(i if i>=0 else 0);self.early_rules.blockSignals(False)
        self.choose_early_rule(self.early_rules.currentIndex())
    def _contest_search_guidance(self):
        query=self.contest_search.text().strip()
        if not query:return f'まず{self.activity_name}を選択してください。登録済み大会では規約に登録された提出形式だけを表示します。'
        if self._contest_match_count:return f'{self._contest_match_count}件の候補があります。コンテストを選択してください。'
        return '一致するコンテストがありません。検索語を変更するか「その他のコンテスト（手動）」を選択してください。'
    def _apply_contest_search_guidance(self,text):
        self.format_note.setText(text)
        if '件の候補があります。コンテストを選択してください。' in text:
            self.format_note.setStyleSheet('font-size:13pt; font-weight:700; color:#244f79; padding:3px 0;')
        elif text.startswith('一致するコンテストがありません。'):
            self.format_note.setStyleSheet('font-size:12pt; font-weight:600; color:#9a2f19; padding:3px 0;')
        else:self.format_note.setStyleSheet('')
    def _set_formats(self,formats,*,manual=False,note=''):
        previous=self.format.currentText();visible=bool(formats);items=list(formats) if visible else list(FORMATS);self.format.blockSignals(True);self.format.clear()
        for fmt in items:self.format.addItem(fmt)
        if previous in items:self.format.setCurrentText(previous)
        elif items:self.format.setCurrentIndex(0)
        self.format.blockSignals(False);self.format.setEnabled(visible and (manual or len(items)>1))
        self._set_stage1_rows(manual,visible);self._apply_contest_search_guidance(note);self.navigate()
    def active_rule(self):
        if self.manual_mode():return self.manual_rule()
        path=self.rules.currentData()
        return RuleStore(self.repo.root).read(path)[0] if path else None
    def event_setup_state(self):
        if self.manual_mode():
            return True,'その他のコンテスト：参加条件は手動確認です。'
        path=self.rules.currentData() if hasattr(self,'rules') else None
        if not path:
            return False,'コンテストを選択してください。'
        try:
            rule,_=RuleStore(self.repo.root).read(path)
        except (ValueError,OSError,StorageError) as e:
            return False,'参加条件を読み込めません：'+str(e)
        event=rule.get('event',{})
        categories=event.get('categories',[])
        if not categories:
            return True,'このルールには参加部門の追加設定はありません。'
        context=self.event_context()
        if context.get('submission_mode')=='checklog':
            return True,'設定済み：チェックログとして提出'
        category=context.get('category','')
        selected=next((c for c in categories if c.get('id')==category),None)
        if not selected:
            return False,'未設定（必須）：参加部門・運用条件を先に設定してください。'
        parts=['設定済み：'+selected.get('name',category)]
        power=context.get('power')
        if power not in (None,'',0,0.0):parts.append(f'最大 {power:g} W')
        station={'individual':'個人局','club':'社団局','special':'特別局・特別記念局'}.get(context.get('station_type'))
        if station:parts.append(station)
        operation={'stationary':'移動しない運用','portable':'移動運用'}.get(context.get('operation_kind'))
        if operation:parts.append(operation)
        return True,' ／ '.join(parts)
    def update_event_setup_ui(self):
        if not hasattr(self,'early_event_button'):return
        manual=self.manual_mode()
        selected=self.early_rules.currentData() if hasattr(self,'early_rules') else None
        visible=selected is not None and not manual
        self.early_event_button.setVisible(visible)
        self.early_event_summary.setVisible(selected is not None)
        if selected is None:
            self.early_event_summary.setText('')
            return
        ok,text=self.event_setup_state()
        self.early_event_summary.setText(text)
        self.early_event_summary.setStyleSheet('color:#2f5f3b;' if ok else 'color:#b32020; font-weight:600;')
        self.early_event_button.setText('参加部門・運用条件を変更…' if ok else '参加部門・運用条件を設定…')
    def update_contest_overview(self,rule):
        if not hasattr(self,'overview_group'):return
        if not rule or self.manual_mode():
            self.overview_group.setVisible(False);self.overview_label.clear();return
        from contest_overview import overview_rows
        rows=overview_rows(rule)
        parts=[]
        for label,text,important in rows:
            color='#0b5fa5' if important else '#202020'
            weight='600' if important else '400'
            parts.append('<div style="margin:0 0 5px 0;color:%s;font-weight:%s;"><b>%s：</b>%s</div>'%(color,weight,html.escape(str(label)),html.escape(str(text)).replace('\n','<br>')))
        self.overview_label.setText(''.join(parts));self.overview_group.setVisible(True)

    def manual_mode(self):return self.early_rules.currentData()==MANUAL_CONTEST
    def manual_rule(self):
        name=self.manual_name.text().strip()
        if not name:raise ValueError('その他のコンテストではコンテスト名を入力してください。')
        try:year=int(self.manual_year.text().strip())
        except ValueError:raise ValueError('参照年を4桁で入力してください。')
        if not 1900<=year<=9999:raise ValueError('参照年を4桁で入力してください。')
        r=default_rule();r.update(id='manual_other',name=name,year=year,url='',organizer='')
        r['points']={'phone':0,'cw':0,'digital':0};r['multi1'].update(kind='off',per_band=False);r['multi2'].update(kind='off',value=1);return r
    def manual_changed(self,*args):
        if self.manual_mode():self.schedule();self.navigate()
    def choose_early_rule(self,index):
        data=self.early_rules.itemData(index) if 0<=index<self.early_rules.count() else None
        self.start.clear();self.end.clear()
        if data is None:
            self.update_target_special_options(None);self.update_contest_overview(None)
            self.rules.setEnabled(True);self.rules.setCurrentIndex(0);self._set_formats([],note=self._contest_search_guidance());self.schedule();return
        if data==MANUAL_CONTEST:
            self.update_target_special_options(None);self.update_contest_overview(None)
            self.rules.setCurrentIndex(0);self.rules.setEnabled(False)
            formats=[x for x in FORMATS if x!='所定様式PDF']
            self._set_formats(formats,manual=True,note='その他のコンテスト：規約連動・自動採点は行いません。大会名・提出形式・提出情報を手動で指定します。所定様式PDFは大会固有のため選べません。')
            self.schedule();return
        i=self.rules.findData(data)
        if i>=0:self.rules.setCurrentIndex(i)
        self.rules.setEnabled(False)
        try:
            from datetime import datetime,timedelta
            r,_=RuleStore(self.repo.root).read(data);self.update_target_special_options(r);self.update_contest_overview(r);submit=r.get('event',{}).get('submission',{});formats=list(submit.get('formats',()))
            if not formats:
                formats=[x for x in FORMATS if x!='所定様式PDF'];note='このルールには提出形式が登録されていないため、形式を手動選択します。'
            else:note='規約登録の提出形式: '+(' / '.join(formats))+('（自動選択）' if len(formats)==1 else '（この中から選択）')
            self._set_formats(formats,note=note)
            windows=r.get('event',{}).get('windows',[])
            if windows:
                self.start.setText(datetime.strptime(min(w['start'] for w in windows),'%Y-%m-%d %H:%M').strftime('%Y%m%d%H%M'));self.end.setText((datetime.strptime(max(w['end'] for w in windows),'%Y-%m-%d %H:%M')-timedelta(minutes=1)).strftime('%Y%m%d%H%M'))
        except (ValueError,OSError,StorageError) as e:
            self.update_target_special_options(None);self.update_contest_overview(None);self.status.setText(str(e))
        self.schedule();self.navigate()
    def update_target_special_options(self,rule=None):
        show=uses_iburi_hidaka_joint(rule)
        if not show and self.joint.isChecked():
            self.joint.blockSignals(True);self.joint.setChecked(False);self.joint.blockSignals(False)
            self.find_logs()
        self.joint.setVisible(show)

    def find_calls(self):
        previous=self.own.currentText();self.own.clear();names=set()
        for p in self.repo.book.glob('*.txt'):
            ident=file_identity(p)
            if ident and self.search.text().strip().upper() in ident[1]:names.add(ident[1])
        self.own.addItems(sorted(names))
        if previous in names:self.own.setCurrentText(previous)
        self.find_logs()
    def find_logs(self):
        self.logs.clear()
        if not self.own.currentText():return
        calls=[self.own.currentText()]
        if self.joint.isChecked():
            from contest_regional import base_call
            b=base_call(calls[0]);calls=[b,b+'/8']
        for p in sorted({p for call in calls for p in self.repo.files(call)}):
            item=QListWidgetItem(p.name);item.setData(Qt.UserRole,str(p));item.setToolTip(str(p.resolve()));item.setFlags(item.flags()|Qt.ItemIsUserCheckable);item.setCheckState(Qt.Unchecked);self.logs.addItem(item)
    def check_all(self,on):
        for i in range(self.logs.count()):self.logs.item(i).setCheckState(Qt.Checked if on else Qt.Unchecked)
    def scope(self):return (self.own.currentText(),tuple(self.logs.item(i).data(Qt.UserRole) for i in range(self.logs.count()) if self.logs.item(i).checkState()==Qt.Checked),self.start.text(),self.end.text(),self.rmks.text().strip(),self.joint.isChecked(),self.filters.state())
    def load_target(self,force=False):
        if self.imported_hits:
            for hit in self.imported_hits:
                hit.snapshot.check(hit.path)
            from sota_export import Selection
            sessions,rows=hits_to_rows(self.imported_hits)
            if not rows:raise ValueError('チェック済みの交信がありません。')
            owns={row[0] for row in rows}
            if len(owns)!=1:raise ValueError('チェック済み交信に複数の自局コールが含まれています。')
            marker=('__search_checked__',tuple((str(h.path),h.line) for h in self.imported_hits))
            if not force and self.selection and self.loaded_scope==marker:
                for session in self.selection.sessions:session.snapshot.check(session.path)
                return True
            self.selection=Selection(sessions,rows);self.review_rows=list(rows);self.loaded_scope=marker;self.draft={};self.result=None;self.page=0
            return True
        s=self.scope()
        if not force and self.selection and s==self.loaded_scope:
            for session in self.selection.sessions:session.snapshot.check(session.path)
            return True
        new=run_task(self,'対象ログを読み込んでいます',lambda:select_logs(self.repo,s[1],s[0],s[2],s[3],s[4],joint=s[5]))
        new.rows=[r for r in new.rows if self.filters.accepts(r[1])]
        if not new.rows:raise ValueError('バンド・モード条件に一致する交信がありません。')
        if self.draft and QMessageBox.question(self,'対象変更','対象の変更により交信ナンバーと採点を初期化します。続けますか？')!=QMessageBox.Yes:return False
        self.selection=new;self.review_rows=list(new.rows);self.loaded_scope=s;self.draft={};self.result=None;self.page=0
        try:
            from contest_timing import HISTORY_FLAG
            from contest_participation import HISTORY as PARTICIPATION_HISTORY
            for context in self.event_contexts.values():
                flags=context.get('flags',{})
                flags.pop(HISTORY_FLAG,None);flags.pop(PARTICIPATION_HISTORY,None)
        except Exception:pass
        return True
    def reload_target(self):
        try:
            if self.load_target(True):self.status.setText(f'対象 {len(self.selection.rows):,}件を再読込しました。');self.draw()
        except (ValueError,OSError,StorageError) as e:self.status.setText(str(e))
    def pending_review_count(self):
        rows=getattr(self,'review_rows',self.selection.rows if self.selection else [])
        pending=0
        for row in rows:
            d=self.draft.get(key(row),{})
            if d.get('excluded'):continue
            status=str(d.get('status',''))
            if status=='候補・要確認' or status=='候補なし' or status.startswith('複数候補:') or status.startswith('規約外候補:'):
                pending+=1
        return pending

    def navigate(self,*args):
        i=self.stack.currentIndex();manual=self.manual_mode() if hasattr(self,'early_rules') else False
        self.heading.setText(['1　コンテスト選択','2　対象ログ','3　交信ナンバー確認','4　提出用確認（自動採点なし）' if manual else '4　得点とマルチ（確認）','5　提出情報と出力'][i]);self.back.setEnabled(i>0)
        final_stage=i==4
        self.submit_prepare_button.setVisible(final_stage);self.submit_save_button.setVisible(final_stage);self.next.setVisible(not final_stage)
        enabled=i<4
        if i==0:
            selected=self.early_rules.currentData() if hasattr(self,'early_rules') else None
            enabled=selected is not None and bool(self.format.currentText())
            if selected==MANUAL_CONTEST:
                try:self.manual_rule()
                except ValueError:enabled=False
            elif selected is not None:
                ready,_=self.event_setup_state();enabled=enabled and ready
            self.update_event_setup_ui()
        if i==2:
            pending=self.pending_review_count()
            enabled=bool(self.selection and self.selection.rows) and pending==0
            self.confirm_page_button.setVisible(True);self.next.setText('次へ')
            if pending:self.status.setText(f'未確認の交信が {pending}件あります。「全件を確認済みにする」で自動候補を一括確認できます。候補なし・複数候補・規約外候補は個別に修正してください。')
            elif self.status.text().startswith('未確認の交信が '):self.status.clear()
        else:
            self.confirm_page_button.setVisible(False)
            self.next.setText('対象を読み込んで次へ' if i==1 else '確認して次へ' if i==3 else '次へ')
        self.next.setEnabled(enabled)
    def advance(self):
        try:
            i=self.stack.currentIndex()
            if i==1:
                if not self.load_target():return
                self.extract(redraw=False,automatic=True)
                self.draw()
            if i==2:
                pending=self.pending_review_count()
                if pending:raise ValueError(f'未確認の交信が {pending}件あります。「全件を確認済みにする」で自動候補を確認するか、候補なし・複数候補・規約外候補を個別に修正してから次へ進んでください。')
                self.selection.rows=[r for r in getattr(self,'review_rows',self.selection.rows) if not self.draft.get(key(r),{}).get('excluded',False)]
                if not self.selection.rows:raise ValueError('提出対象を1件以上選択してください。')
                self.schedule()
            if i==3:
                if self.score_job is not None:raise ValueError('採点中です。完了をお待ちください。')
                if self.result is None:
                    self.timer.stop();self.calculate()
                else:
                    if self.rule_snapshot is not None and self.rule_path is not None:self.rule_snapshot.check(Path(self.rule_path))
                    for session in self.selection.sessions:session.snapshot.check(session.path)
                if self.result is None:
                    raise ValueError('採点結果を作成できません。対象ログ・参加部門・交信ナンバーを確認してください。')
                if self.result.total is None and not (getattr(self.result,'unscored_submission',False) and not self.result.problems and not any(d.get('status')=='候補・要確認' for d in self.draft.values())):
                    confirmations=[p for p in self.result.problems if str(p).startswith('未確認: ')]
                    pending=sum(self.draft.get(key(row),{}).get('status')=='候補・要確認' for row in self.selection.rows)
                    if confirmations:raise ValueError('参加部門・運用条件に未確認項目が残っています。「参加部門・運用条件を変更…」を開いて確認してください。')
                    if pending:raise ValueError(f'交信ナンバーの未確認が {pending}件残っています。「戻る」で確認してください。')
                    raise ValueError('判定エラーが残っています。表の「根拠・確認状態」を確認してください。')
                self.submission.set_context()
            if i<4:self.stack.setCurrentIndex(i+1)
            self.status.clear();self.navigate()
        except (ValueError,OSError,StorageError) as e:self.status.setText(str(e))
    def go_back(self):
        self.cancel_score();self.timer.stop();self.stack.setCurrentIndex(max(0,self.stack.currentIndex()-1));self.navigate()
        if self.stack.currentIndex()==2 and hasattr(self,'review_rows'):
            self.selection.rows=list(self.review_rows);self.draw()
    def draw(self):
        self.loading=True;rows=getattr(self,'review_rows',self.selection.rows);self.table.setRowCount(0)
        for i,row in enumerate(rows[self.page*self.review_page_size:(self.page+1)*self.review_page_size]):
            q=row[1];d=self.draft.get(key(row),{});self.table.insertRow(i)
            for j,value in enumerate([q.date+' '+q.time,q.call,q.band+' / '+q.mode,q.remarks,d.get('sent',''),d.get('received',''),d.get('area',''),d.get('prefix',''),d.get('status',''),d.get('country',''),d.get('continent','')]):
                item=QTableWidgetItem(value);item.setToolTip(value)
                if j not in (4,5,6,7,9,10):item.setFlags(item.flags()&~Qt.ItemIsEditable)
                self.table.setItem(i,j,item)
            item=QTableWidgetItem();item.setFlags(Qt.ItemIsEnabled|Qt.ItemIsUserCheckable);item.setCheckState(Qt.Unchecked if d.get('excluded') else Qt.Checked);self.table.setItem(i,11,item)
        n=max(1,(len(rows)+self.review_page_size-1)//self.review_page_size);self.page_label.setText(f'{self.page+1}/{n}ページ・最大{self.review_page_size}件表示／全{len(rows):,}件');self.prev_page.setEnabled(self.page>0);self.next_page.setEnabled(self.page+1<n);self.loading=False
    def select_review(self,on):
        for row in getattr(self,'review_rows',self.selection.rows):self.draft.setdefault(key(row),{})['excluded']=not on
        self.result=None;self.draw();self.navigate()
    def changed(self,item):
        if self.loading:return
        if item.column()==11:
            r=getattr(self,'review_rows',self.selection.rows)[self.page*self.review_page_size+item.row()];self.draft.setdefault(key(r),{})['excluded']=item.checkState()!=Qt.Checked;self.result=None;self.navigate();return
        if item.column() not in (4,5,6,7,9,10):return
        d=self.draft.setdefault(key(getattr(self,'review_rows',self.selection.rows)[self.page*self.review_page_size+item.row()]),{});d[{4:'sent',5:'received',6:'area',7:'prefix',9:'country',10:'continent'}[item.column()]]=item.text().strip()
        if item.column()==5:
            try:sync_rule_exchange_fields(self.active_rule(),d)
            except (ValueError,OSError,StorageError):pass
            d['status']='手入力';self.loading=True;self.table.item(item.row(),6).setText(d.get('area',''));self.table.item(item.row(),8).setText('手入力');self.loading=False
        self.result=None;self.navigate()
    def move_page(self,delta):self.page+=delta;self.draw();self.navigate()
    def fill_sent(self):
        value=self.sent.text().strip()
        for row in self.selection.rows:
            d=self.draft.setdefault(key(row),{})
            if not d.get('sent'):d['sent']=value
        self.draw();self.result=None
    def fill_received_from_rmks(self,*args,ask=True):
        if not self.selection:return
        rows=getattr(self,'review_rows',self.selection.rows)
        if ask:
            text=(f'対象 {len(rows):,}交信の受信ナンバーを、各QSOのRMKS内容でそのまま上書きします。\n\n'
                  '規約に合う値かどうかを自動抽出せずに設定する自己責任機能です。\n'
                  '元のPSLogログのRMKSは変更しません。\n\n実行しますか？')
            if QMessageBox.question(self,'RMKSを受信ナンバーとして一括設定',text,QMessageBox.Yes|QMessageBox.No,QMessageBox.No)!=QMessageBox.Yes:return
        try:rule=self.active_rule()
        except (ValueError,OSError,StorageError):rule=None
        for row in rows:
            d=self.draft.setdefault(key(row),{})
            value=primary(row[1].remarks).strip()
            d['received']=value
            if value:
                sync_rule_exchange_fields(rule,d);d['status']='手入力（RMKS一括）'
            else:
                d['status']='候補なし'
        self.draw();self.result=None;self.navigate()

    def extract(self,*args,redraw=True,automatic=False):
        if not self.selection:return
        try:rule=self.active_rule()
        except (ValueError,OSError,StorageError):rule=None
        for row in self.selection.rows:
            d=self.draft.setdefault(key(row),{})
            if d.get('received'):
                sync_rule_exchange_fields(rule,d)
                continue
            valid,raw=rule_number_candidates(rule,row[1].remarks,self.loaded_scope[4] if self.loaded_scope else '')
            if len(valid)==1:
                d['received']=valid[0];sync_rule_exchange_fields(rule,d);d['status']='候補・要確認'
            elif len(valid)>1:
                d['status']='複数候補: '+', '.join(valid)
            elif raw and rule and (rule.get('event',{}).get('exchange',{}).get('kind') in ('numbered_region','literal_region')):
                d['status']='規約外候補: '+', '.join(raw)
            elif len(raw)>1:
                d['status']='複数候補: '+', '.join(raw)
            elif len(raw)==1:
                d['received']=raw[0];d['status']='候補・要確認'
            else:
                d['status']='候補なし'
        if redraw:self.draw()
        self.result=None
    def confirm_page(self):
        # Ver1.03: 表示ページに関係なく、自動抽出済みの候補を全件まとめて確認済みにする。
        # 「候補なし」「複数候補」「規約外候補」は誤承認を避けるため残し、個別修正を求める。
        rows=getattr(self,'review_rows',self.selection.rows)
        for row in rows:
            d=self.draft.get(key(row),{})
            if d.get('excluded'):continue
            if d.get('status')=='候補・要確認':d['status']='確認済み'
        self.draw();self.result=None;self.navigate()
    def area_hints(self):
        if not self.selection:return
        try:
            from contest_area_ui import AreaDialog
            dialog=AreaDialog(self.repo.root,self.selection,self)
            if dialog.exec()==dialog.Accepted:
                dialog.apply_to(self.draft);self.draw();self.result=None;self.score_view.clear()
        except (StorageError,OSError,ValueError) as e:self.status.setText(str(e))
    def country_hints(self):
        if not self.selection:return
        try:
            from contest_country_ui import CountryDialog
            dialog=CountryDialog(self.repo.root,self.selection,self)
            if dialog.exec()==dialog.Accepted:
                dialog.apply_to(self.draft);self.draw();self.result=None;self.score_view.clear()
        except (StorageError,OSError,ValueError) as e:self.status.setText(str(e))
    def event_context(self):return self.event_contexts.get(self.rules.currentData(),{})
    def event_details(self):
        try:
            path=self.rules.currentData()
            if not path:return
            r,_=RuleStore(self.repo.root).read(path)
            if 'event' not in r:self.status.setText('このルールには参加条件が登録されていません。');return
            from contest_event_ui import EventDialog
            d=EventDialog(r['event'],self.event_context(),self)
            if d.exec()==d.Accepted:
                self.event_contexts[path]=d.context;self.schedule();self.update_event_setup_ui();self.navigate()
        except (ValueError,OSError,StorageError) as e:self.status.setText(str(e))
    def qso_details(self):
        if not self.selection:return
        from contest_submit_ui import DetailsDialog
        active_rule=getattr(self,'rule',None) or {}
        if self.rules.currentData():
            try:active_rule,_=RuleStore(self.repo.root).read(self.rules.currentData())
            except (ValueError,OSError,StorageError) as ex:self.status.setText(str(ex));return
        d=DetailsDialog(self.selection,self.draft,self,event=active_rule.get('event',{}))
        if d.exec()==d.Accepted:self.update_details_draft(d.draft);self.schedule()
    def update_details_draft(self,draft):
        from contest_timing import HISTORY_FLAG
        if any(self.draft.get(k,{}).get('tx','')!=draft.get(k,{}).get('tx','') for k in set(self.draft)|set(draft)):
            for context in self.event_contexts.values():context.setdefault('flags',{}).pop(HISTORY_FLAG,None)
        self.draft=draft
    def refresh_rules(self):
        current=self.rules.currentData();early=self.early_rules.currentData() if hasattr(self,'early_rules') else None;self.rules.clear();self.rules.addItem('ルールを選択してください',None);store=RuleStore(self.repo.root);self.rule_catalog=[]
        for path in store.files():
            try:
                r,s=store.read(path)
                if not is_contest_rule(r):continue
                label=store.display_label(r,path);sp=str(path);self.rules.addItem(label,sp)
                hay=' '.join((r.get('name',''),str(r.get('year','')),r.get('id',''),r.get('organizer',''),r.get('sort_name','')));self.rule_catalog.append(dict(label=label,path=sp,search=self._search_value(hay)))
            except (ValueError,StorageError,OSError):continue
        i=self.rules.findData(current)
        if i>=0:self.rules.setCurrentIndex(i)
        if hasattr(self,'early_rules'):self.filter_contests(preferred=early)
    def manage(self):RulesDialog(self.repo.root,self).exec();self.refresh_rules();self.schedule()
    def edit_rule(self):
        path=self.rules.currentData()
        if not path:return
        try:
            store=RuleStore(self.repo.root);r,s=store.read(path);RuleEditor(store,r,path,s,self).exec();self.refresh_rules();self.schedule()
        except (ValueError,OSError,StorageError) as e:self.status.setText(str(e))
    def schedule(self,*args):
        try:
            rule=self.manual_rule() if self.manual_mode() else (RuleStore(self.repo.root).read(self.rules.currentData())[0] if self.rules.currentData() else None)
            self.rule_source.setText('その他のコンテスト：手動設定・自動採点なし' if self.manual_mode() else source_text(rule))
        except (ValueError,OSError,StorageError):self.rule_source.setText('主催情報を読み込めません。')
        self.cancel_score();self.result=None;self.score_view.clear();self.result_label.setText('その他のコンテスト：得点・マルチは自動計算しません。出力上は0扱いになり、提出前に手動確認が必要です。' if self.manual_mode() else '計算待ち…');self.timer.start(50)
    def score_result_text(self,result,pending):
        head=score_breakdown(result)+f'得点 {result.points:g} ／ 第一マルチ {result.multi1} ／ 第二マルチ {result.multi2:g}\n'
        if result.total is not None:
            return head+f'総得点 {result.total:g}'
        confirmations=[p for p in result.problems if str(p).startswith('未確認: ')]
        other=[p for p in result.problems if not str(p).startswith('未確認: ')]
        lines=['まだ「次へ」には進めません。']
        if confirmations:
            lines.append(f'参加部門・運用条件の確認が {len(confirmations)}件残っています。上の「参加部門・運用条件を変更…」を開いて、該当する確認項目を確認してください。')
            lines.extend('・'+str(p).removeprefix('未確認: ') for p in confirmations[:3])
        if pending:
            lines.append(f'交信ナンバーの未確認が {pending}件あります。「戻る」で交信ナンバー確認へ戻ってください。')
        if other:
            lines.append(f'その他の判定エラーが {len(other)}件あります。表の「根拠・確認状態」を確認してください。')
            lines.extend('・'+str(p) for p in other[:3])
        if not confirmations and not pending and not other:
            lines.append('採点結果を確定できません。対象ログ・参加部門・交信ナンバーを確認してください。')
        warning='\n'.join(lines)
        # 続行を止める判定・確認必須メッセージは、通常説明と区別できるよう赤字で表示する。
        return (html.escape(head).replace('\n','<br>')+
                '<span style="color:#b32020;font-weight:600;">'+
                html.escape(warning).replace('\n','<br>')+'</span>')

    def calculate(self):
        self.cancel_score();self.result=None;self.score_view.clear()
        if not self.selection:self.result_label.setText('対象交信を選択してください。');return
        if not self.manual_mode() and not self.rules.currentData():self.result_label.setText('対象交信とルールを選択してください。');return
        try:
            for session in self.selection.sessions:session.snapshot.check(session.path)
            if self.manual_mode():r=self.manual_rule();s=None;path=None
            else:path=self.rules.currentData();r,s=RuleStore(self.repo.root).read(path)
            work_entries=entries(self.selection,self.draft)
            if self.manual_mode():result=manual_score(work_entries)
            elif len(self.selection.rows)>1000:
                self.score_job=score_steps(r,work_entries,self.event_context());self.score_context=(r,s,path)
                self.result_label.setText(f'採点中 0 / {len(self.selection.rows):,}件');self.chunk_timer.start();return
            else:result=score(r,work_entries,self.event_context())
            pending=sum(self.draft.get(key(row),{}).get('status')=='候補・要確認' for row in self.selection.rows)
            if pending:result.total=None
            self.result=result;self.rule=r;self.rule_snapshot=s;self.rule_path=path
            if self.manual_mode():self.result_label.setText(f'その他のコンテスト：自動採点なし ／ 対象 {len(self.selection.rows):,}交信\n得点・マルチは出力上0扱いです。部門・交換ナンバー・得点等は提出前に手動確認してください。'+(f'\n未確認の抽出候補 {pending}件' if pending else ''))
            else:self.result_label.setText(self.score_result_text(result,pending))
            self.score_view.set_result(self.selection,result,self.draft)
        except (ValueError,StorageError,OSError) as e:self.result=None;self.result_label.setText('集計できません: '+str(e))
    def cancel_score(self):
        self.chunk_timer.stop();self.score_job=None
    def score_chunk(self):
        if self.score_job is None:self.chunk_timer.stop();return
        try:
            progress=next(self.score_job)
            self.result_label.setText(('提出用データを確認中' if self.manual_mode() else '採点中')+f' {progress:,} / {len(self.selection.rows):,}件')
        except StopIteration as done:
            self.cancel_score()
            try:
                r,s,path=self.score_context
                if s is not None and path is not None:s.check(Path(path))
                for session in self.selection.sessions:session.snapshot.check(session.path)
                result=done.value;pending=sum(self.draft.get(key(row),{}).get('status')=='候補・要確認' for row in self.selection.rows)
                if pending:result.total=None
                self.result=result;self.rule=r;self.rule_snapshot=s;self.rule_path=path
                if self.manual_mode():self.result_label.setText(f'その他のコンテスト：自動採点なし ／ 対象 {len(self.selection.rows):,}交信\n得点・マルチは出力上0扱いです。部門・交換ナンバー・得点等は提出前に手動確認してください。'+(f'\n未確認の抽出候補 {pending}件' if pending else ''))
                else:self.result_label.setText(self.score_result_text(result,pending))
                self.score_view.set_result(self.selection,result,self.draft)
            except (ValueError,StorageError,OSError) as e:self.result=None;self.result_label.setText('集計できません: '+str(e))
        except (ValueError,StorageError,OSError) as e:
            self.cancel_score();self.result=None;self.result_label.setText('集計できません: '+str(e))
    def reject(self):
        if self.draft and QMessageBox.question(self,'作業を終了','交信ナンバーの作業内容は今回の画面内だけで保持しています。閉じますか？')!=QMessageBox.Yes:return
        self.cancel_score();self.timer.stop();super().reject()


def score_breakdown(result):
    if hasattr(result,'ajd_completion'):return 'AJD完成時刻: '+(result.ajd_completion or '未完成')+' / 採用 '+str(len(result.ajd_indexes))+'局（数値得点0）\n'
    if hasattr(result,'party_stations'):return 'QSOパーティ: '+str(result.party_stations)+' / 20局（得点競争なし）\n'
    counts=getattr(result,'multiplier_counts',None)
    if counts is None:return ''
    timing='\n'.join(getattr(result,'timing_summary',[]))
    return 'マルチ内訳: '+' / '.join(f'{key}={value}' for key,value in counts.items())+'\n'+f"最終加算点: {getattr(result,'final_bonus',0):g}\n"+(timing+'\n' if timing else '')
