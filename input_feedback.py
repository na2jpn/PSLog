"""Focus the invalid field and reveal it inside scroll areas."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QScrollArea,QComboBox

def focus_error(error,fields):
    widget=fields.get(getattr(error,'field',None))
    if widget is None:return
    widget.setFocus(Qt.OtherFocusReason)
    editor=widget.lineEdit() if isinstance(widget,QComboBox) else widget
    if editor is not None and hasattr(editor,'selectAll'):editor.selectAll()
    parent=widget.parentWidget()
    while parent is not None:
        if isinstance(parent,QScrollArea):parent.ensureWidgetVisible(widget)
        parent=parent.parentWidget()
