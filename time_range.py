"""Shared partial JST date/time range parsing.

User-facing range fields may contain a leading prefix of YYYYMMDDhhmmss.
The start side expands to the beginning of that period; the end side expands
to its end.  Callers can cap precision (for example at minute precision) while
all comparisons use a 14-digit seconds boundary internally.
"""
from __future__ import annotations

from datetime import datetime
import calendar
import re
import unicodedata


def normalize_prefix(value):
    return unicodedata.normalize('NFKC', str(value or '')).strip()


def _validate_complete_components(value):
    """Validate every complete calendar/time component present in *value*.

    Odd-length prefixes are retained for compatibility with LogSearch.  Only
    components that are fully present are validated; their final partial digit
    remains a lexical prefix by design.
    """
    if len(value) >= 4:
        year=int(value[:4])
        if not 1 <= year <= 9999:
            raise ValueError('年が正しくありません。')
    if len(value) >= 6:
        month=int(value[4:6])
        if not 1 <= month <= 12:
            raise ValueError('月が正しくありません。')
    if len(value) >= 8:
        try:datetime.strptime(value[:8],'%Y%m%d')
        except ValueError as e:raise ValueError('日付が正しくありません。') from e
    if len(value) >= 10:
        hour=int(value[8:10])
        if not 0 <= hour <= 23:
            raise ValueError('時が正しくありません。')
    if len(value) >= 12:
        minute=int(value[10:12])
        if not 0 <= minute <= 59:
            raise ValueError('分が正しくありません。')
    if len(value) >= 14:
        second=int(value[12:14])
        if not 0 <= second <= 59:
            raise ValueError('秒が正しくありません。')


def prefix_boundary(value, upper=False, max_digits=14):
    """Return a 14-digit comparison boundary for a date/time prefix.

    Examples::

        prefix_boundary('20260915', False) == '20260915000000'
        prefix_boundary('20260917', True)  == '20260917235959'

    Empty input returns ``''`` and means unbounded.  Even-length prefixes use
    real calendar period ends (including leap-year month lengths).  Odd-length
    prefixes are supported for compatibility and use lexical 0/9 padding.
    """
    value=normalize_prefix(value)
    if not value:return ''
    if type(max_digits) is not int or not 1 <= max_digits <= 14:
        raise ValueError('日時入力上限が不正です。')
    if not re.fullmatch(r'[0-9]{1,%d}'%max_digits,value):
        raise ValueError(f'日時はYYYYMMDDhhmmssの先頭から最大{max_digits}桁で入力してください。')
    _validate_complete_components(value)

    n=len(value)
    if n==4:
        return value+('1231235959' if upper else '0101000000')
    if n==6:
        if upper:
            year=int(value[:4]);month=int(value[4:6]);last=calendar.monthrange(year,month)[1]
            return value+f'{last:02d}235959'
        return value+'01000000'
    if n==8:return value+('235959' if upper else '000000')
    if n==10:return value+('5959' if upper else '0000')
    if n==12:return value+('59' if upper else '00')
    if n==14:return value
    return value.ljust(14,'9' if upper else '0')


def boundary_datetime(value, upper=False, max_digits=14):
    text=prefix_boundary(value,upper,max_digits)
    return datetime.strptime(text,'%Y%m%d%H%M%S') if text else None


def range_boundaries(start='',end='',max_digits=14):
    lo=prefix_boundary(start,False,max_digits);hi=prefix_boundary(end,True,max_digits)
    if lo and hi and lo>hi:raise ValueError('開始日時は終了日時以前にしてください。')
    return lo,hi


def help_text(max_digits=14):
    example='YYYYMMDDhhmmss'[:max_digits]
    return f'{example}・先頭だけでも可（空欄は制限なし）'
