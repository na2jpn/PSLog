"""Organizer display; no website links."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel

def source_label():
    label=QLabel();label.setWordWrap(True);label.setTextFormat(Qt.PlainText)
    return label

def source_text(rule):
    return '主催：'+((rule or {}).get('organizer','') or '未登録')
