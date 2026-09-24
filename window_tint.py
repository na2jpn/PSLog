"""Small, per-window color cues for PSLog dialogs.

Only the window background and (on supported Windows versions) the native
caption are tinted.  Widget/control colors are deliberately left to the
existing application style so text remains dark and editable fields stay
unchanged.
"""
import ctypes
import sys

from PySide6.QtCore import QTimer
from PySide6.QtGui import QColor, QPalette


TINTS = {
    'contest':   ('#E7F1FB', '#D6E7F7'),  # blue
    'award':     ('#FCEDE8', '#F4DDD5'),  # vermilion
    'qso_party': ('#FFF0DA', '#F5DFC0'),  # orange
    'blacklist': ('#FCE9E9', '#F3D5D5'),  # red
    'import':    ('#E6F4F7', '#D3E9EE'),  # blue/cyan, distinct from contest
    'export':    ('#F2EBF8', '#E5D8F0'),  # purple
    'edit':      ('#FFF7D9', '#F2E8B9'),  # yellow
}


def _colorref(value):
    value = value.lstrip('#')
    r, g, b = (int(value[i:i + 2], 16) for i in (0, 2, 4))
    return r | (g << 8) | (b << 16)


def _native_caption(widget, caption, text='#202020'):
    """Tint the Windows 11 native title bar; harmlessly no-op elsewhere."""
    if sys.platform != 'win32':
        return
    try:
        hwnd = int(widget.winId())
        dwm = ctypes.windll.dwmapi
        for attr, color in ((35, caption), (36, text)):
            value = ctypes.c_uint(_colorref(color))
            dwm.DwmSetWindowAttribute(
                ctypes.c_void_p(hwnd), ctypes.c_uint(attr),
                ctypes.byref(value), ctypes.sizeof(value)
            )
    except Exception:
        # Older Windows versions / unavailable DWM attributes simply retain
        # the system title bar color.
        pass


def apply_window_tint(widget, family):
    """Apply a light functional tint without restyling controls or text."""
    body, caption = TINTS[family]

    palette = widget.palette()
    palette.setColor(QPalette.ColorRole.Window, QColor(body))
    widget.setPalette(palette)
    widget.setAutoFillBackground(True)

    # SafeDialog installs a QScrollArea around many dialogs at show time.
    # Override only those large background surfaces; controls keep the
    # application's existing style/palette.
    widget.setObjectName('pslogTintWindow')
    widget.setStyleSheet((widget.styleSheet() or '') + f'''
        QDialog#pslogTintWindow {{ background:{body}; }}
        QDialog#pslogTintWindow QScrollArea {{ background:{body}; }}
        QDialog#pslogTintWindow QScrollArea QWidget#qt_scrollarea_viewport {{ background:{body}; }}
        QDialog#pslogTintWindow QTabWidget::pane {{ background:{body}; }}
    ''')

    # Delay until the native handle is available. winId() also makes this
    # reliable for modal exec() dialogs.
    QTimer.singleShot(0, lambda w=widget, c=caption: _native_caption(w, c))
