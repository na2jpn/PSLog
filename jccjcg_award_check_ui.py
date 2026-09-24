"""JCC/JCG worked/QSL checker UI for award-oriented review.

PATCH04 FIX1 keeps the window responsive while the log scan runs and delays
creation of the large per-prefecture detail table until the user expands that
prefecture.  The award aggregation itself stays read-only.
"""
from PySide6.QtCore import Qt,QObject,QThread,Signal,Slot
from PySide6.QtWidgets import (
    QDialog,QVBoxLayout,QHBoxLayout,QLabel,QComboBox,QCheckBox,QPushButton,
    QTreeWidget,QTreeWidgetItem,QHeaderView,QAbstractItemView,QProgressBar,
)

from storage import VERSION,StorageError
from logbook_sources import amateur_station_calls,base_station_call
from jccjcg_award_check import aggregate,STATE_NONE,STATE_TEXT,BAND_LABEL
from window_tint import apply_window_tint
from window_geometry import SafeDialog as QDialog


class _AggregateWorker(QObject):
    """Run the file scan outside the GUI thread.

    Repository.open() and aggregate() are read-only here; the worker never
    mutates a log or touches Qt widgets.
    """
    completed=Signal(object)
    failed=Signal(str)

    def __init__(self,repo,own,portable):
        super().__init__();self.repo=repo;self.own=own;self.portable=portable

    @Slot()
    def work(self):
        try:
            result=aggregate(self.repo,self.own,self.portable)
        except (ValueError,StorageError,OSError) as e:
            self.failed.emit(str(e));return
        except Exception as e:  # keep an unexpected worker error from leaving the dialog permanently busy
            self.failed.emit(f'集計処理中にエラーが発生しました: {type(e).__name__}: {e}');return
        self.completed.emit(result)


class JccJcgAwardCheckDialog(QDialog):
    def __init__(self,repo,preferred='',parent=None):
        super().__init__(parent);self.repo=repo;self.result=None
        self._thread=None;self._worker=None
        self.setWindowTitle(f'PSLog Ver{VERSION} — JCC/JCG交信チェック');self.resize(1220,760);apply_window_tint(self,'award')
        outer=QVBoxLayout(self)
        note=QLabel('※「集計」を押すと対象のアマチュア無線ログ全体を確認します。ログ件数・交信件数によっては処理に時間がかかる場合があります。')
        note.setWordWrap(True);outer.addWidget(note)
        row=QHBoxLayout();row.addWidget(QLabel('対象自局コール'))
        self.own=QComboBox();calls=amateur_station_calls(repo)
        if calls:
            self.own.addItems(calls)
            wanted=base_station_call(preferred)
            if wanted and self.own.findText(wanted)>=0:self.own.setCurrentText(wanted)
        else:
            self.own.addItem('ログがありません');self.own.setEnabled(False)
        row.addWidget(self.own,1)
        self.portable=QCheckBox('/1・/P 等の運用サフィックス付きも含む');self.portable.setChecked(True);row.addWidget(self.portable)
        self.run_button=QPushButton('集計');self.run_button.setEnabled(bool(calls));self.run_button.clicked.connect(self.run);row.addWidget(self.run_button)
        outer.addLayout(row)
        status_row=QHBoxLayout()
        self.status=QLabel('対象自局コールを選び、「集計」を押してください。');self.status.setWordWrap(True);status_row.addWidget(self.status,1)
        self.loading=QProgressBar();self.loading.setRange(0,0);self.loading.setTextVisible(False);self.loading.setMaximumWidth(180);self.loading.setVisible(False);status_row.addWidget(self.loading)
        outer.addLayout(status_row)
        self.tree=QTreeWidget();self.tree.setUniformRowHeights(True);self.tree.setAlternatingRowColors(True)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection);self.tree.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tree.itemExpanded.connect(self._populate_prefecture)
        outer.addWidget(self.tree,1)
        bottom=QHBoxLayout();bottom.addStretch();self.close_button=QPushButton('閉じる');self.close_button.clicked.connect(self.accept);bottom.addWidget(self.close_button);outer.addLayout(bottom)
        self._empty_tree()

    def _empty_tree(self):
        self.tree.clear();self.tree.setColumnCount(4);self.tree.setHeaderLabels(['区分','コード','地域名','全バンド'])
        self.tree.header().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.tree.setColumnWidth(0,120);self.tree.setColumnWidth(1,90);self.tree.setColumnWidth(2,240);self.tree.setColumnWidth(3,90)

    @staticmethod
    def _state_text(value):return STATE_TEXT.get(value,'—')

    def _set_busy(self,busy):
        self.loading.setVisible(busy)
        self.run_button.setEnabled((not busy) and self.own.isEnabled())
        self.own.setEnabled((not busy) and self.own.count()>0 and self.own.itemText(0)!='ログがありません')
        self.portable.setEnabled(not busy)
        self.close_button.setEnabled(not busy)

    def run(self):
        if not self.own.isEnabled() or (self._thread is not None and self._thread.isRunning()):return
        own=self.own.currentText();portable=self.portable.isChecked()
        self.result=None;self._empty_tree();self.status.setToolTip('')
        self.status.setText('集計しています…');self._set_busy(True)
        thread=QThread(self);worker=_AggregateWorker(self.repo,own,portable);worker.moveToThread(thread)
        thread.started.connect(worker.work)
        worker.completed.connect(self._aggregate_completed)
        worker.failed.connect(self._aggregate_failed)
        worker.completed.connect(thread.quit);worker.failed.connect(thread.quit)
        worker.completed.connect(worker.deleteLater);worker.failed.connect(worker.deleteLater)
        thread.finished.connect(self._thread_finished);thread.finished.connect(thread.deleteLater)
        self._thread=thread;self._worker=worker;thread.start()

    @Slot(object)
    def _aggregate_completed(self,result):
        self.result=result;self._render(result)
        problem=f'／要確認 {len(result.problems):,}件' if result.problems else ''
        self.status.setText(f'{result.files:,}ファイル・{result.qsos:,}交信を確認、JCC/JCGコード一致 {result.matched:,}交信{problem}。都道府県は折りたたみ表示で、開いた県だけ詳細を読み込みます。')
        if result.problems:self.status.setToolTip('\n'.join(result.problems[:100]))
        else:self.status.setToolTip('')
        self.loading.setVisible(False)

    @Slot(str)
    def _aggregate_failed(self,message):
        self.result=None;self._empty_tree();self.status.setText(message);self.loading.setVisible(False)

    @Slot()
    def _thread_finished(self):
        self._thread=None;self._worker=None;self._set_busy(False)

    def _render(self,result):
        """Render only the 47 prefecture rows; children are created on demand."""
        self.tree.setUpdatesEnabled(False)
        try:
            self.tree.clear();headers=['区分','コード','地域名','全バンド']+[BAND_LABEL.get(b,b) for b in result.bands]
            self.tree.setColumnCount(len(headers));self.tree.setHeaderLabels(headers)
            header=self.tree.header();header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
            self.tree.setColumnWidth(0,120);self.tree.setColumnWidth(1,90);self.tree.setColumnWidth(2,240);self.tree.setColumnWidth(3,90)
            for col in range(4,len(headers)):self.tree.setColumnWidth(col,78)
            for index,pref in enumerate(result.prefectures):
                summary=pref.folded_summary();title=f'{pref.code}.{pref.name}'+(('　'+summary) if summary else '')
                parent=QTreeWidgetItem([title]+['']*(len(headers)-1));parent.setExpanded(False)
                parent.setData(0,Qt.ItemDataRole.UserRole,index)
                parent.setChildIndicatorPolicy(QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator)
                font=parent.font(0);font.setBold(True);parent.setFont(0,font);self.tree.addTopLevelItem(parent);parent.setFirstColumnSpanned(True)
        finally:self.tree.setUpdatesEnabled(True)

    @Slot(QTreeWidgetItem)
    def _populate_prefecture(self,parent):
        """Create one prefecture's JCC/JCG rows only when it is first opened."""
        if self.result is None or parent.parent() is not None or parent.childCount():return
        index=parent.data(0,Qt.ItemDataRole.UserRole)
        if index is None:return
        try:pref=self.result.prefectures[int(index)]
        except (ValueError,TypeError,IndexError):return
        self.tree.setUpdatesEnabled(False)
        try:
            for loc in pref.locations:
                values=[loc.kind,loc.code,loc.name,self._state_text(loc.all_state)]+[self._state_text(loc.states.get(b,STATE_NONE)) for b in self.result.bands]
                item=QTreeWidgetItem(values);parent.addChild(item)
                for col,value in enumerate(values[3:],3):
                    if value=='QSL済':item.setToolTip(col,'QSL受領済')
                    elif value=='交信済':item.setToolTip(col,'交信済・QSL未受領')
        finally:self.tree.setUpdatesEnabled(True)

    def reject(self):
        if self._thread is not None and self._thread.isRunning():
            self.status.setText('集計中です。完了してから閉じてください。');return
        super().reject()

    def closeEvent(self,event):
        if self._thread is not None and self._thread.isRunning():
            self.status.setText('集計中です。完了してから閉じてください。');event.ignore();return
        super().closeEvent(event)
