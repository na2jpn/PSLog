"""Shared, non-destructive band/mode and remarks selection."""
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QCheckBox,QPushButton,QGridLayout,QSizePolicy
from activity_values import BANDS,MODES,norm,band_value,band_group,mode_group
class FilterPane(QWidget):
 def __init__(self,warc=False,parent=None):
  super().__init__(parent);v=QVBoxLayout(self);self.setSizePolicy(QSizePolicy.Preferred,QSizePolicy.Fixed);self.bands={};self.modes={}
  for names,d in ((BANDS,self.bands),(MODES,self.modes)):
   row=QGridLayout();v.addLayout(row)
   for index,name in enumerate(names):
    c=QCheckBox(name);c.setChecked(warc or name not in ('10','18','24'));d[name]=c;row.addWidget(c,index//6,index%6)
   for index,(label,on) in enumerate([('全選択',True),('全解除',False)]):
    b=QPushButton(label);b.clicked.connect(lambda _,d=d,on=on:[c.setChecked(on) for c in d.values()]);row.addWidget(b,(len(names)-1)//6,6+index)
 def state(self):return tuple(k for k,c in self.bands.items() if c.isChecked()),tuple(k for k,c in self.modes.items() if c.isChecked())
 def accepts(self,q):
  bands,modes=self.state();g=band_group(q.band)
  return (g in bands or g is None and len(bands)==len(BANDS)) and mode_group(q.mode) in modes
