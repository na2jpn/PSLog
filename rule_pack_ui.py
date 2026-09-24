from PySide6.QtWidgets import (QVBoxLayout,QHBoxLayout,QLabel,QTableWidget,QTableWidgetItem,QComboBox,QMessageBox,QAbstractItemView,QHeaderView)
from window_geometry import SafeDialog
from search_ui import button
from rule_pack import preview,install
from storage import StorageError

class RulePackDialog(SafeDialog):
    def __init__(self,store,path,parent=None):
        super().__init__(parent);self.store=store;self.plan=preview(store,path);self.choices={}
        self.setWindowTitle('ルールパックを取り込む');self.resize(1060,600)
        box=QVBoxLayout(self);intro=QLabel('新規追加・更新の内容を確認してください。競合は初期状態では現在のルールを残します。旧年度は削除しません。');intro.setWordWrap(True);box.addWidget(intro)
        self.table=QTableWidget(len(self.plan.items),6);self.table.setHorizontalHeaderLabels(['コンテスト','年度','改訂','状態','理由','競合時の処理']);self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents);self.table.horizontalHeader().setSectionResizeMode(0,QHeaderView.Stretch);box.addWidget(self.table,1)
        for row,item in enumerate(self.plan.items):
            for col,value in enumerate((item.rule['name'],item.rule['year'],item.revision,item.status,item.reason)):
                self.table.setItem(row,col,QTableWidgetItem(str(value)))
            if item.status=='競合':
                choice=QComboBox();choice.addItems(['現在のものを残す','配布版に更新']);self.table.setCellWidget(row,5,choice);self.choices[item.target.name]=choice
        self.status=QLabel();self.status.setWordWrap(True);box.addWidget(self.status);buttons=QHBoxLayout();buttons.addStretch();self.apply_button=button('追加・更新を実行',self.apply);buttons.addWidget(self.apply_button);buttons.addWidget(button('閉じる',self.reject));box.addLayout(buttons)
    def apply(self):
        chosen=[name for name,combo in self.choices.items() if combo.currentIndex()==1]
        if QMessageBox.question(self,'ルールの追加・更新','一覧の内容を反映しますか？更新前のファイルはバックアップされます。')!=QMessageBox.Yes:return
        try:
            count=install(self.store,self.plan,chosen)
            self.status.setText(f'{count}件を追加・更新しました。'+self.store.catalog_warning);self.apply_button.setEnabled(False)
        except (ValueError,OSError,StorageError) as e:
            self.status.setText(str(e)+'\n再実行する前に画面を閉じてZIPを読み直してください。');self.apply_button.setEnabled(False)
