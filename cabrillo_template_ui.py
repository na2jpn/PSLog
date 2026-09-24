from copy import deepcopy
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QVBoxLayout,QHBoxLayout,QFormLayout,QWidget,QLineEdit,QLabel,QComboBox,QListWidget,QListWidgetItem,QTabWidget,QPlainTextEdit,QTableWidget,QTableWidgetItem,QMessageBox,QAbstractItemView)
from window_geometry import SafeDialog
from search_ui import button
from contest_rule_ui import combo,spin
from cabrillo_templates import TemplateStore,default_template,validate,loads,dumps,SOURCES,V3,V2,ENUMS
from storage import StorageError

SOURCE_LABELS=['周波数','MODE','UTC日付','UTC時刻','自局コール','送信RST','送信番号','相手コール','受信RST','受信番号','自局GL','相手GL','送信機番号','固定文字']
class TemplateEditor(SafeDialog):
    def __init__(self,store,value=None,path=None,snapshot=None,parent=None):
        super().__init__(parent);self.store=store;self.value=deepcopy(value or default_template());self.baseline=deepcopy(self.value);self.path=path;self.snapshot=snapshot;self.saved_path=None
        self.setWindowTitle('Cabrillo出力テンプレート編集');self.resize(1040,690);box=QVBoxLayout(self);note=QLabel('規約は毎年改定される可能性があります。参照年と主催者指定の列構成を確認してください。');note.setWordWrap(True);note.setStyleSheet('color:#b32020');box.addWidget(note);self.tabs=QTabWidget();box.addWidget(self.tabs,1)
        w=QWidget();f=QFormLayout(w);self.tabs.addTab(w,'基本');self.fields={}
        for key,label in [('id','識別子'),('name','名称'),('url','参照URL'),('contest','CONTEST初期値'),('rule_id','関連する採点ルールID（任意）')]:e=QLineEdit();self.fields[key]=e;f.addRow(label,e)
        self.year=spin(2026);self.year.setRange(1900,9999);f.addRow('参照年',self.year);self.version=combo(['3.0','2.0']);f.addRow('Cabrillo版',self.version);f.addRow(button('選択版の標準ヘッダー欄へ変更',self.change_version_headers));self.encoding=combo(['ascii','utf-8','cp932']);f.addRow('文字コード（主催者の指定）',self.encoding);self.frequency=combo(['バンド識別値を使用可','HF実周波数を必須（VHF以上はバンド）']);f.addRow('周波数',self.frequency)
        self.headers=self.add_table('ヘッダー定義',['タグ','必須','初期値','候補（カンマ区切り）'],[190,50,190,340]);self.columns=self.add_table('QSO列',['項目','幅','寄せ','部分番号','固定文字'],[175,90,95,95,250]);self.modes=self.add_table('MODE対応',['元MODE','出力MODE（2文字）'],[280,280]);self.raw=QPlainTextEdit();w=QWidget();v=QVBoxLayout(w);v.addWidget(self.raw);row=QHBoxLayout();row.addWidget(button('画面の値をJSONへ',self.to_json));row.addWidget(button('JSONを検証して画面へ反映',self.from_json));v.addLayout(row);self.tabs.addTab(w,'JSON')
        self.status=QLabel();self.status.setWordWrap(True);box.addWidget(self.status);row=QHBoxLayout();row.addStretch();row.addWidget(button('保存',self.save));row.addWidget(button('別名保存',lambda:self.save(True)));row.addWidget(button('閉じる',self.reject));box.addLayout(row);self.populate()
    def add_table(self,title,labels,widths):
        w=QWidget();v=QVBoxLayout(w);table=QTableWidget(0,len(labels));table.setHorizontalHeaderLabels(labels);table.setSelectionBehavior(QAbstractItemView.SelectRows)
        for i,width in enumerate(widths):table.setColumnWidth(i,width)
        v.addWidget(table,1);row=QHBoxLayout()
        for label,fn in [('追加',lambda:self.add_row(table)),('削除',lambda:self.remove(table)),('上へ',lambda:self.move(table,-1)),('下へ',lambda:self.move(table,1))]:row.addWidget(button(label,fn))
        v.addLayout(row)
        if title=='QSO列':label=QLabel('列間は半角スペース1個。幅超過はエラー。部分番号0＝全文、1以降＝空白区切りの何番目か。');label.setWordWrap(True);v.addWidget(label)
        self.tabs.addTab(w,title);return table
    def add_row(self,table,value=None):
        i=table.rowCount();table.insertRow(i)
        if table is self.headers:
            value=value or {'tag':'','required':False,'default':'','choices':[]}
            for j,text in enumerate([value['tag'],'',value['default'],','.join(value['choices'])]):
                item=QTableWidgetItem(text)
                if j==1:item.setFlags(Qt.ItemIsEnabled|Qt.ItemIsUserCheckable);item.setCheckState(Qt.Checked if value['required'] else Qt.Unchecked)
                table.setItem(i,j,item)
        elif table is self.columns:
            value=value or {'source':'literal','width':3,'align':'left','part':0,'literal':''};source=combo(SOURCE_LABELS);source.setCurrentIndex(SOURCES.index(value['source']));table.setCellWidget(i,0,source);width=spin(value['width']);width.setRange(1,100);table.setCellWidget(i,1,width);align=combo(['左寄せ','右寄せ']);align.setCurrentIndex(0 if value['align']=='left' else 1);table.setCellWidget(i,2,align);part=spin(value['part']);part.setRange(0,20);table.setCellWidget(i,3,part);table.setItem(i,4,QTableWidgetItem(value['literal']))
        else:
            value=value or ('','')
            for j,text in enumerate(value):table.setItem(i,j,QTableWidgetItem(text))
    def rows(self,table):
        result=[]
        for i in range(table.rowCount()):
            if table is self.headers:result.append({'tag':table.item(i,0).text().strip(),'required':table.item(i,1).checkState()==Qt.Checked,'default':table.item(i,2).text(),'choices':[x.strip() for x in table.item(i,3).text().split(',') if x.strip()]})
            elif table is self.columns:result.append({'source':SOURCES[table.cellWidget(i,0).currentIndex()],'width':table.cellWidget(i,1).value(),'align':['left','right'][table.cellWidget(i,2).currentIndex()],'part':table.cellWidget(i,3).value(),'literal':table.item(i,4).text()})
            else:result.append((table.item(i,0).text().strip(),table.item(i,1).text().strip()))
        return result
    def remove(self,table):
        if table.currentRow()>=0:table.removeRow(table.currentRow())
    def move(self,table,delta):
        i=table.currentRow();j=i+delta
        if i<0 or not 0<=j<table.rowCount():return
        rows=self.rows(table);rows[i],rows[j]=rows[j],rows[i];table.setRowCount(0)
        for value in rows:self.add_row(table,value)
        table.selectRow(j)
    def populate(self):
        t=self.value
        for k,e in self.fields.items():e.setText(t[k])
        self.year.setValue(t['year']);self.version.setCurrentText(t['version']);self.encoding.setCurrentText(t['encoding']);self.frequency.setCurrentIndex(0 if t['frequency']=='band' else 1)
        for table,rows in [(self.headers,t['headers']),(self.columns,t['columns']),(self.modes,list(t['modes'].items()))]:
            table.setRowCount(0)
            for value in rows:self.add_row(table,value)
        self.raw.setPlainText(dumps(t));self.raw.document().setModified(False)
    def collect(self):
        t=deepcopy(self.value);t.update({k:e.text().strip() for k,e in self.fields.items()});t.update(year=self.year.value(),version=self.version.currentText(),encoding=self.encoding.currentText(),frequency=['band','actual'][self.frequency.currentIndex()],headers=self.rows(self.headers),columns=self.rows(self.columns));modes=self.rows(self.modes)
        if len({k for k,v in modes})!=len(modes):raise ValueError('元MODEが重複しています。')
        t['modes']=dict(modes);return validate(t)
    def change_version_headers(self):
        if QMessageBox.question(self,'ヘッダーを変更','版固有の部門ヘッダーを入れ替えます。入力済みの該当ヘッダーは破棄されます。続けますか？')!=QMessageBox.Yes:return
        rows=[h for h in self.rows(self.headers) if h['tag'] not in V3+V2];tags=V3 if self.version.currentText()=='3.0' else V2
        rows=[{'tag':tag,'required':tag in ('CATEGORY','CATEGORY-OPERATOR','CATEGORY-BAND','CATEGORY-MODE','CATEGORY-POWER'),'default':'','choices':ENUMS.get(tag,[])} for tag in tags]+rows;self.headers.setRowCount(0)
        for value in rows:self.add_row(self.headers,value)
    def to_json(self):
        try:
            if self.raw.document().isModified():raise ValueError('先にJSONの変更を画面へ反映してください。')
            self.value=self.collect();self.raw.setPlainText(dumps(self.value));self.raw.document().setModified(False)
        except ValueError as e:self.status.setText(str(e))
    def from_json(self):
        try:self.value=loads(self.raw.toPlainText());self.populate();self.status.setText('JSONを検証して反映しました。')
        except (ValueError,TypeError) as e:self.status.setText(str(e))
    def save(self,as_new=False):
        try:
            if self.raw.document().isModified():raise ValueError('JSONの変更を画面へ反映してください。')
            t=self.collect();self.saved_path,self.snapshot=self.store.save(t,None if as_new else self.path,None if as_new else self.snapshot);self.path=self.saved_path;self.value=t;self.baseline=deepcopy(t);self.populate();self.status.setText('保存しました: '+str(self.path))
        except (ValueError,OSError,StorageError) as e:self.status.setText(str(e))
    def reject(self):
        try:dirty=self.raw.document().isModified() or self.collect()!=self.baseline
        except ValueError:dirty=True
        if dirty and QMessageBox.question(self,'変更を破棄','未保存の変更を破棄して閉じますか？')!=QMessageBox.Yes:return
        super().reject()

class TemplatesDialog(SafeDialog):
    def __init__(self,root,parent=None):
        super().__init__(parent);self.store=TemplateStore(root);self.setWindowTitle('Cabrillo出力テンプレート管理・編集');self.resize(900,590);v=QVBoxLayout(self);self.search=QLineEdit();self.search.setPlaceholderText('名称・CONTEST・参照年で検索');v.addWidget(self.search);self.list=QListWidget();v.addWidget(self.list,1);self.status=QLabel();self.status.setWordWrap(True);v.addWidget(self.status);row=QHBoxLayout()
        for label,cb in [('新規作成',self.new),('編集',self.edit),('複製',self.copy),('再読込',self.refresh),('閉じる',self.reject)]:row.addWidget(button(label,cb))
        v.addLayout(row);self.search.textChanged.connect(self.refresh);self.list.itemDoubleClicked.connect(self.edit);self.refresh()
    def refresh(self,*args):
        self.list.clear();errors=[]
        for path in self.store.files():
            try:
                t,s=self.store.read(path);label=f"{t['name']} / {t['contest']} / {t['year']}年版 / Cabrillo {t['version']}"
                if self.search.text().casefold() not in label.casefold():continue
                item=QListWidgetItem(label);item.setData(Qt.UserRole,str(path));item.setToolTip(str(path));self.list.addItem(item)
            except (ValueError,OSError,StorageError,TypeError) as e:errors.append(path.name+': '+str(e))
        self.status.setText('\n'.join(errors) or '新規テンプレートの列配置は編集開始用です。主催者指定の書式と照合して保存してください。')
    def new(self):TemplateEditor(self.store,parent=self).exec();self.refresh()
    def edit(self,*args):self.open(False)
    def copy(self):self.open(True)
    def open(self,copy):
        item=self.list.currentItem()
        if not item:return
        try:
            path=item.data(Qt.UserRole);t,s=self.store.read(path)
            if copy:t['id']=t['id'][:70]+'-copy';t['name']+='（複製）';path=None;s=None
            TemplateEditor(self.store,t,path,s,self).exec();self.refresh()
        except (ValueError,OSError,StorageError) as e:self.status.setText(str(e))
