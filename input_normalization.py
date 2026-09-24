"""Human-friendly normalization for amateur-radio entry fields.

Free-text Japanese fields are intentionally not handled here.  These helpers are
for fields whose stored representation is machine-oriented (date/time/callsign,
band/mode/RST, contest tokens, etc.).
"""
from __future__ import annotations

from datetime import datetime
import re
import unicodedata


def nfkc(value) -> str:
    return unicodedata.normalize('NFKC', str(value or ''))


def machine_text(value, *, upper: bool = False) -> str:
    """Normalize full-width ASCII forms while preserving ordinary Japanese text."""
    text = nfkc(value).strip()
    # NFKC covers full-width +/-/:/digits/letters.  Also accept the common
    # mathematical minus sign often produced by copy/paste.
    text = text.replace('\u2212', '-')
    return text.upper() if upper else text


def callsign(value) -> str:
    return machine_text(value, upper=True)


def amateur_callsign_entry(value) -> str:
    """Normalize and filter an amateur-radio callsign entry field.

    The visible entry accepts only ASCII letters, digits and ``/``.  Full-width
    ASCII forms are normalized first, letters are upper-cased, and unsupported
    characters (including Japanese text) are discarded.
    """
    text=nfkc(value).upper()
    return ''.join(ch for ch in text if ('A' <= ch <= 'Z') or ('0' <= ch <= '9') or ch == '/')


def date_text(value) -> str:
    """Return YYYY-MM-DD from common human date spellings.

    Accepted examples: 20260909, 2026/09/09, 2026/9/9, 2026-9-9,
    2026年9月9日 and their full-width ASCII equivalents.
    """
    text = machine_text(value)
    match = re.fullmatch(r'(\d{4})(\d{2})(\d{2})', text)
    if not match:
        match = re.fullmatch(r'(\d{4})\s*[-/.]\s*(\d{1,2})\s*[-/.]\s*(\d{1,2})', text)
    if not match:
        match = re.fullmatch(r'(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日?', text)
    if not match:
        raise ValueError('DATEは20260909、2026/9/9、2026年9月9日などで入力してください。')
    year, month, day = map(int, match.groups())
    try:
        parsed = datetime(year, month, day)
    except ValueError as exc:
        raise ValueError('DATEに実在する日付を入力してください。') from exc
    return parsed.strftime('%Y-%m-%d')


def time_text(value) -> str:
    """Return HH:MM from common human time spellings.

    Pure digits are accepted only for 3 or 4 digits: 915 -> 09:15,
    1515 -> 15:15.  A 1-2 digit number is deliberately not guessed.  With an
    explicit separator, one-digit hour/minute forms such as 1:1 are accepted.
    """
    text = machine_text(value)
    hour = minute = None
    match = re.fullmatch(r'(\d{1,2})\s*:\s*(\d{1,2})', text)
    if match:
        hour, minute = map(int, match.groups())
    else:
        match = re.fullmatch(r'(\d{1,2})\s*時\s*(\d{1,2})\s*分?', text)
        if match:
            hour, minute = map(int, match.groups())
        elif re.fullmatch(r'\d{3,4}', text):
            hour, minute = int(text[:-2]), int(text[-2:])
    if hour is None:
        raise ValueError('TIMEは1515、915、15:15、1:1、15時15分などで入力してください。')
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError('TIMEは00:00～23:59で入力してください。')
    return f'{hour:02d}:{minute:02d}'


def jccjcg_code(value) -> str:
    """Normalize a JCC/JCG field to the stored code only.

    Historical/user input such as ``JCC 100101`` or ``ＪＣＧ 12345ａ`` is
    accepted.  The stored form is ``100101`` / ``12345A``.  A five-digit
    JCG may optionally carry one trailing alphabetic supplemental marker; the
    marker is preserved and upper-cased.  Unknown non-empty values are left
    as normalized machine text rather than guessed or discarded.
    """
    text = machine_text(value, upper=True)
    text = re.sub(r'^(?:JCC|JCG)\s*[:：-]?\s*', '', text, count=1)
    compact = re.sub(r'\s+', '', text)
    if re.fullmatch(r'\d{4}|\d{6}|\d{5}[A-Z]?', compact):
        return compact
    return text


def jccjcg_parts(value):
    """Return ``(kind, code)`` while accepting both old and new forms.

    Kind is inferred from the numeric code when no explicit JCC/JCG prefix is
    present: 4/6 digits are JCC, 5 digits (optionally plus a supplemental
    letter) are JCG.
    """
    raw = machine_text(value, upper=True)
    explicit = ''
    match = re.match(r'^(JCC|JCG)\s*[:：-]?\s*', raw)
    if match:
        explicit = match.group(1)
    code = jccjcg_code(raw)
    if re.fullmatch(r'\d{5}[A-Z]?', code):
        inferred = 'JCG'
    elif re.fullmatch(r'(?:\d{4}|\d{6})', code):
        inferred = 'JCC'
    else:
        return explicit, code
    return explicit or inferred, code
