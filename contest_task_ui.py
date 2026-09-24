"""Modal background work: keep Qt responsive without concurrent user edits."""
from PySide6.QtCore import QThread,QTimer,Qt
from PySide6.QtWidgets import QDialog,QVBoxLayout,QLabel,QProgressBar

class Worker(QThread):
    def __init__(self,operation,parent=None):
        super().__init__(parent);self.operation=operation;self.value=None;self.error=None
    def run(self):
        try:self.value=self.operation()
        except Exception as e:self.error=e

class TaskDialog(QDialog):
    def __init__(self,parent,title,operation):
        super().__init__(parent);self.setWindowTitle(title);self.setWindowModality(Qt.ApplicationModal)
        self.setWindowFlag(Qt.WindowCloseButtonHint,False)
        layout=QVBoxLayout(self);layout.addWidget(QLabel(title+'\n完了までお待ちください。'))
        bar=QProgressBar();bar.setRange(0,0);layout.addWidget(bar)
        self.worker=Worker(operation,self);self.worker.finished.connect(self.complete)
    def reject(self):pass  # Do not detach from a still-running read/write operation.
    def closeEvent(self,event):event.ignore()
    def complete(self):self.accept()

def run_task(parent,title,operation):
    dialog=TaskDialog(parent,title,operation)
    QTimer.singleShot(0,dialog.worker.start)
    dialog.exec();dialog.worker.wait()
    value,error=dialog.worker.value,dialog.worker.error
    dialog.deleteLater()
    if error is not None:raise error
    return value
