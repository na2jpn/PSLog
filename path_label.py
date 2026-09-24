"""Resizable absolute-path label with full-path tooltip and copy action."""
from PySide6.QtCore import Qt,QSize
from PySide6.QtWidgets import QLabel,QSizePolicy,QMenu,QApplication

class PathLabel(QLabel):
    def __init__(self,text='',parent=None):
        super().__init__('',parent);self.full_text='';self.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Preferred)
        self.setContextMenuPolicy(Qt.CustomContextMenu);self.customContextMenuRequested.connect(self.menu);self.setText(text)
    def setText(self,text):
        self.full_text=str(text);self.setToolTip(self.full_text);self.refresh()
    def text(self):return self.full_text
    def refresh(self):
        QLabel.setText(self,self.fontMetrics().elidedText(self.full_text,Qt.ElideMiddle,max(0,self.contentsRect().width())))
    def resizeEvent(self,event):super().resizeEvent(event);self.refresh()
    def minimumSizeHint(self):return QSize(0,super().minimumSizeHint().height())
    def menu(self,pos):
        menu=QMenu(self);action=menu.addAction('全文をコピー')
        if menu.exec(self.mapToGlobal(pos))==action:QApplication.clipboard().setText(self.full_text)
