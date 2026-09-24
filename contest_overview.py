"""Read-only contest overview derived only from registered rule data.

The overview deliberately does not invent missing regulation facts.  It uses the
structured rule fields first and falls back to the rule's own submission notes
for short, explicitly stated items such as a deadline or portable-operation
note.
"""
from __future__ import annotations

from datetime import datetime
import re


def _ordered(values):
    out=[]
    for value in values:
        text=str(value).strip()
        if text and text not in out:out.append(text)
    return out


def _format_stamp(value, zone):
    try:dt=datetime.strptime(str(value),'%Y-%m-%d %H:%M')
    except (TypeError,ValueError):return str(value or '')
    return dt.strftime('%Y-%m-%d %H:%M')+' '+zone


def _deadline(instructions, year):
    text=str(instructions or '')
    patterns=[
        # 締切2026-10-06 / 締切 2026/10/06 23:59
        r'締切\s*([12]\d{3})[-/]([01]?\d)[-/]([0-3]?\d)(?:\s*([0-2]?\d):([0-5]\d))?',
        # 2026-10-06締切 / 2026-10-06 23:59まで
        r'([12]\d{3})[-/]([01]?\d)[-/]([0-3]?\d)(?:\s*([0-2]?\d):([0-5]\d))?\s*(?:締切|まで)',
        # 締切5月3日23:59
        r'締切\s*([01]?\d)月([0-3]?\d)日(?:\s*([0-2]?\d):([0-5]\d))?',
        # 5月3日23:59締切 / 7月8日必着 / 9月16日消印有効
        r'([01]?\d)月([0-3]?\d)日(?:\s*([0-2]?\d):([0-5]\d))?\s*(?:締切|必着|消印有効|まで)',
    ]
    for i,pattern in enumerate(patterns):
        m=re.search(pattern,text)
        if not m:continue
        g=m.groups()
        if i<2:y,mo,day,hh,mm=g
        else:y=str(year);mo,day,hh,mm=g
        try:
            dt=datetime(int(y),int(mo),int(day),int(hh or 0),int(mm or 0))
        except ValueError:continue
        return dt.strftime('%Y-%m-%d') + (dt.strftime(' %H:%M') if hh is not None else '')
    return ''


def _bands(event):
    values=[]
    for window in event.get('windows',[]):values.extend(window.get('bands',[]))
    if not values:
        for c in event.get('categories',[]):values.extend(c.get('bands',[]))
    return _ordered(values)


def _modes(event):
    values=[]
    for modes in event.get('band_modes',{}).values():values.extend(modes)
    if not values:
        for c in event.get('categories',[]):values.extend(c.get('modes',[]))
    values=_ordered(values)
    return ['全モード（規約データ上）'] if '*' in values else values


def _multiband(event):
    cats=[]
    for c in event.get('categories',[]):
        bands=_ordered(c.get('bands',[]))
        if len(bands)>1 and int(c.get('max_bands',len(bands)) or 0)>1:
            cats.append(str(c.get('name') or c.get('id') or '').strip())
    cats=_ordered(cats)
    if not cats:return 'なし（登録部門上）'
    example=' / '.join(cats[:4])
    return f'あり（{len(cats)}部門）'+(f'：{example}'+(' ほか' if len(cats)>4 else '') if example else '')


def _region_hint(event):
    names='\n'.join(str(c.get('name','')) for c in event.get('categories',[]))
    labels=[]
    for token,label in [('県内','県内局'),('県外','県外局'),('管内','管内局'),('管外','管外局'),('都内','都内局'),('都外','都外局'),('市内','市内局'),('市外','市外局'),('国内','国内局'),('海外','海外局'),('DX','海外/DX局')]:
        if token in names and label not in labels:labels.append(label)
    return ' / '.join(labels) if labels else '登録なし'


def _station_types(event):
    entrant=event.get('entrant',{}) or {}
    values=entrant.get('station_types',[]) or []
    if not values:return '登録なし'
    names={'individual':'個人局','club':'社団局','special':'特別局・特別記念局'}
    check=set(entrant.get('checklog_only_types',[]) or [])
    out=[]
    for value in values:
        text=names.get(value,str(value))
        if value in check:text+='（チェックログのみ）'
        out.append(text)
    guest={'allowed':'ゲストOP可','forbidden':'ゲストOP不可','mo_only':'ゲストOPはマルチOPのみ'}.get(entrant.get('guest_policy'))
    if guest:out.append(guest)
    return ' / '.join(out)


def _power(event, instructions):
    # Human-facing rule_view is authoritative for a contest's broad power
    # restriction wording.  Do not collapse category-specific limits (for
    # example QRP classes) into a misleading list of wattages.
    view_power=str((event.get('rule_view') or {}).get('power','')).strip()
    if view_power:return view_power
    values=[]
    for c in event.get('categories',[]):
        if c.get('max_power') not in (None,''):values.append(float(c['max_power']))
        for value in (c.get('power_by_band',{}) or {}).values():
            if value not in (None,''):values.append(float(value))
    pbo=event.get('power_by_operation',{}) or {}
    def walk(obj):
        if isinstance(obj,dict):
            for k,v in obj.items():
                if isinstance(v,(dict,list)):walk(v)
                elif isinstance(v,(int,float)) and ('power' in str(k).lower() or str(k).lower() in ('max','watts','w')):values.append(float(v))
        elif isinstance(obj,list):
            for v in obj:walk(v)
    walk(pbo)
    for m in re.finditer(r'(?<!\d)(\d+(?:\.\d+)?)\s*W(?:以下)?',str(instructions or ''),re.I):
        try:values.append(float(m.group(1)))
        except ValueError:pass
    clean=sorted(set(values))
    if not clean:
        if re.search(r'(?:送信出力|空中線電力|出力).{0,12}(?:制限なし|制限無し)',str(instructions or '')):
            return '制限なし'
        return '登録なし'
    labels=[(str(int(v)) if v.is_integer() else str(v))+' W' for v in clean]
    return '明示された上限・出力値: '+' / '.join(labels)+('（部門・バンド等により異なる）' if len(labels)>1 else '')


def _humanize_portable_sentence(sentence):
    """Make internal confirmation-style portable-operation notes readable.

    This is display-only wording cleanup; it does not broaden or narrow the
    registered contest rule.
    """
    text=str(sentence or '').strip()
    text=text.replace('SO移動の例外以外は場所を変更していない',
                      'シングルオペの移動運用として規約で認められる場合を除き、コンテスト中に運用場所を変更していません')
    text=text.replace('SO移動例外以外の場所変更はない',
                      'シングルオペの移動運用として規約で認められる場合を除き、コンテスト中に運用場所を変更していません')
    text=text.replace('SO移動例外', 'シングルオペの移動運用として規約で認められる例外')
    text=text.replace('移動SOの許可範囲', 'シングルオペの移動運用で認められた範囲')
    text=re.sub(r'運用場所を変更していない、又はシングルオペの移動運用で認められた範囲（([^）]+)）のみで変更した',
                r'コンテスト中は運用場所を変更していません。移動運用するシングルオペの場合は、規約で認められた範囲（\1）内のみで移動しています',text)
    return text


def _portable(event, instructions):
    texts=[]
    texts.extend(event.get('required_flags',[]) or [])
    for c in event.get('categories',[]):texts.extend(c.get('required_flags',[]) or [])
    texts.append(str(instructions or ''))
    snippets=[]
    for raw in texts:
        for sentence in re.split(r'[。\n]+',str(raw)):
            sentence=_humanize_portable_sentence(sentence.strip())
            if '移動' in sentence and sentence not in snippets:snippets.append(sentence)
    if not snippets:return '登録なし'
    text=' ／ '.join(snippets[:2])
    if len(snippets)>2:text+=' ほか'
    return text


def _timing(event):
    rows=[]
    for c in event.get('categories',[]):
        timing=c.get('timing') or {}
        band=timing.get('band_change')
        if band:
            if band.get('kind')=='stay':rule=f'バンド変更後 {band.get("min_minutes")}分間の滞在'
            else:rule=f'1時間あたりのバンド変更 {band.get("max_changes")}回まで'
            rows.append((str(c.get('name') or c.get('id')),rule))
        operating=timing.get('operating')
        if operating:rows.append((str(c.get('name') or c.get('id')),f'運用時間上限 {operating.get("max_minutes")}分 / 休止 {operating.get("min_off_minutes")}分'))
    if not rows:return '登録なし',False
    grouped=[]
    for name,rule in rows:
        hit=next((x for x in grouped if x[0]==rule),None)
        if hit:hit[1].append(name)
        else:grouped.append([rule,[name]])
    parts=[]
    for rule,names in grouped:
        parts.append(rule+'（対象: '+' / '.join(names[:4])+(' ほか' if len(names)>4 else '')+'）')
    return 'あり：'+' ／ '.join(parts),True


def _exchange(event, instructions):
    spec=event.get('exchange') or {};kind=spec.get('kind')
    mapping={
        'jarl_region_power':'RS(T) + 都府県支庁ナンバー + 空中線電力記号',
        'jarl_band_power':'RS(T) + 規約指定地域コード + 空中線電力記号（バンド別）',
        'numbered_region':'RS(T) + 規約指定地域コード',
        'literal_region':'RS(T) + 規約指定地域コード',
        'tagged_region':'RS(T) + 地域コード + 規約指定タグ',
        'postal_region':'RS(T) + 規約指定の郵便番号系地域コード',
    }
    if kind in mapping:return mapping[kind]
    text=str(instructions or '')
    if 'GLのみ交換' in text or 'グリッドロケーター' in text:return 'GL（グリッドロケーター。登録済み提出案内による）'
    return '登録なし'


def overview_rows(rule):
    """Return ``[(label, text, important), ...]`` for the selected rule."""
    if not rule:return []
    event=rule.get('event',{}) or {};submission=event.get('submission',{}) or {};instructions=str(submission.get('instructions','') or '')
    zone=str(event.get('timezone','JST'))
    windows=event.get('windows',[]) or []
    window_text=' ／ '.join(_format_stamp(w.get('start'),zone)+' ～ '+_format_stamp(w.get('end'),zone) for w in windows) if windows else '登録なし'
    deadline=_deadline(instructions,rule.get('year')) or '登録なし（提出案内・公式規約を確認）'
    bands=_bands(event);modes=_modes(event)
    timing,timing_important=_timing(event)
    region=_region_hint(event);station_types=_station_types(event)
    participant=('登録なし' if region=='登録なし' and station_types=='登録なし' else f'地域区分：{region} ／ 局種：{station_types}')
    notes=instructions.strip() or '特記事項の登録なし'
    return [
        ('主催',str(rule.get('organizer') or '主催の登録なし'),False),
        ('開催日時',window_text,False),
        ('提出締切',deadline,False),
        ('対象バンド',' / '.join(bands) if bands else '登録なし',False),
        ('対象モード',' / '.join(modes) if modes else '登録なし',False),
        ('マルチバンド／オールバンド部門',_multiband(event),False),
        ('参加できる局',participant,False),
        ('送信出力',_power(event,instructions),bool(re.search(r'\d+(?:\.\d+)?\s*W',_power(event,instructions)))),
        ('移動運用',_portable(event,instructions),False),
        ('10分間ルール・時間制限',timing,timing_important),
        ('ナンバー交換',_exchange(event,instructions),False),
        ('特記事項',notes,notes!='特記事項の登録なし'),
    ]
