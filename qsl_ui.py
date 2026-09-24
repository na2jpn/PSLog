"""QSL receipt dialog: review first, choose ambiguous matches on a guarded detail screen."""
from PySide6.QtCore import Qt,Signal
from PySide6.QtGui import QColor,QBrush
from PySide6.QtWidgets import (QVBoxLayout,QHBoxLayout,QFormLayout,QLineEdit,QLabel,
    QComboBox,QFileDialog,QSplitter,QWidget,QTableWidget,QTableWidgetItem,QGroupBox,
    QAbstractItemView,QTextEdit,QMessageBox,QCheckBox)
from window_geometry import SafeDialog
from search_ui import button
from storage import StorageError,VERSION
from window_tint import apply_window_tint
from datetime import datetime
from pathlib import Path
from html import escape
import json
from qsl_batch import (METHODS,prepare,decisions,commit,BatchFailure,report_paths,
                       call_difference,set_selected,selected_hits)
from qsl_marks import change,buro_judgement,receipt_state

RED=QBrush(QColor(190,0,0))
MUTED=QBrush(QColor(100,100,100))
DETAIL_RED='#b00000'
DETAIL_YELLOW='#fff6cc'
DETAIL_PINK='#ffe2ea'


def _delta_minutes(entry,hit):
    if not entry.stamp or not hit:return None
    stamp=datetime.strptime(hit.qso.date+' '+hit.qso.time,'%Y-%m-%d %H:%M')
    return int((stamp-entry.stamp).total_seconds()/60)


def _hit_text(entry,hit):
    q=hit.qso;delta=_delta_minutes(entry,hit)
    delta_text='' if delta is None else f' ／ 時刻差 {delta:+d}分'
    diff=call_difference(entry.call,q.call)
    diff_text='' if diff=='同一コール' else f'\nコール差: {diff}'
    return (f'{q.date} {q.time} JST{delta_text}\n'
            f'自局: {hit.own} ／ 相手: {q.call} ／ {q.band} / {q.mode}{diff_text}\n'
            f'HIS QTH: {q.his_qth or "(空欄)"} ／ JCC/JCG: {q.code or "(空欄)"}\n'
            f'MY QTH: {q.my_qth or "(空欄)"}\nRMKS: {q.remarks or "(空欄)"}\n'
            f'{hit.path}:{hit.line}')


def _html_text(value):
    return escape(str(value or '')).replace('\n','<br>')


def _detail_head_html(entry,state,reason):
    alert=state in ('未一致','複数候補','手動候補','書式不正','一致・未選択')
    style=(f'color:{DETAIL_RED};font-weight:600;' if alert else 'font-weight:600;')
    code=(f'<br>入力JCC/JCG: {_html_text(entry.code)}' if getattr(entry,'code','') else '')
    return (f'<div style="{style}">'
            f'入力: {_html_text(entry.raw)}{code}<br>'
            f'照合状態: {_html_text(state)}<br>'
            f'理由: {_html_text(reason)}</div>')


def _hit_block_html(entry,hit,title,extra=''):
    same=call_difference(entry.call,hit.qso.call)=='同一コール'
    bg=DETAIL_YELLOW if same else DETAIL_PINK
    body=_hit_text(entry,hit)
    if extra:body+='\n'+extra
    return (f'<div style="background-color:{bg};border:1px solid #d9d9d9;'
            f'padding:6px;margin:5px 0;">'
            f'<b>{_html_text(title)}</b><br>{_html_text(body)}</div>')


def _detail_html(entry,state,reason,hit=None,after='',nearby=(),around=(),skip_reason=''):
    parts=[_detail_head_html(entry,state,reason)]
    if hit:
        extra=f'更新予定RMKS: {after or "(空欄)"}'
        if skip_reason:extra+='\nスキップ理由: '+skip_reason
        parts.append(_hit_block_html(entry,hit,'照合したログ',extra))
    else:
        for candidate in nearby:
            parts.append(_hit_block_html(entry,candidate,'候補・同一コールの近いログ'))
    for candidate in around:
        if call_difference(entry.call,candidate.qso.call)=='同一コール':continue
        title='入力時刻±3分のQSO（コール違い確認用）'
        parts.append(_hit_block_html(entry,candidate,title))
    return ''.join(parts)


class QSLResultDialog(SafeDialog):
    """Final human-facing result screen with report and remaining-input panes."""
    def __init__(self,plan,result_path,unprocessed_path,csv_path,journal,failure='',parent=None):
        super().__init__(parent);self.plan=plan
        self.setWindowTitle(f'PSLog Ver{VERSION} — QSL受領一括処理 / 最終結果');self.resize(1120,760);apply_window_tint(self,'edit')
        layout=QVBoxLayout(self)
        title=QLabel('QSL一括受領 — 最終結果');title.setStyleSheet('font-size:15px;font-weight:700;');layout.addWidget(title)
        try:state=json.loads(Path(journal).read_text(encoding='utf-8'))
        except Exception:state={}
        counts=state.get('report_counts',{})
        summary=QLabel(f"入力 {counts.get('input','?')}件 ／ 更新 {counts.get('updated','?')}件 ／ 既受領等スキップ {counts.get('skipped','?')}件 ／ 未処理 {counts.get('unprocessed','?')}件")
        summary.setWordWrap(True);layout.addWidget(summary)
        if failure:
            warning=QLabel('処理中に問題が発生しました。下記レポートと回復記録を確認してください。\n'+failure);warning.setWordWrap(True);warning.setStyleSheet('color:#b00000;font-weight:600;');layout.addWidget(warning)
        split=QSplitter(Qt.Orientation.Vertical);layout.addWidget(split,1)
        top=QWidget();tb=QVBoxLayout(top);tb.addWidget(QLabel('結果レポート'))
        self.result=QTextEdit();self.result.setReadOnly(True);tb.addWidget(self.result,1);split.addWidget(top)
        bottom=QWidget();bb=QVBoxLayout(bottom);bb.addWidget(QLabel('未処理（のこり）'))
        self.unprocessed=QTextEdit();self.unprocessed.setReadOnly(True);bb.addWidget(self.unprocessed,1);split.addWidget(bottom);split.setSizes([430,230])
        if result_path and Path(result_path).exists():
            self.result.setPlainText(Path(result_path).read_text(encoding='utf-8-sig',errors='replace'))
        else:self.result.setPlainText('結果レポートTXTを作成できませんでした。結果CSV・回復記録を確認してください。')
        if unprocessed_path and Path(unprocessed_path).exists():
            enc='cp932' if plan.encoding=='cp932' else 'utf-8-sig'
            self.unprocessed.setPlainText(Path(unprocessed_path).read_text(encoding=enc,errors='replace'))
        else:self.unprocessed.setPlainText('未処理はありません。未処理TXTは作成していません。')
        paths=QLabel('結果レポート\n'+(str(result_path) if result_path else '（作成なし）')+'\n\n未処理（のこり）\n'+(str(unprocessed_path) if unprocessed_path else '0件（作成なし）')+'\n\n結果CSV\n'+str(csv_path)+'\n回復記録\n'+str(journal))
        paths.setWordWrap(True);paths.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse);layout.addWidget(paths)
        r=QHBoxLayout();r.addStretch();r.addWidget(button('閉じる',self.accept));layout.addLayout(r)

class QSLDetailDialog(SafeDialog):
    """Second-stage candidate selector.  Nothing is written until execute()."""
    def __init__(self,repo,plan,folder,parent=None):
        super().__init__(parent);self.repo=repo;self.plan=plan;self.folder=folder;self.busy=False;self.completed=False;self.message=''
        self.original_selections=[(e.pick,list(getattr(e,'selected',[]))) for e in plan.entries]
        self.row_meta=[]
        self.setWindowTitle(f'PSLog Ver{VERSION} — QSL受領一括処理 / 処理の詳細');self.resize(1260,760);apply_window_tint(self,'edit')
        layout=QVBoxLayout(self)
        title=QLabel('処理の詳細　—　一意一致は選択済みです。未一致・複数候補は赤字で表示します。');title.setStyleSheet('font-weight:600;');layout.addWidget(title)
        note=QLabel('一意一致は選択済みです。複数候補・手動候補はチェックボックスで必要なQSOを複数選べます。既に同じ受領方法が記録済みのQSOはスキップします。');note.setWordWrap(True);layout.addWidget(note)
        self.summary=QLabel();layout.addWidget(self.summary)
        self.table=QTableWidget(0,9);self.table.setHorizontalHeaderLabels(['選択','入力行','相手コール','ログ日時','BAND / MODE','照合状態','時刻差','BURO判定','更新内容'])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows);self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection);self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self.show_detail);layout.addWidget(self.table,1)
        self.selector_buttons=[]
        r=QHBoxLayout();r.addWidget(button('一意一致を全て選択',self.select_unique));r.addWidget(button('全て解除',self.clear_all));r.addStretch();layout.addLayout(r)
        self.detail=QTextEdit();self.detail.setReadOnly(True);self.detail.setMaximumHeight(190);layout.addWidget(self.detail)
        self.status=QLabel();self.status.setWordWrap(True);layout.addWidget(self.status)
        r=QHBoxLayout();self.back=button('戻る',self.accept);r.addWidget(self.back);r.addStretch();self.execute_button=button(f'チェック済を受領［{self.plan.method}］にする',self.execute);r.addWidget(self.execute_button);r.addWidget(button('閉じる',self.cancel));layout.addLayout(r)
        self.render()

    def cancel(self):
        for e,(pick,selected) in zip(self.plan.entries,self.original_selections):
            e.pick=pick;e.selected=list(selected)
        self.reject()

    def _candidate_state(self,entry,hit,manual=False):
        current=receipt_state(hit.qso.remarks,self.plan.method);after,_,_=change(hit.qso.remarks,self.plan.method)
        received=current['received'] and not current['sent'] and after==hit.qso.remarks
        if received:return '既受領スキップ',f'既に {self.plan.method} 受領済み',after,False
        if manual:return '手動候補',f'{entry.reason} / 手動割当候補: {call_difference(entry.call,hit.qso.call)}',after,True
        if len(entry.candidates)>1:return '複数候補',entry.reason,after,True
        return '更新予定',entry.reason,after,True

    def render(self):
        self.busy=True
        try:
            self.table.setRowCount(0);self.row_meta=[];self.selector_buttons=[]
            for entry in self.plan.entries:
                shown=[(ci,hit,False) for ci,hit in enumerate(entry.candidates)]
                if not shown:
                    shown=[(mi,hit,True) for mi,hit in enumerate(getattr(entry,'manual_candidates',[]))]
                if shown:
                    for ci,hit,manual in shown:
                        state,reason,after,enabled=self._candidate_state(entry,hit,manual)
                        row=self.table.rowCount();self.table.insertRow(row)
                        values=[str(entry.number),entry.call,f'{hit.qso.date} {hit.qso.time}',f'{hit.qso.band} / {hit.qso.mode}',state,f'{_delta_minutes(entry,hit):+d}分',buro_judgement(hit.qso.remarks),f'{hit.qso.remarks or "(空欄)"} → {after or "(空欄)"}']
                        for col,value in enumerate(values,1):self.table.setItem(row,col,QTableWidgetItem(value))
                        selector=self._make_selector(entry,hit,row,enabled)
                        self.table.setCellWidget(row,0,selector)
                        if state in ('複数候補','手動候補'):
                            for col in range(1,self.table.columnCount()):self.table.item(row,col).setForeground(RED)
                        elif state=='既受領スキップ':
                            for col in range(1,self.table.columnCount()):self.table.item(row,col).setForeground(MUTED)
                        self.row_meta.append({'entry':entry,'candidate':ci,'hit':hit,'state':state,'reason':reason,'after':after,'enabled':enabled,'manual':manual})
                else:
                    row=self.table.rowCount();self.table.insertRow(row)
                    state='書式不正' if entry.stamp is None else '未一致'
                    selector=QCheckBox();selector.setEnabled(False);self.table.setCellWidget(row,0,self._selector_cell(selector));self.selector_buttons.append(selector)
                    vals=[str(entry.number),entry.call,'','',''+state,'','',entry.reason]
                    for col,value in enumerate(vals,1):self.table.setItem(row,col,QTableWidgetItem(value))
                    for col in range(1,self.table.columnCount()):self.table.item(row,col).setForeground(RED)
                    self.row_meta.append({'entry':entry,'candidate':None,'hit':None,'state':state,'reason':entry.reason,'after':'','enabled':False})
            self.table.resizeColumnsToContents();self.table.setColumnWidth(0,58);self.refresh_summary()
        finally:self.busy=False

    def refresh_summary(self):
        rows=decisions(self.plan);selected=sum(r['state']=='更新予定' for r in rows)
        multiple=sum(len(e.candidates)>1 and not selected_hits(e) for e in self.plan.entries)
        manual=sum(bool(getattr(e,'manual_candidates',[])) and not e.candidates and not selected_hits(e) for e in self.plan.entries)
        unmatched=sum(not e.candidates and not getattr(e,'manual_candidates',[]) for e in self.plan.entries)
        received=sum(r['state']=='既受領スキップ' for r in rows)
        self.summary.setText(f'更新予定 {selected:,}件 ／ 複数候補未選択 {multiple:,}件 ／ 手動候補未選択 {manual:,}件 ／ 未一致・不正 {unmatched:,}件 ／ 既受領スキップ {received:,}件')
        self.execute_button.setEnabled(bool(rows) and not self.plan.consumed)

    def _selector_cell(self,button_widget):
        cell=QWidget();layout=QHBoxLayout(cell);layout.setContentsMargins(0,0,0,0);layout.addStretch();layout.addWidget(button_widget);layout.addStretch();return cell

    def _make_selector(self,entry,hit,row,enabled):
        button_widget=QCheckBox();button_widget.setToolTip('このQSOを処理対象にします。複数候補でも必要なQSOを複数選択できます。')
        selected={ (str(x.path),x.line) for x in selected_hits(entry) }
        button_widget.setEnabled(enabled);button_widget.setChecked(bool(enabled and (str(hit.path),hit.line) in selected))
        button_widget.toggled.connect(lambda checked,e=entry,h=hit,r=row:self._check_toggled(e,h,r,checked))
        self.selector_buttons.append(button_widget)
        return self._selector_cell(button_widget)

    def _check_toggled(self,entry,hit,row,checked):
        if self.busy:return
        set_selected(entry,hit,checked);self.table.selectRow(row);self.refresh_summary();self.show_detail()

    def select_unique(self):
        self.busy=True
        try:
            for r,m in enumerate(self.row_meta):
                if m['enabled'] and not m.get('manual') and len(m['entry'].candidates)==1:
                    set_selected(m['entry'],m['hit'],True);self.selector_buttons[r].setChecked(True)
        finally:self.busy=False
        self.refresh_summary()

    def clear_all(self):
        self.busy=True
        try:
            for e in self.plan.entries:
                e.pick=None;e.selected=[]
            for r,m in enumerate(self.row_meta):
                if m['enabled']:self.selector_buttons[r].setChecked(False)
        finally:self.busy=False
        self.refresh_summary()

    def show_detail(self):
        row=self.table.currentRow()
        if not 0<=row<len(self.row_meta):self.detail.clear();return
        m=self.row_meta[row];e=m['entry']
        skip=(f'既に {self.plan.method} 受領済み' if m['state']=='既受領スキップ' else '')
        self.detail.setHtml(_detail_html(e,m['state'],m['reason'],m['hit'],m['after'],e.nearby,e.around,skip))

    def execute(self):
        if self.plan.consumed:return
        rows=decisions(self.plan);count=sum(r['state']=='更新予定' for r in rows)
        if QMessageBox.question(self,'QSL受領を反映',f'選択済み {count}件へ {self.plan.method} を反映しますか？\n結果レポート/CSVを保存し、対象ログは更新前にバックアップされます。',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:return
        self.execute_button.setEnabled(False)
        try:
            csv,journal,saved=commit(self.repo,self.plan,self.folder)
            result_report,unprocessed_report=report_paths(journal)
            QSLResultDialog(self.plan,result_report,unprocessed_report,csv,journal,parent=self).exec()
            self.message=f'{len(saved)}ファイルを更新しました。\n結果レポート: {result_report or "作成なし"}';self.completed=True;self.accept()
        except BatchFailure as e:
            result_report=e.result_report;unprocessed_report=e.unprocessed_report
            if result_report is None:result_report,unprocessed_report=report_paths(e.journal)
            QSLResultDialog(self.plan,result_report,unprocessed_report,e.csv,e.journal,failure=str(e),parent=self).exec()
            self.message=str(e)+'\n結果レポート: '+str(result_report or '作成なし')+'\n結果CSV: '+str(e.csv)+'\n回復記録: '+str(e.journal);self.completed=True;self.accept()
        except (StorageError,OSError,ValueError) as e:
            self.status.setText(str(e));self.execute_button.setEnabled(True)


class QSLDialog(SafeDialog):
    logs_changed=Signal()
    def __init__(self,repo,own='',parent=None):
        super().__init__(parent);self.repo=repo;self.plan=None;self.page=0;self.visible_rows=[];self.busy=False
        self.setWindowTitle(f'PSLog Ver{VERSION} — QSL受領一括処理');self.resize(1240,740);apply_window_tint(self,'edit')
        layout=QVBoxLayout(self);split=QSplitter(Qt.Orientation.Horizontal);layout.addWidget(split,1)
        left=QWidget();form=QFormLayout(left);split.addWidget(left)
        instruction=QLabel('処理するTXTを「受領一覧TXT」で選択してください。');instruction.setWordWrap(True);instruction.setStyleSheet('font-weight:600;');form.addRow(instruction)
        self.source=QLineEdit();r=QHBoxLayout();r.addWidget(self.source);r.addWidget(button('選択',self.browse));form.addRow('受領一覧TXT',r)
        self.own=QLineEdit(own.split('/')[0]);form.addRow('対象の基本コール',self.own)
        note=QLabel('基本コールと /1・/P等の移動運用を含めます。\n全年度が対象。時刻差は±5分以内を一致候補とします。');note.setWordWrap(True);form.addRow(note)
        self.zone=QComboBox();self.zone.addItems(['選択してください','JST','UTC']);form.addRow('受領一覧TXTの日時基準',self.zone)
        self.method=QComboBox();self.method.addItems(['選択してください',*METHODS]);form.addRow('今回の受領方法',self.method)
        self.encoding=QComboBox();self.encoding.addItems(['UTF-8（BOMあり／なし）','CP932']);form.addRow('文字コード',self.encoding)
        self.folder=QLineEdit(str(repo.root/'reports'));r=QHBoxLayout();r.addWidget(self.folder);r.addWidget(button('選択',self.browse_folder));form.addRow('結果保存先',r)
        for title,text in [
            ('受領一覧TXTの形式','1行に日付・時刻・相手コールを記載します。JCC/JCGが分かる場合はコードを1項目追加できます。\n3項目/4項目とも順序は自由。日付は - または / 区切り、時刻は 5:10 のように : が必要です。\n例：JA1AAA 2026/9/10 5:10　／　1321 5:10 JA1AAA 2026/9/10\n海外局などJCC/JCGがない場合は従来どおり3項目で構いません。JCC/JCGは照合時の確認情報として表示し、このQSL受領処理ではログのJCC/JCG欄を変更しません。'),
            ('QSL更新時の扱い','初回QSL：更新前に既知の.Rがない交信。\n元タグ（例 BURO）がある場合は受領時に .R 付き（BURO.R）へ昇格し、重複タグは作りません。\nBURO判定：BURO=発送済、BURO.R=発送/受領済。'),
            ('照合できなかった場合','±5分以内に1件なら自動選択、複数なら自動確定しません。未一致・複数候補は詳細画面で確認し、結果レポート/CSVにも理由を残します。')]:
            group=QGroupBox(title);gbox=QVBoxLayout(group);n=QLabel(text);n.setWordWrap(True);gbox.addWidget(n);form.addRow(group)
        self.preview_button=button('読み込み・照合',self.preview);form.addRow(self.preview_button)
        right=QWidget();box=QVBoxLayout(right);split.addWidget(right);split.setSizes([420,800])
        filter_row=QHBoxLayout();filter_row.addWidget(QLabel('表示フィルター'));self.filter=QComboBox();self.filter.addItems(['すべて','初回QSL確認','BURO判定あり','未一致・複数候補・不正','既受領スキップ']);filter_row.addWidget(self.filter,1);box.addLayout(filter_row)
        self.summary=QLabel('未照合');box.addWidget(self.summary)
        self.table=QTableWidget(0,6);self.table.setHorizontalHeaderLabels(['入力行','相手コール','照合状態','理由','初回QSL','BURO判定']);self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows);self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection);self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers);box.addWidget(self.table,1)
        r=QHBoxLayout();self.prev=button('前へ',lambda:self.move(-1));r.addWidget(self.prev);self.pages=QLabel();r.addWidget(self.pages);self.next=button('次へ',lambda:self.move(1));r.addWidget(self.next);r.addStretch();box.addLayout(r)
        self.detail=QTextEdit();self.detail.setReadOnly(True);self.detail.setMaximumHeight(220);box.addWidget(self.detail)
        self.status=QLabel();self.status.setWordWrap(True);layout.addWidget(self.status)
        r=QHBoxLayout();r.addStretch();self.detail_button=button('処理の詳細へ進む',self.open_detail);r.addWidget(self.detail_button);r.addWidget(button('閉じる',self.reject));layout.addLayout(r)
        for e in (self.source,self.own):e.textChanged.connect(self.invalidate)
        for c in (self.zone,self.method,self.encoding):c.currentIndexChanged.connect(self.invalidate)
        self.source.textChanged.connect(self.source.setToolTip);self.folder.textChanged.connect(self.folder.setToolTip);self.folder.setToolTip(self.folder.text())
        self.filter.currentIndexChanged.connect(self.refilter);self.table.itemSelectionChanged.connect(self.select);self.invalidate()

    def browse(self):
        path,_=QFileDialog.getOpenFileName(self,'受領一覧TXT','','受領一覧 (*.txt)')
        if path:self.source.setText(path)
    def browse_folder(self):
        path=QFileDialog.getExistingDirectory(self,'結果CSVの保存先',self.folder.text())
        if path:self.folder.setText(path)
    def _ready(self):return bool(self.source.text().strip()) and self.zone.currentIndex()>0 and self.method.currentIndex()>0
    def invalidate(self):
        self.plan=None;self.page=0;self.render();self.status.clear();self.preview_button.setEnabled(self._ready())
    def preview(self):
        self.invalidate()
        if not self._ready():self.status.setText('受領一覧TXT・日時基準・受領方法を選択してください。');return
        try:self.plan=prepare(self.repo,self.source.text(),self.own.text(),self.zone.currentText(),self.method.currentText(),['utf-8-sig','cp932'][self.encoding.currentIndex()])
        except (StorageError,OSError,ValueError) as e:self.status.setText(str(e));return
        self.render()
    def refilter(self):self.page=0;self.render()
    def move(self,delta):self.page+=delta;self.render()

    def render(self):
        self.busy=True
        try:
            rows=decisions(self.plan) if self.plan else [];f=self.filter.currentIndex()
            chosen=[r for r in rows if f==0 or f==1 and r['first'] or f==2 and bool(r['buro_status']) or f==3 and r['state'] in ('未一致','複数候補','手動候補','書式不正','一致・未選択') or f==4 and r['state']=='既受領スキップ']
            pages=max(1,(len(chosen)+99)//100);self.page=max(0,min(self.page,pages-1));self.visible_rows=chosen[self.page*100:(self.page+1)*100]
            self.table.setRowCount(0)
            for i,r in enumerate(self.visible_rows):
                self.table.insertRow(i)
                values=[str(r['entry'].number),r['entry'].call,r['state'],r.get('reason',''),'要確認' if r['first'] and r['state']=='更新予定' else '',r['buro_status']]
                for j,v in enumerate(values):self.table.setItem(i,j,QTableWidgetItem(v))
                if r['state'] in ('未一致','複数候補','手動候補','書式不正','一致・未選択'):
                    for j in range(self.table.columnCount()):self.table.item(i,j).setForeground(RED)
                elif r['state']=='既受領スキップ':
                    for j in range(self.table.columnCount()):self.table.item(i,j).setForeground(MUTED)
            self.pages.setText(f'{self.page+1} / {pages} ページ（100行ずつ）');self.prev.setEnabled(self.page>0);self.next.setEnabled(self.page+1<pages)
            self.summary.setWordWrap(True)
            buros=sum(r['buro_status']=='発送済' for r in rows);buror=sum(r['buro_status']=='発送/受領済' for r in rows)
            input_count=len({r['entry'].number for r in rows})
            self.summary.setText(f"入力 {input_count:,}行 ／ 更新予定 {sum(r['state']=='更新予定' for r in rows):,}件 ／ 表示対象 {len(chosen):,}行\n初回QSL {sum(r['first'] and r['state']=='更新予定' for r in rows):,}件 ／ BURO発送済 {buros:,}件 ／ BURO発送/受領済 {buror:,}件")
            self.detail.clear();self.detail_button.setEnabled(bool(rows) and bool(self.plan) and not self.plan.consumed)
        finally:self.busy=False

    def selected(self):
        i=self.table.currentRow();return self.visible_rows[i] if 0<=i<len(self.visible_rows) else None

    def select(self):
        if self.busy:return
        row=self.selected()
        if not row:self.detail.clear();return
        e=row['entry'];reason=row.get('reason',e.reason)
        if row['hit']:
            extra=f'更新前: {row["hit"].qso.remarks or "(空欄)"}\n更新予定: {row["after"] or "(空欄)"}'
            skip=(f'既に {self.plan.method} 受領済み' if row['state']=='既受領スキップ' else '')
            html=_detail_head_html(e,row['state'],reason)+_hit_block_html(e,row['hit'],'照合したログ',extra+(('\nスキップ理由: '+skip) if skip else ''))
            for candidate in e.around:
                if call_difference(e.call,candidate.qso.call)!='同一コール':
                    html+=_hit_block_html(e,candidate,'入力時刻±3分のQSO（コール違い確認用）')
            self.detail.setHtml(html)
        else:
            candidates=e.candidates or getattr(e,'manual_candidates',[]) or e.nearby
            self.detail.setHtml(_detail_html(e,row['state'],reason,None,'',candidates,e.around))

    def open_detail(self):
        if not self.plan or self.plan.consumed:return
        dialog=QSLDetailDialog(self.repo,self.plan,self.folder.text(),self);dialog.exec()
        if dialog.completed:
            self.plan=None;self.logs_changed.emit();self.status.setText(dialog.message);self.render()
        else:self.render()
