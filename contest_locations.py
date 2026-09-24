"""Declared event locations; text is an attestation, not coordinate evidence."""
import unicodedata

def location(value):
    if not isinstance(value,str):raise ValueError('運用地は文字列です。')
    s=unicodedata.normalize('NFKC',value).strip()
    if any(ord(c)<32 or c in '<>' for c in s):raise ValueError('運用地に制御文字等は使用できません。')
    return s

def validate(spec):
    from contest_rules import keys
    import re
    keys(spec,('groups','matches'),'部門別運用地')
    if not isinstance(spec['groups'],dict) or not 1<=len(spec['groups'])<=20:raise ValueError('運用地グループが不正です。')
    for k,v in spec['groups'].items():
        if not isinstance(k,str) or not re.fullmatch('[a-z_]+',k) or not location(v):raise ValueError('運用地グループ名が不正です。')
    if not isinstance(spec['matches'],dict):raise ValueError('運用地一致条件が不正です。')
    for k,values in spec['matches'].items():
        if k not in spec['groups'] or not isinstance(values,list) or not values or k in values or len(values)!=len(set(values)) or not set(values)<=set(spec['groups']):raise ValueError('運用地の参照先が不正です。')

def check(event,category,ctx):
    spec=event.get('operating_locations');group=category.get('location_group')
    if not spec or not group:return ''
    values=ctx.get('operating_locations',{})
    if not isinstance(values,dict):raise ValueError('部門別の運用地を入力してください。')
    selected=location(values.get(group,''))
    if not selected:raise ValueError(spec['groups'][group]+'の具体的な運用地を入力してください。')
    if group in spec['matches'] and selected not in [location(values.get(x,'')) for x in spec['matches'][group]]:raise ValueError('デジタルの運用地は電信・電話のいずれかと一致させてください。')
    return selected
