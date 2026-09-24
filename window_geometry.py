"""Qt logical-pixel geometry, fitted to current available screen areas."""
from PySide6.QtCore import QRect,QTimer
from PySide6.QtWidgets import QApplication,QDialog,QWidget,QVBoxLayout,QScrollArea


def fitted(saved,areas,default=(1360,850),minimum=(640,420)):
    areas=[r for r in areas if r.width()>0 and r.height()>0]
    if not areas:areas=[QRect(0,0,800,600)]
    valid=isinstance(saved,dict) and all(type(saved.get(k)) is int and abs(saved[k])<10000000 for k in ('x','y','width','height'))
    old=QRect(saved['x'],saved['y'],saved['width'],saved['height']) if valid else QRect()
    area=max(areas,key=lambda a:max(0,a.intersected(old).width())*max(0,a.intersected(old).height())) if old.isValid() else areas[0]
    w=min(area.width(),max(minimum[0],old.width() if old.isValid() else default[0]))
    h=min(area.height(),max(minimum[1],old.height() if old.isValid() else default[1]))
    intersects=old.isValid() and old.intersects(area)
    x=min(max(old.x(),area.x()),area.x()+area.width()-w) if intersects else area.x()+(area.width()-w)//2
    y=min(max(old.y(),area.y()),area.y()+area.height()-h) if intersects else area.y()+(area.height()-h)//2
    return QRect(x,y,w,h)

def state(widget):
    rect=widget.normalGeometry() if widget.isMaximized() or widget.isMinimized() else widget.geometry()
    return {'x':rect.x(),'y':rect.y(),'width':rect.width(),'height':rect.height(),
            'maximized':bool(widget.isMaximized() or (widget.isMinimized() and getattr(widget,'_was_maximized',False)))}

def areas(widget):
    screens=QApplication.screens();primary=QApplication.primaryScreen()
    screens=([primary] if primary else [])+[s for s in screens if s!=primary]
    handle=widget.windowHandle();margins=handle.frameMargins() if handle else None
    result=[]
    for screen in screens:
        r=screen.availableGeometry()
        if margins:r=r.adjusted(margins.left(),margins.top(),-margins.right(),-margins.bottom())
        result.append(r)
    return result

def fit_widget(widget,saved=None,default=(1360,850),minimum=(640,420)):
    rect=fitted(state(widget) if saved is None else saved,areas(widget),default,minimum)
    widget.setMinimumSize(min(minimum[0],rect.width()),min(minimum[1],rect.height()))
    widget.setGeometry(rect)
    return rect

class SafeDialog(QDialog):
    """Custom dialogs remain usable on small screens via outer scrolling."""
    Accepted=QDialog.DialogCode.Accepted
    Rejected=QDialog.DialogCode.Rejected
    def showEvent(self,event):
        if not getattr(self,'_scroll_installed',False):
            self._scroll_installed=True
            # Most dialogs get a safety scroll around the whole layout.
            # A few complex dialogs (e.g. contest workflow) provide their own
            # central scroll area so their footer/navigation remains visible.
            if not getattr(self,'_own_scroll_area',False):
                layout=self.layout()
                if layout:
                    body=QWidget();body.setLayout(layout)
                    body.setMinimumSize(body.minimumSizeHint())
                    outer=QVBoxLayout(self);outer.setContentsMargins(0,0,0,0)
                    scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(body);outer.addWidget(scroll)
            self._preferred=(self.width(),self.height())
            app=QApplication.instance()
            app.screenRemoved.connect(self.schedule_fit)
            app.screenAdded.connect(self.schedule_fit)
            for screen in app.screens():
                screen.availableGeometryChanged.connect(self.schedule_fit)
            if self.windowHandle():self.windowHandle().screenChanged.connect(self.schedule_fit)
        super().showEvent(event)
        QTimer.singleShot(0,self.fit_screen)
    def schedule_fit(self,*args):
        if self.isVisible():QTimer.singleShot(0,self.fit_screen)
    def fit_screen(self):
        if self.isVisible():fit_widget(self,default=self._preferred,minimum=(min(400,self._preferred[0]),min(280,self._preferred[1])))
