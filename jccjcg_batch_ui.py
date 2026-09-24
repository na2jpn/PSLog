"""Three-stage JCC/JCG log batch maintenance dialog."""
from __future__ import annotations

from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QFormLayout,QLabel,QComboBox,QListWidget,QListWidgetItem,
    QLineEdit,QRadioButton,QButtonGroup,QStackedWidget,QTableWidget,QTableWidgetItem,QAbstractItemView,QHeaderView,
    QCheckBox,QMessageBox,QTextEdit)

from window_geometry import SafeDialog
from window_tint import apply_window_tint
from search import station_call_candidates,file_identity,base_station_call
from search_ui import button
from storage import StorageError,VERSION
from time_range import help_text
from jccjcg_batch import (MODE_CODE_TO_QTH,MODE_RMKS_TO_BOTH,MODE_RMKS_TO_PREF,MODE_QTH_TO_CODE,MODE_MISMATCH,MODE_LABELS,collect,commit)


class JccJcgBatchDialog(SafeDialog):
    def __init__(self,repo,own='',parent=None):
        super().__init__(parent);self.repo=repo;self.page=0;self.candidates=[];self.selections=[];self.saved=False
        self.setWindowTitle(f'PSLog Ver{VERSION} — ログ一括処理 JCC/JCG');self.resize(1220,760);apply_window_tint(self,'edit')
        outer=QVBoxLayout(self);self.heading=QLabel();self.heading.setStyleSheet('font-weight:600;');outer.addWidget(self.heading)
        self.stack=QStackedWidget();outer.addWidget(self.stack,1)
        self._source_page(own);self._list_page();self._confirm_page()
        self.status=QLabel();self.status.setWordWrap(True);self.status.setStyleSheet('color:#ad2424');outer.addWidget(self.status)
        nav=QHBoxLayout();self.back_button=button('戻る',self.back);self.next_button=button('次へ',self.next);self.run_button=button('実行',self.run)
        nav.addWidget(self.back_button);nav.addStretch();nav.addWidget(self.next_button);nav.addWidget(self.run_button);nav.addWidget(button('閉じる',self.reject));outer.addLayout(nav)
        self.show_page(0)

    def _source_page(self,own):
        w=QWidget();v=QVBoxLayout(w);self.stack.addWidget(w)
        note=QLabel('対象ログ・期間と、1回に実行する処理方法を選択してください。原本は最終確認後にだけ変更します。');note.setWordWrap(True);v.addWidget(note)
        row=QHBoxLayout();row.addWidget(QLabel('自局コール'));self.own=QComboBox();self.own.addItems(station_call_candidates(self.repo,own));row.addWidget(self.own,1);v.addLayout(row)
        self.logs=QListWidget();self.logs.setMinimumHeight(160);v.addWidget(self.logs,1)
        buttons=QHBoxLayout();buttons.addWidget(button('全て選択',lambda:self._check_logs(True)));buttons.addWidget(button('全て解除',lambda:self._check_logs(False)));buttons.addStretch();v.addLayout(buttons)
        form=QFormLayout();self.start=QLineEdit();self.end=QLineEdit();self.start.setPlaceholderText(help_text(14));self.end.setPlaceholderText(help_text(14));form.addRow('開始（JST）',self.start);form.addRow('終了（JST・含む）',self.end)
        hint=QLabel('空欄は制限なし。開始は指定期間の先頭、終了は指定期間の末尾として扱います。例：20260909だけでも指定できます。');hint.setWordWrap(True);form.addRow(hint)
        recent=QLabel('※ 開始・終了とも空欄の場合は、最新2,000QSOを対象とします。日時を指定した場合は指定範囲から抽出します。');recent.setWordWrap(True);recent.setStyleSheet('color:#555;');form.addRow(recent);v.addLayout(form)
        self.force=QCheckBox('HIS QTHがJapanまたは空欄でなくても強制（[A][B]のみ）');v.addWidget(self.force)
        v.addWidget(QLabel('処理方法（1つ選択）'))
        self.mode_group=QButtonGroup(self);self.mode_buttons={}
        for index,mode in enumerate((MODE_CODE_TO_QTH,MODE_RMKS_TO_BOTH,MODE_RMKS_TO_PREF,MODE_QTH_TO_CODE,MODE_MISMATCH)):
            rb=QRadioButton(MODE_LABELS[mode]);self.mode_group.addButton(rb,index);self.mode_buttons[mode]=rb;v.addWidget(rb)
        self.mode_buttons[MODE_CODE_TO_QTH].setChecked(True)
        for rb in self.mode_buttons.values():rb.toggled.connect(self._update_force_state)
        self._update_force_state();v.addStretch()
        self.own.currentTextChanged.connect(self.find_logs);self.find_logs()

    def _list_page(self):
        w=QWidget();v=QVBoxLayout(w);self.stack.addWidget(w)
        self.list_note=QLabel();self.list_note.setWordWrap(True);v.addWidget(self.list_note)
        self.table=QTableWidget();self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers);self.table.setAlternatingRowColors(True);self.table.verticalHeader().setVisible(False);v.addWidget(self.table,1)
        row=QHBoxLayout();row.addWidget(button('全て選択',lambda:self._set_all_targets(True)));row.addWidget(button('全て解除',lambda:self._set_all_targets(False)));row.addStretch();v.addLayout(row)
        self.target_checks=[];self.choice_groups=[];self.choice_buttons=[]

    def _confirm_page(self):
        w=QWidget();v=QVBoxLayout(w);self.stack.addWidget(w)
        note=QLabel('原本ログを書き換える処理です。以下の予定を確認してください。実行直前に対象ログをバックアップします。');note.setWordWrap(True);v.addWidget(note)
        self.summary=QTextEdit();self.summary.setReadOnly(True);v.addWidget(self.summary,1)
        self.confirmed=QCheckBox('実行内容を確認しました');self.confirmed.toggled.connect(lambda on:self.run_button.setEnabled(bool(on) and self.page==2))
        confirm_row=QHBoxLayout();confirm_row.addStretch(1);confirm_row.addWidget(self.confirmed);v.addLayout(confirm_row)

    def _update_force_state(self,*_):
        enabled=self.mode() in (MODE_CODE_TO_QTH,MODE_RMKS_TO_BOTH)
        self.force.setEnabled(enabled)
        if not enabled:self.force.setChecked(False)

    def mode(self):
        for mode,rb in self.mode_buttons.items():
            if rb.isChecked():return mode
        return MODE_CODE_TO_QTH

    def find_logs(self,*_):
        self.logs.clear();wanted=base_station_call(self.own.currentText())
        for p in sorted(self.repo.book.glob('*.txt')):
            ident=file_identity(p)
            if ident and base_station_call(ident[1])==wanted:
                item=QListWidgetItem(p.name);item.setData(Qt.ItemDataRole.UserRole,str(p));item.setToolTip(str(p));item.setFlags(item.flags()|Qt.ItemFlag.ItemIsUserCheckable);item.setCheckState(Qt.CheckState.Unchecked);self.logs.addItem(item)

    def _check_logs(self,on):
        for i in range(self.logs.count()):self.logs.item(i).setCheckState(Qt.CheckState.Checked if on else Qt.CheckState.Unchecked)

    def _paths(self):return [self.logs.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.logs.count()) if self.logs.item(i).checkState()==Qt.CheckState.Checked]

    @staticmethod
    def _cell_check(checked=True,enabled=True):
        box=QCheckBox();box.setChecked(checked);box.setEnabled(enabled);host=QWidget();layout=QHBoxLayout(host);layout.setContentsMargins(0,0,0,0);layout.setAlignment(Qt.AlignmentFlag.AlignCenter);layout.addWidget(box);return host,box

    def _build_candidates(self):
        paths=self._paths()
        if not paths:raise ValueError('対象ログを1つ以上選択してください。')
        self.candidates=collect(self.repo,paths,self.own.currentText(),self.mode(),self.start.text(),self.end.text(),self.force.isChecked())
        if not self.candidates:raise ValueError('指定条件で修正候補となるQSOはありません。')
        mismatch=self.mode()==MODE_MISMATCH
        headers=(['対象','HIS QTH採用','JCC/JCG採用'] if mismatch else ['対象'])+['DATE','TIME','HIS CALLSIGN','HIS QTH','JCC/JCG','RMKS','元ログ']
        self.table.clear();self.table.setRowCount(len(self.candidates));self.table.setColumnCount(len(headers));self.table.setHorizontalHeaderLabels(headers)
        self.target_checks=[];self.choice_groups=[];self.choice_buttons=[]
        offset=3 if mismatch else 1
        for row,c in enumerate(self.candidates):
            host,target=self._cell_check(True);self.table.setCellWidget(row,0,host);self.target_checks.append(target)
            if mismatch:
                group=QButtonGroup(self);group.setExclusive(True)
                choices={}
                for col,(name,allowed) in enumerate((('his_qth',c.can_adopt_his_qth),('jccjcg',c.can_adopt_jccjcg)),1):
                    rb=QRadioButton();rb.setEnabled(allowed);group.addButton(rb);host=QWidget();lay=QHBoxLayout(host);lay.setContentsMargins(0,0,0,0);lay.setAlignment(Qt.AlignmentFlag.AlignCenter);lay.addWidget(rb);self.table.setCellWidget(row,col,host);choices[name]=rb
                self.choice_groups.append(group);self.choice_buttons.append(choices)
            q=c.qso
            for col,value in enumerate((q.date,q.time,q.call,q.his_qth,q.code,q.remarks,c.path.name),offset):self.table.setItem(row,col,QTableWidgetItem(str(value)))
        self.table.resizeColumnsToContents();self.table.horizontalHeader().setStretchLastSection(True)
        self.list_note.setText(f'{len(self.candidates):,}件の候補です。実行するQSOだけ「対象」をONにしてください。'+(' 不一致修正では各対象行で、どちらの情報を正しいものとして採用するか1つ選択してください。' if mismatch else ''))

    def _set_all_targets(self,on):
        for box in self.target_checks:box.setChecked(on)

    def _selected(self):
        selected=[];mismatch=self.mode()==MODE_MISMATCH
        for row,c in enumerate(self.candidates):
            if not self.target_checks[row].isChecked():continue
            choice=''
            if mismatch:
                choices=self.choice_buttons[row]
                if choices['his_qth'].isChecked():choice='his_qth'
                elif choices['jccjcg'].isChecked():choice='jccjcg'
                else:raise ValueError(f'{row+1}行目の対象QSOで「HIS QTH採用」または「JCC/JCG採用」を選択してください。')
            if c.proposal(choice) is None:raise ValueError(f'{row+1}行目の修正内容を確定できません。')
            selected.append((c,choice))
        if not selected:raise ValueError('実行するQSOを1件以上選択してください。')
        return selected

    def _build_summary(self):
        self.selections=self._selected();files=sorted({c.path.name for c,_ in self.selections});mode=self.mode()
        qth_count=code_count=0
        for c,choice in self.selections:
            after=c.proposal(choice);qth_count+=after.his_qth!=c.qso.his_qth;code_count+=after.code!=c.qso.code
        start=self.start.text().strip() or '制限なし';end=self.end.text().strip() or '制限なし'
        lines=[f'処理: {MODE_LABELS[mode]}']
        if mode in (MODE_CODE_TO_QTH,MODE_RMKS_TO_BOTH):lines.append('強制上書き: '+('ON' if self.force.isChecked() else 'OFF'))
        lines+=[f'対象QSO: {len(self.selections):,}件',f'対象ログ: {len(files):,}ファイル',f'期間: {start} ～ {end}',f'HIS QTH変更: {qth_count:,}件',f'JCC/JCG変更: {code_count:,}件','','対象ログ:']+['  '+name for name in files]+['','変更予定:']
        preview=[]
        for c,choice in self.selections[:200]:
            after=c.proposal(choice);parts=[]
            if after.his_qth!=c.qso.his_qth:parts.append(f'HIS QTH: {c.qso.his_qth or "(空欄)"} → {after.his_qth or "(空欄)"}')
            if after.code!=c.qso.code:parts.append(f'JCC/JCG: {c.qso.code or "(空欄)"} → {after.code or "(空欄)"}')
            preview.append(f'  {c.qso.date} {c.qso.time} {c.qso.call}  '+(' / '.join(parts)))
        lines+=preview
        if len(self.selections)>200:lines.append(f'  …ほか {len(self.selections)-200:,}件')
        lines+=['','変更しない項目: DATE / TIME / BAND / MODE / HIS CALLSIGN / RST / MY QTH / RMKS','実行直前に対象ログのバックアップを作成します。']
        self.summary.setPlainText('\n'.join(lines));self.confirmed.setChecked(False)

    def show_page(self,index):
        self.page=max(0,min(2,index));self.stack.setCurrentIndex(self.page);self.heading.setText(['1 / 3　対象ログ・期間・処理方法','2 / 3　対象QSO確認','3 / 3　実行確認'][self.page]);self.back_button.setVisible(self.page>0);self.next_button.setVisible(self.page<2);self.run_button.setVisible(self.page==2);self.run_button.setEnabled(self.page==2 and self.confirmed.isChecked())

    def next(self):
        self.status.clear()
        try:
            if self.page==0:self._build_candidates();self.show_page(1)
            elif self.page==1:self._build_summary();self.show_page(2)
        except (ValueError,StorageError,OSError) as e:self.status.setText(str(e))

    def back(self):
        if self.page>0:self.show_page(self.page-1)

    def run(self):
        if not self.confirmed.isChecked():return
        self.status.clear()
        try:count,files=commit(self.repo,self.selections)
        except (ValueError,StorageError,OSError) as e:self.status.setText(str(e));return
        self.saved=True;QMessageBox.information(self,'ログ一括処理 JCC/JCG',f'{count:,}交信を更新しました。\n対象ログ: {files:,}ファイル\n更新前のログはバックアップに保存されています。');self.accept()
