"""Dedicated search, edit and confirmed single-QSO deletion screens."""
from dataclasses import asdict,replace
from pathlib import Path
from PySide6.QtCore import Qt,QAbstractTableModel,QModelIndex,Signal,QTimer
from PySide6.QtWidgets import (QDialog,QVBoxLayout,QHBoxLayout,QGridLayout,QLabel,
    QLineEdit,QCheckBox,QPushButton,QComboBox,QTableView,QTableWidget,QTableWidgetItem,QHeaderView,QAbstractItemView,
    QTextEdit,QSplitter,QWidget,QScrollArea,QFormLayout,QMessageBox,QFileDialog,QFrame)
from model import QSO
from mode_text import split_mode_value
from qsl_marks import TOKEN as QSL_TOKEN,change as change_qsl_mark
from remarks_sections import primary as primary_remarks,split_for_ui,compose as compose_remarks,validate_component as validate_remarks_component
from storage import StorageError,VERSION
from window_tint import apply_window_tint
from search import Criteria,search,normalize_time,delete_hits,station_call_candidates,Hit

LABELS=[('date','DATE'),('time','TIME（JST）'),('band','BAND'),('mode','MODE'),
    ('call','相手コールサイン'),('sent','RSTs（送信）'),('received','RSTr（受信）'),
    ('his_qth','HIS QTH'),('my_qth','MY QTH'),('remarks','RMKS'),('code','JCC / JCG')]

def button(text,slot):
    b=QPushButton(text);b.setAutoDefault(False);b.clicked.connect(slot);return b

def detail(hit):
    q=asdict(hit.qso)
    return '\n'.join([f'自局: {hit.own}',f'原本: {hit.path}',f'原本行: {hit.line}','']+
                     [label+': '+q[key] for key,label in LABELS])


def _fresh_hit(repo,old_hit,qso):
    target=old_hit.path if qso.date[:4]==old_hit.path.name[:4] else old_hit.path.with_name(qso.date[:4]+old_hit.path.name[4:])
    session=repo.open(target)
    wanted=asdict(qso)
    # Same-file edits keep the line when possible.  Cross-year edits append to
    # the destination, so search from the end for the newly stored exact row.
    if target==old_hit.path and 1<=old_hit.line<=len(session.log.lines):
        parsed=session.log.lines[old_hit.line-1].qso
        if parsed and asdict(parsed)==wanted:
            line=old_hit.line
            return Hit(session,session.snapshot,line,session.log.lines[line-1].raw,parsed,old_hit.own)
    for line in range(len(session.log.lines),0,-1):
        parsed=session.log.lines[line-1].qso
        if parsed and asdict(parsed)==wanted:
            return Hit(session,session.snapshot,line,session.log.lines[line-1].raw,parsed,old_hit.own)
    raise StorageError('編集後の交信を再表示できません。ログ検索を再読み込みしてください。')

def detail_text(hit):
    q=hit.qso;main_mode,sub_mode=split_mode_value(q.mode)
    marks=sorted({m.group() for m in QSL_TOKEN.finditer(primary_remarks(q.remarks))},key=str.casefold)
    rows=[
        f'自局コール: {hit.own}',
        f'元ログファイル: {hit.path.name}',
        f'元ログPATH: {hit.path}',
        f'原本行: {hit.line}',
        '',
        f'DATE: {q.date}',
        f'TIME: {q.time} JST',
        f'BAND: {q.band}',
        f'MODE: {main_mode or q.mode}',
    ]
    if sub_mode:rows.append(f'Sub Mode: {sub_mode}')
    rows.extend([
        f'相手コールサイン: {q.call}',
        f'RSTs（送信）: {q.sent}',
        f'RSTr（受信）: {q.received}',
        f'HIS QTH: {q.his_qth}',
        f'JCC / JCG: {q.code}',
        f'MY QTH: {q.my_qth}',
        f'RMKS: {q.remarks}',
        '',
        'QSL受領判定: '+('あり' if q.confirmed else 'なし'),
        'QSL関連記録: '+(', '.join(marks) if marks else 'なし'),
        '',
        '原本行内容:',
        hit.raw.rstrip('\r\n'),
    ])
    return '\n'.join(rows)

from window_geometry import SafeDialog as QDialog

class ResultModel(QAbstractTableModel):
    columns=['選択','DATE','TIME JST','相手コール','BAND','MODE','RMKS','HisQTH','MyQTH','元ログ']
    def __init__(self,parent=None): super().__init__(parent);self.hits=[];self.checked=set()
    @staticmethod
    def key(hit):return (str(hit.path),hit.line)
    def reset(self,hits):
        self.beginResetModel();self.hits=list(hits);self.checked={self.key(h) for h in self.hits};self.endResetModel()
    def rowCount(self,parent=QModelIndex()):return 0 if parent.isValid() else len(self.hits)
    def columnCount(self,parent=QModelIndex()):return 0 if parent.isValid() else len(self.columns)
    def headerData(self,section,orientation,role=Qt.ItemDataRole.DisplayRole):
        if role==Qt.ItemDataRole.DisplayRole and orientation==Qt.Orientation.Horizontal:return self.columns[section]
    def data(self,index,role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():return None
        h=self.hits[index.row()];q=h.qso
        if role==Qt.ItemDataRole.CheckStateRole and index.column()==0:
            return Qt.CheckState.Checked if self.key(h) in self.checked else Qt.CheckState.Unchecked
        if role==Qt.ItemDataRole.DisplayRole:
            if index.column()==0:return ''
            return [q.date,q.time,q.call,q.band,q.mode,q.remarks,q.his_qth,q.my_qth,h.path.name][index.column()-1]
        if role==Qt.ItemDataRole.ToolTipRole:return detail(h)
    def flags(self,index):
        flags=super().flags(index)
        if index.isValid() and index.column()==0:flags|=Qt.ItemFlag.ItemIsUserCheckable
        return flags
    def setData(self,index,value,role=Qt.ItemDataRole.EditRole):
        if not index.isValid() or index.column()!=0 or role!=Qt.ItemDataRole.CheckStateRole:return False
        key=self.key(self.hits[index.row()])
        if value==Qt.CheckState.Checked.value or value==Qt.CheckState.Checked:self.checked.add(key)
        else:self.checked.discard(key)
        self.dataChanged.emit(index,index,[Qt.ItemDataRole.CheckStateRole]);return True
    def set_all(self,on):
        self.checked={self.key(h) for h in self.hits} if on else set()
        if self.hits:self.dataChanged.emit(self.index(0,0),self.index(len(self.hits)-1,0),[Qt.ItemDataRole.CheckStateRole])
    def checked_hits(self):return [h for h in self.hits if self.key(h) in self.checked]

class EditDialog(QDialog):
    def __init__(self,hit,parent=None):
        super().__init__(parent);self.hit=hit;self.saved=False;self.deleted=False;self.saved_qso=None;self.original=asdict(hit.qso)
        self.setWindowTitle(f'PSLog Ver{VERSION} — 交信を編集');self.resize(820,740);apply_window_tint(self,'edit')
        outer=QVBoxLayout(self)
        label=QLabel(f'自局: {hit.own}   原本行: {hit.line}');outer.addWidget(label)
        path=QLineEdit(str(hit.path));path.setReadOnly(True);path.setToolTip(str(hit.path));outer.addWidget(path)
        notice=QLabel('メイン画面へ入力する場合は、編集を保存またはキャンセルしてこのウィンドウを閉じてください。');notice.setWordWrap(True);outer.addWidget(notice)
        scroll=QScrollArea();scroll.setWidgetResizable(True);body=QWidget();form=QFormLayout(body)
        scroll.setWidget(body);outer.addWidget(scroll,1);self.inputs={}
        rmks1,rmks2,self.rmks_extras=split_for_ui(self.original['remarks'])
        self.qsl_buttons={}
        for key,label in LABELS:
            if key=='received':
                continue
            if key=='sent':
                sent=QLineEdit(self.original['sent']);received=QLineEdit(self.original['received'])
                self.inputs['sent']=sent;self.inputs['received']=received
                host=QWidget();row=QHBoxLayout(host);row.setContentsMargins(0,0,0,0);row.setSpacing(8)
                row.addWidget(sent,1);row.addWidget(QLabel('RSTr（受信）'));row.addWidget(received,1)
                form.addRow(label,host);continue
            if key=='remarks':
                label_widget=QWidget();label_row=QHBoxLayout(label_widget);label_row.setContentsMargins(0,0,0,0);label_row.setSpacing(8);label_row.addWidget(QLabel(label))
                self.rmks2_toggle=QCheckBox('RMKS2を表示');self.rmks2_toggle.setChecked(bool(rmks2 or self.rmks_extras));label_row.addWidget(self.rmks2_toggle);label_row.addStretch()
                e=QLineEdit(rmks1);self.inputs[key]=e;form.addRow(label_widget,e)
                qsl_host=QWidget();qsl_row=QHBoxLayout(qsl_host);qsl_row.setContentsMargins(0,0,0,0);qsl_row.setSpacing(5)
                for method in ('LoTW.R','hQSL.R','eQSL.R','BURO.R','QRZ.R','CARD.R','Other.R'):
                    b=button('['+method+']',lambda checked=False,m=method:self.add_qsl_receipt(m));self.qsl_buttons[method]=b;qsl_row.addWidget(b)
                qsl_row.addStretch();form.addRow('QSL追加',qsl_host)
                self.rmks2=QLineEdit(rmks2);self.rmks2_label=QLabel('RMKS2');form.addRow(self.rmks2_label,self.rmks2)
                self.rmks2.setVisible(self.rmks2_toggle.isChecked());self.rmks2_label.setVisible(self.rmks2_toggle.isChecked());self.rmks2_toggle.toggled.connect(self.rmks2_visibility_changed)
            else:
                e=QLineEdit(self.original[key]);self.inputs[key]=e
                if key=='code':
                    host=QWidget();row=QHBoxLayout(host);row.setContentsMargins(0,0,0,0);row.setSpacing(6);row.addWidget(e,1);row.addWidget(button('HIS QTHへ反映',self.apply_qth_from_code));form.addRow(label,host)
                else:form.addRow(label,e)
        self.changes=QTextEdit();self.changes.setReadOnly(True);self.changes.setMaximumHeight(140);outer.addWidget(self.changes)
        self.error=QLabel();self.error.setWordWrap(True);self.error.setStyleSheet('color:#ad2424');outer.addWidget(self.error)
        actions=QHBoxLayout()
        self.delete_button=button('この交信を削除',self.delete_record);self.delete_button.setEnabled(hit.editable)
        self.delete_button.setStyleSheet('color:#a61f1f; font-weight:600;')
        actions.addWidget(self.delete_button);actions.addStretch()
        self.save_button=button('変更を保存',self.save);self.cancel_button=button('キャンセル',self.reject)
        actions.addWidget(self.save_button);actions.addWidget(self.cancel_button);outer.addLayout(actions)
        for e in self.inputs.values():e.textChanged.connect(self.changed)
        self.rmks2.textChanged.connect(self.changed);self.changed()
    def add_qsl_receipt(self,method):
        try:
            updated,_,_=change_qsl_mark(self.values()['remarks'],method)
            rmks1,_,_=split_for_ui(updated)
        except (ValueError,StorageError) as e:
            self.error.setText(str(e));return
        self.inputs['remarks'].setText(rmks1);self.error.clear()

    def apply_qth_from_code(self):
        try:
            from jccjcg_batch import qth_from_code
            qth=qth_from_code(self.hit.session.repo.root,self.inputs['code'].text())
        except (ValueError,StorageError,OSError) as e:
            self.error.setText(str(e));return
        self.inputs['his_qth'].setText(qth);self.error.clear()

    def rmks2_visibility_changed(self,on):
        if not on and self.rmks2.text():
            answer=QMessageBox.question(self,'RMKS2を非表示','RMKS2の内容を削除して非表示にしますか？',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)
            if answer!=QMessageBox.StandardButton.Yes:
                self.rmks2_toggle.blockSignals(True);self.rmks2_toggle.setChecked(True);self.rmks2_toggle.blockSignals(False);return
            self.rmks2.clear()
        self.rmks2.setVisible(bool(on));self.rmks2_label.setVisible(bool(on));self.changed()
    def values(self):
        values={key:e.text() for key,e in self.inputs.items()}
        values['remarks']=compose_remarks(values['remarks'],self.rmks2.text() if self.rmks2_toggle.isChecked() else '',self.rmks_extras)
        return values
    def changed(self):
        now=self.values()
        changes=[f'{label}: {self.original[key]} → {now[key]}' for key,label in LABELS if now[key]!=self.original[key]]
        self.changes.setPlainText('\n'.join(changes) or '変更はありません。')
        self.save_button.setEnabled(bool(changes) and self.hit.editable)
    def save(self):
        try:
            validate_remarks_component(self.inputs['remarks'].text(),'RMKS');validate_remarks_component(self.rmks2.text(),'RMKS2')
            q=QSO(**self.values());q.validate()
            if q.date[:4]!=self.hit.path.name[:4]:
                target=self.hit.path.with_name(q.date[:4]+self.hit.path.name[4:])
                if QMessageBox.question(self,'保存年の変更','この交信を次のログへ移します。\n'+str(target)+'\n両方のログを保護してから保存します。',QMessageBox.Yes|QMessageBox.No,QMessageBox.No)!=QMessageBox.Yes:return
            # No RST default recalculation on mode change in an edit screen.
            self.hit.apply(q)
        except (ValueError,StorageError,OSError) as e:
            self.error.setText(str(e))
            from input_feedback import focus_error
            focus_error(e,self.inputs);return
        self.saved_qso=q;self.saved=True;self.accept()
    def delete_record(self):
        if not self.hit.editable:return
        q=self.hit.qso
        text=('この交信を削除しますか？\n\n'
              f'{q.date} {q.time} JST　{q.call}　{q.band}MHz {q.mode}')
        answer=QMessageBox.question(self,'交信の削除確認',text,
            QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)
        if answer!=QMessageBox.StandardButton.Yes:return
        try:self.hit.apply()
        except (StorageError,OSError) as e:
            self.error.setText(str(e));return
        self.deleted=True;self.saved=True;self.saved_qso=None;self.accept()
    def reject(self):
        if self.values()!=self.original and not self.saved:
            answer=QMessageBox.question(self,'未保存の変更','変更を破棄して閉じますか？',
                QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)
            if answer!=QMessageBox.StandardButton.Yes:return
        super().reject()
    def closeEvent(self,event):
        self.reject()
        if self.isVisible():event.ignore()
        else:event.accept()


class QSLQuickDialog(QDialog):
    """Compact, read-only QSO view with receipt-mark buttons only."""
    METHODS=('LoTW.R','hQSL.R','eQSL.R','BURO.R','QRZ.R','CARD.R','Other.R')
    def __init__(self,repo,hit,parent=None):
        super().__init__(parent);self.repo=repo;self.hit=hit;self.saved=False
        self.setWindowTitle(f'PSLog Ver{VERSION} — QSL処理');self.resize(760,390);apply_window_tint(self,'edit')
        outer=QVBoxLayout(self)
        guide=QLabel('選択した交信のQSL受領記録だけを処理します。QSO情報はここでは編集できません。')
        guide.setWordWrap(True);outer.addWidget(guide)
        self.info=QGridLayout();outer.addLayout(self.info);self.info_values={}
        labels=(('date','DATE'),('time','TIME（JST）'),('band','BAND'),('mode','MODE'),('call','相手コールサイン'),('his_qth','HIS QTH'),('code','JCC / JCG'))
        for i,(key,label) in enumerate(labels):
            row=i//2;col=(i%2)*2;self.info.addWidget(QLabel(label),row,col)
            value=QLabel();value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse);value.setWordWrap(True);self.info.addWidget(value,row,col+1);self.info_values[key]=value
        self.info.setColumnStretch(1,1);self.info.setColumnStretch(3,1)
        outer.addWidget(QLabel('現在のRMKS'))
        self.remarks=QLineEdit();self.remarks.setReadOnly(True);outer.addWidget(self.remarks)
        qsl=QHBoxLayout();self.qsl_buttons={}
        for method in self.METHODS:
            b=button('['+method+']',lambda checked=False,m=method:self.add_qsl_receipt(m));self.qsl_buttons[method]=b;qsl.addWidget(b)
        qsl.addStretch();outer.addLayout(qsl)
        self.status=QLabel();self.status.setWordWrap(True);outer.addWidget(self.status)
        actions=QHBoxLayout();actions.addStretch();actions.addWidget(button('閉じる',self.accept));outer.addLayout(actions)
        self.refresh()
    def refresh(self):
        q=self.hit.qso
        for key,label in self.info_values.items():label.setText(getattr(q,key))
        self.remarks.setText(q.remarks);self.remarks.setToolTip(q.remarks)
        for b in self.qsl_buttons.values():b.setEnabled(bool(self.hit.editable))
    def add_qsl_receipt(self,method):
        if not self.hit.editable:return
        try:
            updated,_,_=change_qsl_mark(self.hit.qso.remarks,method)
            if updated==self.hit.qso.remarks:
                self.status.setText(method+' はすでに記録されています。');return
            q=replace(self.hit.qso,remarks=updated);q.validate();old=self.hit
            old.apply(q);self.hit=_fresh_hit(self.repo,old,q);self.saved=True;self.refresh()
            self.status.setText(method+' をRMKSへ反映しました。')
        except (ValueError,StorageError,OSError) as e:self.status.setText(str(e))


class DetailDialog(QDialog):
    def __init__(self,repo,hit,parent=None):
        super().__init__(parent);self.repo=repo;self.hit=hit;self.saved=False
        self.setWindowTitle('PSLog — 交信詳細');self.resize(820,650);apply_window_tint(self,'edit')
        layout=QVBoxLayout(self)
        notice=QLabel('メイン画面へ入力する場合は、このウィンドウを閉じてください。');notice.setWordWrap(True);layout.addWidget(notice)
        self.view=QTextEdit();self.view.setReadOnly(True);layout.addWidget(self.view,1)
        self.error=QLabel();self.error.setWordWrap(True);self.error.setStyleSheet('color:#ad2424');layout.addWidget(self.error)
        row=QHBoxLayout();row.addStretch();self.edit_button=button('編集…',self.edit);row.addWidget(self.edit_button);row.addWidget(button('閉じる',self.accept));layout.addLayout(row)
        self.refresh()
    def refresh(self):
        self.view.setPlainText(detail_text(self.hit))
        self.edit_button.setEnabled(bool(self.hit.editable))
    def edit(self):
        if not self.hit.editable:return
        dialog=EditDialog(self.hit,self);dialog.exec()
        if not dialog.saved:return
        self.saved=True
        if dialog.deleted:
            self.accept();return
        try:
            self.hit=_fresh_hit(self.repo,self.hit,dialog.saved_qso);self.error.clear();self.refresh()
        except (StorageError,OSError) as e:
            self.error.setText(str(e));self.edit_button.setEnabled(False)


class DeleteDialog(QDialog):
    def __init__(self,hit,parent=None):
        super().__init__(parent);self.hit=hit;self.saved=False
        self.setWindowTitle(f'PSLog Ver{VERSION} — 交信の削除確認');self.resize(730,580);apply_window_tint(self,'edit')
        layout=QVBoxLayout(self);layout.addWidget(QLabel('この1交信を削除します。削除前のログはバックアップに残します。'))
        view=QTextEdit();view.setReadOnly(True);view.setPlainText(detail(hit));layout.addWidget(view,1)
        self.error=QLabel();self.error.setWordWrap(True);self.error.setStyleSheet('color:#ad2424');layout.addWidget(self.error)
        actions=QHBoxLayout();actions.addStretch()
        self.delete_button=button('この交信を削除',self.delete);self.delete_button.setEnabled(hit.editable)
        self.cancel_button=button('キャンセル',self.reject);self.cancel_button.setDefault(True)
        actions.addWidget(self.delete_button);actions.addWidget(self.cancel_button);layout.addLayout(actions)
        self.cancel_button.setFocus()
    def delete(self):
        try:self.hit.apply()
        except (StorageError,OSError) as e:self.error.setText(str(e));return
        self.saved=True;self.accept()

class CheckedDeleteDialog(QDialog):
    def __init__(self,repo,hits,parent=None):
        super().__init__(parent);self.repo=repo;self.hits=list(hits);self.saved=False
        count=len(self.hits);self.setWindowTitle('PSLog — チェックした交信の削除確認');self.resize(820,560);apply_window_tint(self,'edit')
        layout=QVBoxLayout(self)
        guide=QLabel(f'チェックした{count:,}件の交信を削除します。削除前のログはバックアップに残します。\n対象を確認してから削除してください。')
        guide.setWordWrap(True);layout.addWidget(guide)
        self.table=QTableWidget(count,6);self.table.setHorizontalHeaderLabels(['DATE','TIME JST','相手コール','BAND','MODE','元ログ'])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers);self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False);self.table.setAlternatingRowColors(True)
        for row,h in enumerate(self.hits):
            q=h.qso
            for col,value in enumerate((q.date,q.time,q.call,q.band,q.mode,h.path.name)):
                self.table.setItem(row,col,QTableWidgetItem(str(value)))
        self.table.resizeColumnsToContents();self.table.horizontalHeader().setStretchLastSection(True);layout.addWidget(self.table,1)
        self.error=QLabel();self.error.setWordWrap(True);self.error.setStyleSheet('color:#ad2424');layout.addWidget(self.error)
        actions=QHBoxLayout();actions.addStretch()
        self.delete_button=button(f'{count:,}件を削除',self.delete);self.cancel_button=button('キャンセル',self.reject);self.cancel_button.setDefault(True)
        actions.addWidget(self.delete_button);actions.addWidget(self.cancel_button);layout.addLayout(actions);self.cancel_button.setFocus()
    def delete(self):
        try:delete_hits(self.repo,self.hits)
        except (StorageError,OSError) as e:self.error.setText(str(e));return
        self.saved=True;self.accept()

class SearchDialog(QDialog):
    logs_changed=Signal()
    def __init__(self,repo,own='',parent=None,*,filename='',autorun=False):
        super().__init__(parent);self.repo=repo;self.result_hits=[];self.search_status_base='';self.setWindowTitle(f'PSLog Ver{VERSION} — ログ検索・編集');self.resize(1180,740);apply_window_tint(self,'edit')
        outer=QVBoxLayout(self);form=QGridLayout();outer.addLayout(form)
        self.filters={}

        def line_filter(key,hint):
            e=QLineEdit();e.setPlaceholderText(hint);e.returnPressed.connect(self.run_search);self.filters[key]=e;return e

        own_box=QComboBox();own_box.addItem('選択してください');own_box.addItems(station_call_candidates(repo,own));own_box.setToolTip('PSLogのログファイル名から抽出した自局コールです。/1・/P 等は候補名から除きます。')
        self.filters['own']=own_box
        form.addWidget(QLabel('対象自局'),0,0);form.addWidget(own_box,0,1)

        filename_filter=line_filter('filename','空欄は全ログ・部分一致')
        file_box=QWidget();file_row=QHBoxLayout(file_box);file_row.setContentsMargins(0,0,0,0);file_row.setSpacing(6)
        file_row.addWidget(filename_filter,1);self.file_browse_button=button('参照…',self.browse_log_file);file_row.addWidget(self.file_browse_button)
        form.addWidget(QLabel('対象ログファイル'),0,2);form.addWidget(file_box,0,3,1,4)

        form.addWidget(QLabel('相手コール'),1,0);form.addWidget(line_filter('call','部分一致'),1,1)
        form.addWidget(QLabel('BAND'),1,2);form.addWidget(line_filter('band','空欄はすべて・完全一致'),1,3)
        form.addWidget(QLabel('MODE'),1,5);form.addWidget(line_filter('mode','空欄はすべて・部分一致'),1,6)

        form.addWidget(QLabel('RMKS'),2,0);form.addWidget(line_filter('remarks','部分一致'),2,1,1,6)

        form.addWidget(QLabel('HIS QTH'),3,0);form.addWidget(line_filter('his_qth','部分一致'),3,1)
        form.addWidget(QLabel('JCC/JCG'),3,2);form.addWidget(line_filter('jccjcg','コード・部分一致'),3,3)
        separator=QFrame();separator.setFrameShape(QFrame.Shape.VLine);separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setToolTip('左側は相手局情報、右側は自局情報です。');form.addWidget(separator,3,4)
        form.addWidget(QLabel('MY QTH'),3,5);form.addWidget(line_filter('my_qth','部分一致'),3,6)

        form.addWidget(QLabel('開始日時 JST'),4,0);form.addWidget(line_filter('start','YYYYMMDDhhmm・先頭だけでも可'),4,1)
        form.addWidget(QLabel('終了日時 JST'),4,2);form.addWidget(line_filter('end','YYYYMMDDhhmm・先頭だけでも可'),4,3)

        for col in (1,3,6):form.setColumnStretch(col,1)
        form.setColumnMinimumWidth(4,14)
        actions=QHBoxLayout();self.portable=QCheckBox('指定自局の /1・/P 等の運用も含める');self.portable.setChecked(True);actions.addWidget(self.portable)
        self.select_all_button=button('表示一覧を全選択',lambda:self.model.set_all(True));self.clear_all_button=button('全解除',lambda:self.model.set_all(False))
        actions.addWidget(self.select_all_button);actions.addWidget(self.clear_all_button);actions.addStretch();actions.addWidget(QLabel('最大表示件数'))
        self.max_results=QLineEdit('1000');self.max_results.setMaximumWidth(90);self.max_results.setToolTip('検索結果一覧に表示する最大件数です。1以上の数字を入力してください。')
        self.max_results.returnPressed.connect(self.run_search);actions.addWidget(self.max_results)
        self.search_button=button('検索 / 再読み込み',self.run_search);actions.addWidget(self.search_button);outer.addLayout(actions)
        self.status=QLabel('検索条件を指定して検索してください。開始・終了日時は先頭だけでも指定できます。開始側は指定範囲の先頭、終了側は指定範囲の末尾として検索します（例：終了 20260917 はその日の23:59まで）。');self.status.setWordWrap(True);outer.addWidget(self.status)
        split=QSplitter(Qt.Orientation.Horizontal);outer.addWidget(split,1)
        self.table=QTableView();self.model=ResultModel(self);self.table.setModel(self.model)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True);self.table.setWordWrap(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.verticalHeader().setVisible(False)
        for i,width in enumerate([55,105,80,120,60,70,170,180,180,190]):self.table.setColumnWidth(i,width)
        split.addWidget(self.table)
        right=QWidget();right_layout=QVBoxLayout(right);right_layout.setContentsMargins(0,0,0,0);right_layout.setSpacing(6)
        self.details=QTextEdit();self.details.setReadOnly(True);right_layout.addWidget(self.details,1)
        edit_host=QWidget();edit_row=QHBoxLayout(edit_host);edit_row.setContentsMargins(0,0,0,0);edit_row.setSpacing(6)
        self.qsl_button=button('QSL処理…',self.qsl_selected);self.edit_button=button('交信を編集…',self.edit_selected)
        edit_row.addWidget(self.qsl_button,1);edit_row.addWidget(self.edit_button,1);right_layout.addWidget(edit_host)
        split.addWidget(right);split.setSizes([750,400])
        self.table.selectionModel().selectionChanged.connect(self.selection_changed);self.model.dataChanged.connect(self.selection_changed)
        self.table.doubleClicked.connect(lambda _index:self.show_detail())
        self.problems=QTextEdit();self.problems.setReadOnly(True);self.problems.setMaximumHeight(95);self.problems.hide();outer.addWidget(self.problems)
        bottom=QHBoxLayout();bottom.addWidget(QLabel('チェック済みを →'))
        self.delete_button=button('削除…',self.delete_checked);self.pota_button=button('POTAへ…',self.open_pota);self.sota_button=button('SOTAへ…',self.open_sota)
        self.party_button=button('QSOパーティへ…',self.open_party);self.contest_button=button('コンテスト提出へ…',self.open_contest);self.export_button=button('エクスポートへ…',self.open_export)
        tip='現在一覧に表示されている交信のうち、先頭のチェックがONの交信だけを渡します。最大表示件数を超えた非表示行は対象になりません。'
        for b in (self.pota_button,self.sota_button,self.party_button,self.contest_button,self.export_button):b.setToolTip(tip)
        self.delete_button.setToolTip('現在一覧に表示されている交信のうち、先頭のチェックがONの交信だけを削除確認画面へ送ります。')
        for b in (self.delete_button,self.pota_button,self.sota_button,self.party_button,self.contest_button,self.export_button):bottom.addWidget(b)
        bottom.addStretch();separator=QFrame();separator.setFrameShape(QFrame.Shape.VLine);separator.setFrameShadow(QFrame.Shadow.Sunken);bottom.addWidget(separator);bottom.addWidget(button('閉じる',self.reject));outer.addLayout(bottom)
        self.selection_changed()
        for e in self.filters.values():
            (e.currentTextChanged if isinstance(e,QComboBox) else e.textChanged).connect(self.invalidate)
        self.portable.toggled.connect(self.invalidate)
        self.max_results.textChanged.connect(self.invalidate)
        if own and own_box.findText(own)>=0:own_box.setCurrentText(own)
        else:own_box.setCurrentText('選択してください')
        if filename:self.filters['filename'].setText(filename)
        if autorun:QTimer.singleShot(0,self.run_search)
    def browse_log_file(self):
        selected,_=QFileDialog.getOpenFileName(self,'対象ログファイルを選択',str(self.repo.book),'PSLogログ (*.txt);;すべてのファイル (*)')
        if not selected:return
        chosen=Path(selected)
        try:
            if chosen.resolve().parent!=self.repo.book.resolve():
                QMessageBox.warning(self,'対象ログファイル','PSLogの logbook フォルダー内のログファイルを選択してください。')
                return
        except OSError as e:
            QMessageBox.warning(self,'対象ログファイル',str(e));return
        self.filters['filename'].setText(chosen.name)
    def invalidate(self):
        self.result_hits=[];self.search_status_base='';self.problems.clear();self.problems.hide()
        self.model.reset([]);self.selection_changed();self.status.setText('条件を変更しました。検索してください。')
    def selected(self):
        rows=self.table.selectionModel().selectedRows()
        return self.model.hits[rows[0].row()] if rows else None
    def selection_changed(self,*args):
        h=self.selected();editable=bool(h and h.editable)
        self.edit_button.setEnabled(editable);self.qsl_button.setEnabled(editable)
        can_export=bool(self.model.checked_hits());self.delete_button.setEnabled(can_export);self.party_button.setEnabled(can_export);self.pota_button.setEnabled(can_export);self.sota_button.setEnabled(can_export);self.contest_button.setEnabled(can_export);self.export_button.setEnabled(can_export)
        self.select_all_button.setEnabled(bool(self.model.hits));self.clear_all_button.setEnabled(bool(self.model.hits))
        self.details.setPlainText((detail(h)+ ('\n\nこのファイルに要確認行があるため編集・削除できません。' if not editable else '')) if h else '一覧から交信を選ぶと詳細を表示します。')
        if self.search_status_base:self._update_search_status()
    def run_search(self):
        self.result_hits=[];self.model.reset([]);self.selection_changed();self.problems.hide()
        try:
            limit_text=normalize_time(self.max_results.text())
            if not limit_text.isdigit() or int(limit_text)<1:
                raise ValueError('最大表示件数は1以上の数字で入力してください。')
            limit=int(limit_text)
            values={k:(e.currentText() if isinstance(e,QComboBox) else e.text()).strip() for k,e in self.filters.items()}
            if values.get('own')=='選択してください':raise ValueError('対象自局を選択してください。')
            values['start']=normalize_time(values['start']);values['end']=normalize_time(values['end'])
            result=search(self.repo,Criteria(**values,portable=self.portable.isChecked()))
        except (ValueError,StorageError,OSError) as e:self.status.setText(str(e));return
        self.result_hits=list(result.hits);total=len(self.result_hits);shown=self.result_hits[:limit]
        self.model.reset(shown);self.selection_changed()
        if total>limit:
            count_text=f'{total:,}件中 {len(shown):,}件表示（最大表示件数 {limit:,}）'
        else:
            count_text=f'{total:,}件'
        self.search_status_base=f'{count_text} / 対象{result.files}ファイル　要確認{len(result.problems)}件。一覧内をスクロールできます。'
        self._update_search_status()
        if result.problems:self.problems.setPlainText('\n'.join(result.problems));self.problems.show()
    def _update_search_status(self):
        note=f' 下部の削除・POTA・SOTA・QSOパーティー・コンテスト提出・エクスポートは、一覧に表示中のチェック済み {len(self.model.checked_hits()):,}件だけを対象にします。' if self.model.hits else ''
        self.status.setText(self.search_status_base+note)
    def finish_operation(self,dialog):
        dialog.exec()
        if dialog.saved:
            self.logs_changed.emit();self.run_search()
            self.status.setText('原本へ反映しました。'+self.status.text())
    def show_detail(self):
        h=self.selected()
        if not h:return
        dialog=DetailDialog(self.repo,h,self);dialog.exec()
        if dialog.saved:
            self.logs_changed.emit();self.run_search()
            self.status.setText('原本へ反映しました。'+self.status.text())
    def qsl_selected(self):
        h=self.selected()
        if h and h.editable:self.finish_operation(QSLQuickDialog(self.repo,h,self))
    def edit_selected(self):
        h=self.selected()
        if h and h.editable:self.finish_operation(EditDialog(h,self))
    def delete_checked(self):
        hits=self._checked_export_hits()
        if not hits:return
        if any(not h.editable for h in hits):
            QMessageBox.warning(self,'チェックした交信の削除','チェック済みの検索結果に要確認行を含むログがあります。\n原本を確認・修正してから再検索してください。')
            return
        self.finish_operation(CheckedDeleteDialog(self.repo,hits,self))
    def _checked_export_hits(self):return self.model.checked_hits()
    def _export_hits(self,kind):
        hits=self._checked_export_hits()
        if not hits:return None,None
        if any(not h.editable for h in hits):
            QMessageBox.warning(self,'特殊なエクスポート','チェック済みの検索結果に要確認行を含むログがあります。\n原本を確認・修正してから再検索してください。')
            return None,None
        owns=sorted({h.own for h in hits})
        if len(owns)!=1:
            QMessageBox.warning(self,'特殊なエクスポート',f'チェック済みの検索結果に複数の自局コールが含まれています。\n{kind}用は1つの運用コールだけにチェックしてから進んでください。\n\n'+', '.join(owns))
            return None,None
        return owns[0],hits
    def open_party(self):
        own,hits=self._export_hits('QSOパーティー')
        if not own:return
        QMessageBox.information(self,'QSOパーティーへ',
            '「1 対象・抽出」でパーティーを設定してください。\n\nチェックした交信は「2 確認・選択」へ渡します。')
        from activity_ui import ActivityDialog
        ActivityDialog(self.repo,own,self,hits=hits).exec()
    def open_pota(self):
        own,hits=self._export_hits('POTA')
        if not own:return
        from pota_ui import PotaDialog
        PotaDialog(self.repo,own,self,hits=hits).exec()
    def open_sota(self):
        own,hits=self._export_hits('SOTA')
        if not own:return
        from sota_ui import SotaDialog
        SotaDialog(self.repo,own,self,hits=hits).exec()
    def open_contest(self):
        own,hits=self._export_hits('コンテスト提出')
        if not own:return
        from contest_ui import ContestDialog
        ContestDialog(self.repo,own,self,hits=hits).exec()
    def open_export(self):
        hits=self._checked_export_hits()
        if not hits:return
        if any(not h.editable for h in hits):
            QMessageBox.warning(self,'通常エクスポート','チェック済みの検索結果に要確認行を含むログがあります。\n原本を確認・修正してから再検索してください。')
            return
        from export_ui import ExportDialog
        ExportDialog(self.repo,self.filters['own'].currentText().strip(),self,hits=hits).exec()
