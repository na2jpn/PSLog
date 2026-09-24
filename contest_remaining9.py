"""Submission-only processing for the next PSLOG101 checkpoint.

Original log columns and actual exchanged values remain unchanged.
"""


def prepare_row(event, category, row, context):
    profile = event.get('regional', {}).get('profile')
    if profile in ('nara','kyoto'):
        import re
        pattern='[1-5][1-9][1-9]' if row['mode']=='CW' else '[1-5][1-9]'
        if any(not re.fullmatch(pattern,str(row.get(k,''))) for k in ('rst_sent','rst_received')):raise ValueError('この大会は実交換RS(T)が必要です。')
    if profile == 'kyoto':return prepare_kyoto(event,category,row,context)
    if profile == 'nara':
        import re
        from contest_regional import base_call
        year=context.get('declarations',{}).get('call_license_year','')
        if not re.fullmatch('[0-9]{4}',year) or not 1952<=int(year)<=2026:raise ValueError('当該コールの最初の局免許年を1952～2026の西暦で確認してください。')
        if row['sent'][:2]!=year[-2:]:raise ValueError('送信した開局年と当該コールの初免許年が一致しません。事後に送信番号を書き換えないでください。')
        row['prefix']=base_call(row['call'])[-1]
    if profile == 'saitama':
        remote = str(row.get('remote_mode', '')).strip().upper()
        remote = {'USB': 'SSB', 'LSB': 'SSB', 'A2A': 'CW', 'F2A': 'CW'}.get(remote, remote)
        if remote not in ('CW', 'SSB', 'FM', 'AM'):
            raise ValueError('埼玉は相手の通信方式を交信情報で確認してください。クロスモードは電話として採点します。')
        both_cw = row['mode_family'] == 'cw' and remote == 'CW'
        row['mode_family'] = 'cw' if both_cw else 'phone'
        local = row.get('exchange') in event['regional']['local_a']
        row['_computed_points'] = (2 if both_cw else 1) + int(local)


def finish(event, category, rows, result, context, problems):
    if event.get('regional',{}).get('profile')=='kyoto':
        try:
            from decimal import Decimal,ROUND_CEILING
            factor=kyoto_factor(category,context);result.multi2=factor
            if result.total is not None:result.total=(result.points*result.multi1*factor).to_integral_value(rounding=ROUND_CEILING)
            category.setdefault('_timing_summary',[]).append('京都ニューカマー係数 '+str(factor)+'：最終結果だけ切上げ')
        except ValueError as ex:problems.append(str(ex))
    if event.get('regional',{}).get('profile')=='nara':
        counts=getattr(result,'multiplier_counts',{})
        result.multi1=counts.get('tail',0);result.multi2=counts.get('year',0)
        if result.total is not None:result.total=result.points*result.multi1*result.multi2


def submission_info(rule, ctx, info, rows):
    if rule.get('event',{}).get('regional',{}).get('profile')!='nara' or ctx.get('submission_mode')=='checklog':return info
    kind=ctx.get('declarations',{}).get('operator_kind','').strip().upper()
    if kind not in ('SO','MO'):raise ValueError('奈良の実運用者区分をSO又はMOと記入してください。')
    if (kind=='MO')!=bool(info.get('multiop')):raise ValueError('奈良の実運用者区分と提出者設定が一致しません。')
    if kind=='MO':
        roster=info.get('multioplist','').upper()
        if not roster:raise ValueError('MOは運用者のコール（無い人は氏名）と資格が必要です。')
        import re
        for v in rows:
            name=v.get('operator_name','').strip().upper()
            if not name or not re.search(r'(?<![A-Z0-9/])'+re.escape(name)+r'(?![A-Z0-9/])',roster):raise ValueError('各行の担当者がMO一覧に含まれていません。')
    return info


def kyoto_number(event, raw):
    import re
    raw=str(raw or '').strip().upper()
    local=event['regional']['local_a'];out=event['regional']['local_b']
    matches=[x for x in local+out if raw.startswith(x)]
    if not matches:raise ValueError('京都の専用地域符号が未確認です。')
    region=max(matches,key=len);suffix=raw[len(region):]
    if not re.fullmatch('[A-Z]{2}',suffix) and not (region in local and re.fullmatch('[0-9]{3}',suffix)):raise ValueError('地域符号の後にイニシャル2文字、又は府内の登録番号3桁が必要です。')
    return region,suffix


def prepare_kyoto(e,c,v,ctx):
    own,_=kyoto_number(e,v.get('sent'));other,second=kyoto_number(e,v.get('exchange'));inside=own in e['regional']['local_a'];local=other in e['regional']['local_a']
    if inside!=(c['id'][0]=='I'):raise ValueError('送信地域と京都府内外の部門が一致しません。')
    v['_sent_region']=own;v['area']=other;v['prefix']=second
    v['_computed_points']=(2 if local else 1) if inside else (1 if local else 0)
    if not inside and not local:v['_excluded_reason']='府外同士の交信は対象外'


def kyoto_factor(c,ctx):
    from datetime import datetime
    from decimal import Decimal
    if c.get('operator')=='MO':return Decimal(1)
    d=ctx.get('declarations',{})
    try:age=int(d.get('participation_age',''))
    except (ValueError,TypeError):raise ValueError('京都は参加時の実年齢を整数で確認してください。')
    if not 0<=age<=125:raise ValueError('参加時年齢が不正です。')
    if age<=18:
        try:birth=datetime.strptime(d.get('young_birthdate',''),'%Y-%m-%d')
        except (ValueError,TypeError):raise ValueError('18歳以下の係数申告には生年月日が必要です。')
        if not 2007<=birth.year<=2026:raise ValueError('生年月日と18歳以下の申告を確認してください。')
        return Decimal('2.5')
    raw=d.get('first_license_date','')
    if raw=='対象外':return Decimal(1)
    try:date=datetime.strptime(raw,'%Y-%m-%d')
    except (ValueError,TypeError):raise ValueError('成人は初開局日をYYYY-MM-DDで、係数対象外の場合は「対象外」と記入してください。')
    if date>datetime(2026,2,8):raise ValueError('初開局日が開催後です。')
    for boundary,factor in [('2025-02-02','2.5'),('2024-02-05','1.5'),('2023-02-06','1.2')]:
        if raw>=boundary:return Decimal(factor)
    return Decimal(1)
