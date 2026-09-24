"""Pure session/tab state helpers for PSLog 1.03.

This module deliberately has no Qt dependency so session restoration and limits can
be regression-tested on Linux even when PySide6 is unavailable.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import re
from input_normalization import machine_text
import uuid

MAX_STANDARD = 5
MAX_EASY = 2
MAX_FREE = 4
MAX_CONTEST = 6
MAX_TOTAL = MAX_STANDARD + MAX_EASY + MAX_FREE + MAX_CONTEST
RECENT_LIMIT = 20

CONTEST_PALETTE = (
    {'name':'blue',      'light':'#DDEEFF', 'selected':'#C9E1FA', 'dark':'#145A9C'},
    {'name':'vermilion', 'light':'#FFE3DA', 'selected':'#FFD2C4', 'dark':'#A63B20'},
    {'name':'purple',    'light':'#EEE2FA', 'selected':'#E1D0F3', 'dark':'#70439A'},
    {'name':'brown',     'light':'#F2E6DC', 'selected':'#E7D5C6', 'dark':'#79513B'},
    {'name':'turquoise', 'light':'#D9F3F1', 'selected':'#C5E9E6', 'dark':'#147C78'},
    {'name':'pink',      'light':'#FCE1EE', 'selected':'#F5CCE0', 'dark':'#A23E72'},
)


def _id():
    return uuid.uuid4().hex


def clean_contest_name(value):
    value=machine_text(value,upper=True)
    if not re.fullmatch(r'[A-Z0-9]+', value):
        raise ValueError('コンテスト英名は英数字だけで入力してください。')
    return value


def clean_event_ym(value):
    value=machine_text(value)
    if not re.fullmatch(r'\d{6}', value):
        raise ValueError('対象年月はYYYYMM（例: 202609）で入力してください。')
    month=int(value[4:])
    if not 1 <= month <= 12:
        raise ValueError('対象年月の月は01～12で入力してください。')
    return value


def contest_suffix(name, event_ym):
    return clean_contest_name(name) + clean_event_ym(event_ym)


def standard_title(call='', suffix=''):
    """Return the display title for an amateur-radio standard workspace.

    ``slot`` remains an internal workspace-management value and is deliberately
    not part of the visible title.  An unset callsign keeps a recognizable
    fallback while still identifying the radio service as amateur radio.
    """
    call=machine_text(call,upper=True).strip()
    if not call:
        return '[A]標準'
    suffix=str(suffix or '').strip()
    return f'[A]{call}' + (f'-{suffix}' if suffix else '')


def easy_title(call='', suffix=''):
    call=machine_text(call,upper=True).strip()
    if not call:
        return 'EASYタブ'
    # EASY has no separate log-file suffix UI.  Portable designators such as /1
    # are part of the callsign itself and therefore remain visible.
    return f'[E]{call}'


def free_title(call='', kind=''):
    call=str(call or '').strip()
    kind=str(kind or '').strip()
    if not call:return 'フリラタブ'
    return f'[F]{call}' + (f' {kind}' if kind else '')


def session_title(session):
    if session.get('type') == 'contest':
        return session.get('contest_name') or 'CONTEST'
    if session.get('type') == 'easy':
        return easy_title(session.get('call',''),session.get('suffix',''))
    if session.get('type') == 'free':
        return free_title(session.get('call',''),session.get('free_type',''))
    return standard_title(session.get('call',''),session.get('suffix',''))


def standard_session(slot, settings=None):
    settings=settings or {}
    return {
        'id':_id(), 'type':'standard', 'slot':int(slot),
        'call':machine_text(settings.get('own',''),upper=True),
        'suffix':str(settings.get('suffix','') or ''),
        'band':machine_text(settings.get('band','430') or '430'),
        'mode':machine_text(settings.get('mode','FM') or 'FM',upper=True),
        'my_qth':str(settings.get('my_qth','') or ''),
        'limited':bool(settings.get('standard_limited',False)),
        'rmks2_visible':bool(settings.get('rmks2_visible',False)),
    }


def easy_session(slot, settings=None):
    settings=settings or {}
    return {
        'id':_id(), 'type':'easy', 'slot':int(slot),
        'call':machine_text(settings.get('own',''),upper=True),
        'suffix':'',
        'band':machine_text(settings.get('band','430') or '430'),
        'mode':machine_text(settings.get('mode','FM') or 'FM',upper=True),
        'my_qth':str(settings.get('my_qth','') or ''),
        'limited':bool(settings.get('standard_limited',False)),
        'rmks2_visible':False,
    }



def free_session(slot, call='', free_type='DCR', model='', my_qth=''):
    return {
        'id':_id(), 'type':'free', 'slot':int(slot),
        'call':str(call or ''), 'free_type':str(free_type or 'DCR'),
        'model':str(model or ''), 'my_qth':str(my_qth or ''),
    }

def contest_session(name, event_ym, call='', band='7', mode='SSB', my_qth=''):
    return {
        'id':_id(), 'type':'contest',
        'call':machine_text(call,upper=True),
        'contest_name':clean_contest_name(name),
        'event_ym':clean_event_ym(event_ym),
        'band':machine_text(band or '7'), 'mode':machine_text(mode or 'SSB',upper=True),
        'my_qth':str(my_qth or ''), 'limited':True,
    }


def counts(sessions):
    standard=sum(1 for s in sessions if s.get('type')=='standard')
    contest=sum(1 for s in sessions if s.get('type')=='contest')
    return standard,contest


def easy_count(sessions):
    return sum(1 for s in sessions if s.get('type')=='easy')

def free_count(sessions):
    return sum(1 for s in sessions if s.get('type')=='free')


def next_standard_slot(sessions):
    used={int(s.get('slot',0)) for s in sessions if s.get('type')=='standard' and str(s.get('slot','')).isdigit()}
    for slot in range(1,MAX_STANDARD+1):
        if slot not in used:return slot
    return None


def next_free_slot(sessions):
    used={int(s.get('slot',0)) for s in sessions if s.get('type')=='free' and str(s.get('slot','')).isdigit()}
    for slot in range(1,MAX_FREE+1):
        if slot not in used:return slot
    return None


def next_easy_slot(sessions):
    used={int(s.get('slot',0)) for s in sessions if s.get('type')=='easy' and str(s.get('slot','')).isdigit()}
    for slot in range(1,MAX_EASY+1):
        if slot not in used:return slot
    return None


def contest_colors(sessions):
    """Return session-id -> palette entry, keeping a tab's runtime color on moves.

    ``_tab_color_index`` is deliberately runtime-only; ``serializable`` does not
    persist it.  This means a drag reorders tabs without repainting each contest
    as a different color, while a fresh launch still assigns the palette from
    the restored order.
    """
    result={};used=set()
    for session in sessions:
        if session.get('type')!='contest':continue
        idx=session.get('_tab_color_index')
        if isinstance(idx,int) and 0<=idx<len(CONTEST_PALETTE) and idx not in used:
            used.add(idx);result[session['id']]=dict(CONTEST_PALETTE[idx])
    for session in sessions:
        if session.get('type')!='contest' or session['id'] in result:continue
        idx=next((i for i in range(len(CONTEST_PALETTE)) if i not in used),None)
        if idx is None:break
        session['_tab_color_index']=idx;used.add(idx);result[session['id']]=dict(CONTEST_PALETTE[idx])
    return result


def _text(value, default=''):
    return value if isinstance(value,str) else default


def _normal_standard(raw, slot, fallback):
    s=standard_session(slot,fallback)
    s['id']=_text(raw.get('id')) or _id()
    s['call']=_text(raw.get('call'),s['call']).strip().upper()
    s['suffix']=_text(raw.get('suffix'),s['suffix'])
    s['band']=_text(raw.get('band'),s['band'])
    s['mode']=_text(raw.get('mode'),s['mode'])
    s['my_qth']=_text(raw.get('my_qth'),s['my_qth'])
    s['limited']=bool(raw.get('limited',s['limited']))
    s['rmks2_visible']=bool(raw.get('rmks2_visible',s.get('rmks2_visible',False)))
    return s


def _normal_easy(raw, slot, fallback):
    s=easy_session(slot,fallback)
    s['id']=_text(raw.get('id')) or _id()
    s['call']=_text(raw.get('call'),s['call']).strip().upper()
    s['suffix']=''
    s['band']=_text(raw.get('band'),s['band'])
    s['mode']=_text(raw.get('mode'),s['mode'])
    s['my_qth']=_text(raw.get('my_qth'),s['my_qth'])
    s['limited']=bool(raw.get('limited',s['limited']))
    s['rmks2_visible']=False
    return s


def _normal_free(raw, slot):
    s=free_session(slot,raw.get('call',''),raw.get('free_type','DCR'),raw.get('model',''),raw.get('my_qth',''))
    s['id']=_text(raw.get('id')) or _id()
    return s


def _normal_contest(raw, fallback, now_ym):
    try:name=clean_contest_name(raw.get('contest_name',''))
    except ValueError:return None
    try:ym=clean_event_ym(raw.get('event_ym',now_ym))
    except ValueError:ym=now_ym
    s=contest_session(name,ym,
        _text(raw.get('call'),fallback.get('own','')),
        _text(raw.get('band'),fallback.get('band','7')),
        _text(raw.get('mode'),fallback.get('mode','SSB')),
        _text(raw.get('my_qth'),fallback.get('my_qth','')))
    s['id']=_text(raw.get('id')) or _id()
    s['limited']=bool(raw.get('limited',True))
    return s


def restore(settings, now=None):
    """Normalize saved workspace state, always returning at least one valid session."""
    settings=settings or {}
    now=now or datetime.now()
    now_ym=now.strftime('%Y%m')
    raw=settings.get('workspace_sessions')
    sessions=[];used_ids=set();used_slots=set();used_easy_slots=set();used_free_slots=set();std_count=easy_count_value=free_count_value=contest_count=0
    if isinstance(raw,list):
        for item in raw:
            if not isinstance(item,dict):continue
            kind=item.get('type')
            if kind=='standard' and std_count < MAX_STANDARD:
                slot=item.get('slot')
                try:slot=int(slot)
                except (TypeError,ValueError):slot=0
                if not 1 <= slot <= MAX_STANDARD or slot in used_slots:
                    slot=next((n for n in range(1,MAX_STANDARD+1) if n not in used_slots),None)
                if slot is None:continue
                s=_normal_standard(item,slot,settings);used_slots.add(slot);std_count+=1
            elif kind=='easy' and easy_count_value < MAX_EASY:
                slot=item.get('slot')
                try:slot=int(slot)
                except (TypeError,ValueError):slot=0
                if not 1 <= slot <= MAX_EASY or slot in used_easy_slots:
                    slot=next((n for n in range(1,MAX_EASY+1) if n not in used_easy_slots),None)
                if slot is None:continue
                s=_normal_easy(item,slot,settings);used_easy_slots.add(slot);easy_count_value+=1
            elif kind=='free' and free_count_value < MAX_FREE:
                slot=item.get('slot')
                try:slot=int(slot)
                except (TypeError,ValueError):slot=0
                if not 1 <= slot <= MAX_FREE or slot in used_free_slots:
                    slot=next((n for n in range(1,MAX_FREE+1) if n not in used_free_slots),None)
                if slot is None:continue
                s=_normal_free(item,slot);used_free_slots.add(slot);free_count_value+=1
            elif kind=='contest' and contest_count < MAX_CONTEST:
                s=_normal_contest(item,settings,now_ym)
                if s is None:continue
                contest_count+=1
            else:continue
            if s['id'] in used_ids:s['id']=_id()
            used_ids.add(s['id']);sessions.append(s)
            if len(sessions)>=MAX_TOTAL:break
    if not sessions:
        sessions=[standard_session(1,settings)]
    active_id=_text(settings.get('active_workspace_id'))
    active_index=next((i for i,s in enumerate(sessions) if s['id']==active_id),0)

    recent=[];recent_ids=set()
    raw_recent=settings.get('recent_workspace_sessions')
    if isinstance(raw_recent,list):
        for item in raw_recent[:RECENT_LIMIT]:
            if not isinstance(item,dict):continue
            if item.get('type')=='standard':
                slot=item.get('slot',1)
                try:slot=max(1,min(MAX_STANDARD,int(slot)))
                except (TypeError,ValueError):slot=1
                s=_normal_standard(item,slot,settings)
            elif item.get('type')=='easy':
                slot=item.get('slot',1)
                try:slot=max(1,min(MAX_EASY,int(slot)))
                except (TypeError,ValueError):slot=1
                s=_normal_easy(item,slot,settings)
            elif item.get('type')=='free':
                slot=item.get('slot',1)
                try:slot=max(1,min(MAX_FREE,int(slot)))
                except (TypeError,ValueError):slot=1
                s=_normal_free(item,slot)
            elif item.get('type')=='contest':
                s=_normal_contest(item,settings,now_ym)
                if s is None:continue
            else:continue
            if s['id'] in used_ids or s['id'] in recent_ids:continue
            recent_ids.add(s['id']);recent.append(s)
    return sessions,active_index,recent


def serializable(session):
    allowed=('id','type','slot','call','suffix','band','mode','my_qth','limited','rmks2_visible','contest_name','event_ym','free_type','model')
    return {k:deepcopy(session[k]) for k in allowed if k in session}


def recent_snapshot(session, fallback_call=''):
    """Return a durable recently-closed-tab snapshot, preserving its own call.

    Older/partially-written recent-tab records may lack ``call``.  Only in that
    case do we fall back to the configured primary amateur callsign; an explicit
    per-tab callsign is never replaced.
    """
    snapshot=serializable(session)
    call=machine_text(snapshot.get('call') or fallback_call,upper=True)
    if call:snapshot['call']=call
    return snapshot


def reopen_snapshot(session, fallback_call=''):
    """Copy a recently-closed tab for reopening without losing its own call."""
    candidate=deepcopy(session)
    call=machine_text(candidate.get('call') or fallback_call,upper=True)
    if call:candidate['call']=call
    return candidate
