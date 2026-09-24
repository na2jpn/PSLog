"""Explicit per-event aliases on working copies, never on PSLog originals."""

def validate(spec):
    from contest_rules import keys
    keys(spec,('bands','modes','mode_families'),'大会別表記')
    for field in ('bands','modes','mode_families'):
        values=spec[field]
        if not isinstance(values,dict) or len(values)>1000:raise ValueError('大会別表記は対応表で指定してください。')
        for source,target in values.items():
            if not isinstance(source,str) or not source or source!=source.strip().upper() or any(c.isspace() or ord(c)<32 for c in source):raise ValueError('別名は空白なしの大文字で指定してください。')
            if not isinstance(target,str) or not target or any(c.isspace() or ord(c)<32 for c in target):raise ValueError('変換先表記が不正です。')
            if field=='mode_families':
                if target not in ('phone','cw','digital'):raise ValueError('モード分類が不正です。')
            elif target!=target.upper():raise ValueError('変換先は大文字で指定してください。')
            elif target in values and values[target]!=target:raise ValueError('別名の連鎖・循環は指定できません。')

def values(event,band,mode):
    spec=event.get('normalization',{})
    # Matching is exact after case/edge-space normalization: 10G is never
    # guessed to mean 10.1G or 10.4G, and DV is not inferred from FreeDV.
    b=str(band).strip().upper();m=str(mode).strip().upper()
    return spec.get('bands',{}).get(b,b),spec.get('modes',{}).get(m,m)

def mode_family(event,mode):
    from contest_rules import family
    return event.get('normalization',{}).get('mode_families',{}).get(mode,family(mode))

def validate_choices(event):
    from contest_event import lists
    choices=event['band_choices'];bands={b for w in event['windows'] for b in w['bands']}
    if not isinstance(choices,dict) or not 1<=len(choices)<=50:raise ValueError('曖昧なバンドの選択肢は対応表で指定してください。')
    for source,targets in choices.items():
        if not isinstance(source,str) or not source or source!=source.strip().upper() or any(c.isspace() for c in source):raise ValueError('曖昧なバンドの表記が不正です。')
        lists(targets,'実バンド選択肢')
        if len(targets)<2 or not set(targets)<=bands or source in targets:raise ValueError('実バンド選択肢は大会対象の異なる2バンド以上で指定してください。')

def working_values(event,band,mode,chosen=''):
    b,m=values(event,band,mode);choices=event.get('band_choices',{})
    if not choices:return b,m  # Other contests retain their own normalization.
    if not isinstance(chosen,str):raise ValueError('提出用バンドの指定が不正です。')
    chosen=chosen.strip().upper()
    if b in choices:
        if chosen not in choices[b]:raise ValueError(b+'は実バンドを区別できません。交信情報補完で '+ ' / '.join(choices[b])+' MHzから指定してください。')
        return chosen,m
    if chosen and chosen!=b:raise ValueError('元の確定バンドと提出用バンドの指定が一致しません。')
    return b,m
