"""Inline HIS QTH suggestions backed by PSLog's location database."""
from __future__ import annotations

import re
from PySide6.QtCore import Qt,QModelIndex
from PySide6.QtGui import QStandardItem,QStandardItemModel
from PySide6.QtWidgets import QCompleter

from locations import load,exact_matches,qth_for_row

_JAPANESE=re.compile(r'[\u3040-\u30ff\u3400-\u9fff]')


def _english(row):
    return qth_for_row(row)


def _code(row):
    return str(row['code']).strip()

def _display_code(row):
    return f"{row['kind']} {row['code']}"



class LocationSuggestor:
    """Attach a bilingual completer and safe JCC/JCG autofill to one QTH field."""
    def __init__(self,root,qth_edit,code_edit):
        self.root=root;self.qth=qth_edit;self.code=code_edit;self.data=load(root)
        self.rows=list(self.data.get('rows',[]));self.prefer_japanese=False;self.last_auto_code=''
        self.model=QStandardItemModel(self.qth)
        for index,row in enumerate(self.rows):
            english=_english(row)
            display=row.get('name','')
            if english:display+=' / '+english
            display+=f"  [{_display_code(row)}]"
            item=QStandardItem(display);item.setData(index,Qt.ItemDataRole.UserRole);self.model.appendRow(item)
        self.completer=QCompleter(self.model,self.qth)
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.completer.setMaxVisibleItems(12)
        self.qth.setCompleter(self.completer)
        self.qth.textEdited.connect(self._typed)
        self.qth.editingFinished.connect(self._exact)
        self.completer.activated[QModelIndex].connect(self._activated)

    def set_enabled(self,on):
        self.qth.setCompleter(self.completer if on else None)

    def _typed(self,text):
        self.prefer_japanese=bool(_JAPANESE.search(str(text)))

    def _can_auto_code(self):
        current=self.code.text().strip()
        return not current or current==self.last_auto_code

    def _apply_code(self,row):
        value=_code(row)
        if self._can_auto_code():
            self.code.setText(value);self.last_auto_code=value

    def _activated(self,index):
        # PySide may deliver QModelIndex or a string overload.  Prefer the index
        # because it unambiguously identifies duplicate-looking labels.
        try:row_index=index.data(Qt.ItemDataRole.UserRole)
        except Exception:return
        try:row=self.rows[int(row_index)]
        except (TypeError,ValueError,IndexError):return
        english=_english(row)
        value=row.get('name','') if self.prefer_japanese or not english else english
        self.qth.setText(value);self._apply_code(row)

    def _exact(self):
        matches=exact_matches(self.data,self.qth.text())
        if len(matches)==1:self._apply_code(matches[0])
