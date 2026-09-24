"""Regional exchanges with per-contact qualification suffixes on working data."""
import re
from datetime import datetime

def validate(spec):
    from contest_rules import keys,number
    keys(spec,('kind','codes','local_codes','same_sent_region','tag_points','operator_tag','special_tag','special_calls','young_below','reference_date'),'地域番号の付加文字')
    from contest_jarl import validate_exchange
    validate_exchange(dict(kind='numbered_region',codes=spec['codes'],same_sent_region=spec['same_sent_region']))
    local=spec['local_codes']
    if not isinstance(local,list) or not local or len(local)!=len(set(local)) or not set(local)<=set(spec['codes']):raise ValueError('付加文字の地域が不正です。')
    tags=spec['tag_points']
    if not isinstance(tags,dict) or not tags or any(not isinstance(k,str) or not re.fullmatch('[A-Z]',k) for k in tags):raise ValueError('付加文字は英字1文字です。')
    for value in tags.values():number(value,'付加文字の得点')
    if spec['operator_tag']==spec['special_tag'] or set(tags)!={spec['operator_tag'],spec['special_tag']}:raise ValueError('付加文字の用途を区別してください。')
    calls=spec['special_calls']
    if not isinstance(calls,dict) or not calls:raise ValueError('年度指定局が必要です。')
    for call,codes in calls.items():
        if not isinstance(call,str) or not re.fullmatch('[A-Z0-9]+',call) or not isinstance(codes,list) or not codes or len(codes)!=len(set(codes)) or not set(codes)<=set(local):raise ValueError('指定局のコール・運用地域が不正です。')
    if type(spec['young_below']) is not int or not 1<=spec['young_below']<=150:raise ValueError('年齢上限が不正です。')
    date(spec['reference_date'])

def date(value):
    if not isinstance(value,str) or not re.fullmatch('[0-9]{4}-[0-9]{2}-[0-9]{2}',value):raise ValueError('生年月日・基準日はYYYY-MM-DDで入力してください。')
    return datetime.strptime(value,'%Y-%m-%d').date()

def age_at(birth,reference):
    born=date(birth);today=date(reference)
    if born>today:raise ValueError('生年月日が運用日より後です。')
    return today.year-born.year-((today.month,today.day)<(born.month,born.day))

def base_call(value):
    value=str(value or '').strip().upper()
    # Only a conventional terminal portable suffix, never arbitrary substring.
    return re.sub(r'/(?:[0-9]|P|JD1)$','',value)

def decode(spec,value,label):
    m=re.fullmatch(r'([0-9]{2,6})([A-Z]?)',str(value or '').strip().upper())
    if not m or m[1] not in spec['codes'] or m[2] and m[2] not in spec['tag_points']:raise ValueError(label+'の地域番号・付加文字を確認してください。')
    return m[1],m[2]

def prepare(spec,v):
    area,tag=decode(spec,v.get('exchange'),'受信番号');sent,stag=decode(spec,v.get('sent'),'送信番号')
    if v.get('area') and str(v['area']).strip()!=area:raise ValueError('補助地域と受信番号が一致しません。')
    v.update(area=area,_received_tag=tag,_sent_region=sent,_sent_tag=stag)

def validate_operator(spec,v):
    name=v.get('operator_name','')
    if not isinstance(name,str) or not name.strip() or any(ord(c)<32 or c in '<>' for c in name):raise ValueError('Y送信行の実運用者のコール・氏名を入力してください。')
    if v.get('operator_yl') is True:return
    if not 0<=age_at(v.get('operator_birthdate'),spec['reference_date'])<spec['young_below']:raise ValueError('Y送信行はYL又は規約年齢未満の実運用者である必要があります。')

def check_sent(spec,v):
    tag=v['_sent_tag'];area=v['_sent_region']
    if tag and area not in spec['local_codes']:raise ValueError('府外の送信番号にはY/Xを付けられません。')
    if base_call(v.get('own')) in spec['special_calls'] and tag!=spec['special_tag']:raise ValueError('年度指定局の送信番号にはXが必要です。')
    if tag==spec['special_tag'] and area not in spec['special_calls'].get(base_call(v.get('own')),[]):raise ValueError('X送信番号と自局の年度指定局・運用地域が一致しません。')
    if tag==spec['operator_tag']:validate_operator(spec,v)

def points(spec,v):
    tag=v['_received_tag'];area=v['area']
    if tag and area not in spec['local_codes']:raise ValueError('府外の受信番号にY/Xがあります。交換記録を確認してください。')
    if base_call(v.get('call')) in spec['special_calls'] and tag!=spec['special_tag']:raise ValueError('年度指定局の受信番号にXがありません。交換記録を確認してください。')
    if tag==spec['special_tag'] and area not in spec['special_calls'].get(base_call(v.get('call')),[]):raise ValueError('X受信番号と年度指定局・運用地域が一致しません。')
    if tag:v['_computed_points']=spec['tag_points'][tag]

def submission_comments(spec,rows,info):
    from contest_export import clean
    extra=[]
    for row in rows:
        if row.get('_sent_tag')!=spec['operator_tag']:continue
        name=clean(row['operator_name'],'運用者',True)
        detail='性別: 女性（YL）' if row.get('operator_yl') is True else '生年月日: '+row['operator_birthdate']
        text=name+' / '+detail
        if text not in extra:extra.append(text)
    if not extra:return info
    result=dict(info);result['comments']=' '.join(x for x in (info.get('comments','').strip(),'Y送信の実運用者: '+'; '.join(extra)) if x);return result
