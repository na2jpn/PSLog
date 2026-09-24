"""Backward-compatible structured RMKS helpers.

PSLog keeps the canonical TXT format at 11 columns.  Optional secondary/future
remarks live inside the existing RMKS column and are separated by reserved
ASCII markers such as ``<<RMKS2>>``.  No marker means the historical single
RMKS value and remains byte/text compatible with old logs.
"""
from __future__ import annotations

import re

RMKS2_MARKER='<<RMKS2>>'
_TAG_RE=re.compile(r'<<RMKS([2-9][0-9]*)>>')


def primary(text):
    """Return RMKS1 (text before the first reserved RMKS section marker)."""
    value=str(text or '')
    match=_TAG_RE.search(value)
    return value[:match.start()].rstrip() if match else value


def split_for_ui(text):
    """Return ``(rmks1, rmks2, extras)`` for editing.

    ``extras`` is a raw list of future section tuples ``(number, text)``.  The
    current UI edits RMKS1/RMKS2 only, but later RMKS3+ data is not discarded.
    """
    value=str(text or '')
    matches=list(_TAG_RE.finditer(value))
    if not matches:return value,'',[]
    first=value[:matches[0].start()].rstrip()
    sections=[]
    for i,match in enumerate(matches):
        end=matches[i+1].start() if i+1<len(matches) else len(value)
        sections.append((int(match.group(1)),value[match.end():end].strip()))
    rmks2='';extras=[];seen2=False
    for number,body in sections:
        if number==2 and not seen2:
            rmks2=body;seen2=True
        else:extras.append((number,body))
    return first,rmks2,extras


def compose(rmks1,rmks2='',extras=()):
    """Serialize UI remarks using one-space marker boundaries.

    If RMKS2 and future sections are empty, historical single-RMKS text is
    returned unchanged (apart from no forced quoting/escaping).
    """
    first=str(rmks1 or '')
    second=str(rmks2 or '')
    extra=list(extras or ())
    parts=[first]
    if second or extra:
        parts.append(f'{RMKS2_MARKER} {second}'.rstrip())
    for number,body in extra:
        try:number=int(number)
        except (TypeError,ValueError):continue
        if number<2:continue
        parts.append(f'<<RMKS{number}>> {str(body or "")}'.rstrip())
    return ' '.join(p for p in parts if p!='') if first else ' '.join(parts[1:])


def validate_component(value,label='RMKS'):
    """Reject reserved structural markers in user-editable component text."""
    match=_TAG_RE.search(str(value or ''))
    if match:
        raise ValueError(f'{label}に予約文字列 {match.group()} は使用できません。')
    return value


def replace_primary(text,new_primary):
    """Replace RMKS1 while preserving RMKS2/future sections."""
    value=str(text or '')
    match=_TAG_RE.search(value)
    if not match:return str(new_primary or '')
    tail=value[match.start():].lstrip()
    first=str(new_primary or '')
    return (first+' '+tail).strip() if first else tail


def append_primary(text,addition):
    """Append text to RMKS1 without moving it behind RMKS2."""
    first=primary(text);addition=str(addition or '')
    new=first+(' ' if first and addition and not first[-1].isspace() else '')+addition
    return replace_primary(text,new)
