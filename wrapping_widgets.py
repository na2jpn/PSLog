"""Checkbox labels that wrap within a form instead of widening its viewport."""
from PySide6.QtCore import Qt,QSize,QRect
from PySide6.QtWidgets import QCheckBox,QSizePolicy,QStyle,QStyleOptionButton,QStylePainter

class WrappedCheckBox(QCheckBox):
    def __init__(self,text='',parent=None):
        super().__init__(text,parent)
        policy=QSizePolicy(QSizePolicy.Preferred,QSizePolicy.Preferred);policy.setHeightForWidth(True);self.setSizePolicy(policy)
    def _offset(self):return self.style().pixelMetric(QStyle.PM_IndicatorWidth,None,self)+self.style().pixelMetric(QStyle.PM_CheckBoxLabelSpacing,None,self)+6
    def hasHeightForWidth(self):return True
    def heightForWidth(self,width):
        offset=self._offset();height=self.fontMetrics().boundingRect(QRect(0,0,max(20,width-offset),100000),Qt.TextWordWrap,self.text()).height()
        return max(self.style().pixelMetric(QStyle.PM_IndicatorHeight,None,self),height)+8
    def sizeHint(self):return QSize(340,self.heightForWidth(340))
    def minimumSizeHint(self):return QSize(100,self.fontMetrics().height()+8)
    def hitButton(self,pos):return self.rect().contains(pos)
    def paintEvent(self,event):
        painter=QStylePainter(self);option=QStyleOptionButton();self.initStyleOption(option);option.text='';painter.drawControl(QStyle.CE_CheckBox,option)
        rect=self.rect().adjusted(self._offset(),3,-3,-3)
        self.style().drawItemText(painter,rect,Qt.TextWordWrap|Qt.AlignVCenter|Qt.AlignLeft,self.palette(),self.isEnabled(),self.text(),self.foregroundRole())
