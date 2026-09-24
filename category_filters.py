"""Generic contest-category facets used by the category picker.

The facets are convenience hints only.  They never replace the original
category list, id or submission code: unclassified/irregular categories remain
available under ``その他／未分類`` and the all-items view always contains every
source category exactly once.
"""
from __future__ import annotations

import re
import unicodedata

PHONE_MODES={'SSB','AM','FM','DV','DSTAR','DMR','FREEDV','C4FM'}
DIGITAL_MODES={'RTTY','FT8','FT4','FT2','PSK31','PSK','JT65','JT9','MFSK','PACKET','DIGITAL'}


def _text(value):
    return unicodedata.normalize('NFKC',str(value or '')).strip()


def _upper(value):
    return _text(value).upper()


def _region(category):
    name=_text(category.get('name',''))
    for token,label in (
        ('県内','県内'),('県外','県外'),('管内','管内'),('管外','管外'),
        ('市内','市内'),('市外','市外'),('国内','国内'),('海外','海外'),('DX','海外/DX')):
        if token in name.upper() if token=='DX' else token in name:
            return label
    ident=_upper(category.get('id',''))
    # Common JARL regional category prefixes.  This is display-only and falls
    # back harmlessly when a contest uses different conventions.
    if ident.startswith(('I-','IN','LOCAL')):return '地域内'
    if ident.startswith(('O-','OUT')):return '地域外'
    return 'その他／未分類'


def _operation(category):
    hay=_upper(category.get('name',''))+' '+_upper(category.get('id',''))
    if re.search(r'(^|[^A-Z])SO([^A-Z]|$)',hay) or 'シングルオペ' in hay or 'SINGLE OP' in hay:
        return 'シングルオペ'
    if re.search(r'(^|[^A-Z])MO([^A-Z]|$)',hay) or 'マルチオペ' in hay or 'MULTI OP' in hay:
        return 'マルチオペ'
    return 'その他／未分類'


def _mode(category):
    modes={_upper(v) for v in category.get('modes',[]) if _text(v)}
    hay=_upper(category.get('name',''))+' '+_upper(category.get('id',''))
    if 'RTTY' in hay or modes=={'RTTY'}:return 'RTTY'
    if modes=={'CW'} or '電信' in hay and '電話' not in hay:return '電信'
    if modes and modes.issubset(PHONE_MODES):return '電話'
    if modes and modes.issubset(DIGITAL_MODES):return 'デジタル'
    if len(modes)>1 or 'MIX' in hay or 'MIXED' in hay:return 'MIX／複合'
    return 'その他／未分類'


def _power(category):
    hay=_upper(category.get('name',''))+' '+_upper(category.get('id',''))
    if 'QRP' in hay:return 'QRP'
    value=category.get('max_power')
    try:
        if value is not None and float(value)<=5:return 'QRP'
    except (TypeError,ValueError):
        pass
    return '通常／その他'


def _band(category):
    bands=[_text(v) for v in category.get('bands',[]) if _text(v) and _text(v)!='*']
    if len(bands)==1:return bands[0]+' MHz'
    hay=_upper(category.get('name',''))
    if len(bands)>1 and ('オール' in hay or 'ALL' in hay):return 'オールバンド'
    if len(bands)>1:return '複数バンド'
    return 'その他／未分類'


def category_facets(category):
    """Return safe, display-only facets for one untouched category dict."""
    return {
        'region':_region(category),
        'operation':_operation(category),
        'mode':_mode(category),
        'power':_power(category),
        'band':_band(category),
    }


def classify_categories(categories):
    """Return one entry per source category, preserving order/id/name/code."""
    out=[]
    for category in categories:
        out.append({
            'id':category.get('id',''),
            'name':category.get('name',''),
            'submission_code':category.get('submission_code',category.get('id','')),
            'facets':category_facets(category),
            'source':category,
        })
    return out


def category_compatible(category,station_type='',power=None):
    """Return whether entered station/power conditions can use this category.

    Empty/zero inputs mean "not specified yet" and therefore do not filter.
    This is intentionally limited to explicit category metadata; it does not
    guess eligibility from category names.
    """
    if station_type and category.get('station_types') and station_type not in category['station_types']:
        return False
    try:p=float(power or 0)
    except (TypeError,ValueError):p=0
    if p>0:
        cap=category.get('max_power')
        if cap is not None and p>float(cap):return False
        low=category.get('min_power_exclusive')
        if low is not None and p<=float(low):return False
    return True
