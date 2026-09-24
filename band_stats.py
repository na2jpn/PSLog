"""Presentation helpers for contest band-count badges."""
from __future__ import annotations

from html import escape

BAND_COLORS={
    'lf_mf':'#D9C6A8',
    '1.8':'#D9B8CF',
    '3.5':'#E6B3B3',
    '7':'#F2C7D5',
    '10':'#F1E4B5',
    '14':'#CFE5C9',
    '18':'#CBE5DF',
    '21':'#CDE2EE',
    '24':'#D1DDF0',
    '28':'#DDD0EC',
    '50':'#E8CCE1',
    '144':'#CBE1DD',
    '430':'#CBDCED',
    '1200':'#DDD2E8',
    'shf':'#D2C9E8',
    'other':'#E6E6E6',
    'total':'#E7E7E7',
}

def color_for_band(value: str) -> str:
    text=str(value or '').strip()
    try:
        mhz=float(text)
    except ValueError:
        return BAND_COLORS['other']
    if mhz <= 0.475:
        return BAND_COLORS['lf_mf']
    if mhz in (1.8,1.9):
        return BAND_COLORS['1.8']
    if mhz >= 2400:
        return BAND_COLORS['shf']
    key=f'{mhz:g}'
    return BAND_COLORS.get(key,BAND_COLORS['other'])

def band_badge(value: str, count: int) -> str:
    label=f'{value} MHz {count}'
    return f'<span style="background-color:{color_for_band(value)}; color:#202020;">&nbsp;{escape(label)}&nbsp;</span>'

def total_badge(total: int) -> str:
    return f'<span style="background-color:{BAND_COLORS["total"]}; color:#202020; font-weight:600;">&nbsp;合計 {int(total)}&nbsp;</span>'
