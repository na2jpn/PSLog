"""Submission-only profiles; original records and raw exchanges never rewritten."""
import re,math
from datetime import datetime,timedelta
from decimal import Decimal,InvalidOperation
PROFILES={'aadx','jarl_rtty','ww_digi','okayama_ft','miyazaki'}

def code(value):
    value=str(value or '').strip().upper()
    if not re.fullmatch('[A-Z0-9]+(?:[-/][A-Z0-9]+)*',value):raise ValueError('DXCC識別子を確認してください。本土JA/K/VE/VKと島嶼を区別します。')
    return value

def continent(value):
    value=str(value or '').upper()
    if value not in ('AF','AN','AS','EU','NA','OC','SA'):raise ValueError('実運用大陸を確認してください。')
    return value

def age_number(raw,allow_zero=False):
    raw=str(raw or '').strip()
    if not re.fullmatch(r'[0-9]{1,3}(?:\.[0-9]+)?',raw) or not (0 if allow_zero else 1)<=Decimal(raw)<=150:raise ValueError('実交換の年齢・平均年齢を確認してください。代替番号は大会の規定に従います。')
    return raw

def rst(v):
    pat='[1-5][1-9]' if v['mode'] in ('SSB','AM','FM') else '[1-5][1-9][1-9]'
    if any(not re.fullmatch(pat,str(v.get(k,''))) for k in ('rst_sent','rst_received')):raise ValueError('実際に交換したRS(T)が必要です。')

def first24(ctx):
    from contest_timing import stamp
    budget=1440;last=None
    for b in sorted(ctx.get('operating_blocks',[]),key=lambda b:b['start']):
        a,z=stamp(b['start']),stamp(b['end']);gap=0 if last is None else int((a-last).total_seconds()/60)
        if last and gap<60:
            if gap>=budget:return last+timedelta(minutes=budget)
            budget-=gap
        duration=int((z-a).total_seconds()/60)
        if duration>=budget:return a+timedelta(minutes=budget)
        budget-=duration;last=z
    return None

def call_area(call):
    parts=str(call).strip().upper().split('/');parts=[p for p in parts if p not in ('P','M','QRP')]
    if len(parts)>2:raise ValueError('複合移動コールのエリアを一意に判定できません。実コール表記を確認してください。')
    if len(parts)==2:
        if any(re.fullmatch('[0-9]',p) for p in parts):return next(p for p in parts if re.fullmatch('[0-9]',p))
        # A portable prefix has its own final prefix digit; no digit means area0.
        a,b=parts
        if len(a)==len(b):raise ValueError('同長複合コールはエリア要確認です。')
        portable=min(parts,key=len);digits=re.findall('[0-9]',portable);return digits[-1] if digits else '0'
    prefix=re.match('[A-Z0-9]*[0-9]',parts[0])
    if not prefix:raise ValueError('本土局コールエリアが判定できません。')
    return re.findall('[0-9]',prefix.group())[-1]

def prepare_row(e,c,v,ctx):
    kind=e.get('regional',{}).get('profile')
    if kind not in PROFILES:return
    d=ctx.get('declarations',{})
    if kind in ('ww_digi','okayama_ft'):
        from contest_international import grid
        from contest_event import grid_distance
        own=grid(v.get('my_grid'));raw=str(v.get('his_grid') or '').upper();unknown=kind=='ww_digi' and raw=='ZZ00';his='ZZ00' if unknown else grid(raw)
        if v.get('sent') and grid(v['sent'])!=own:raise ValueError('送信番号と自局GLが一致しません。')
        if v.get('exchange') and (str(v['exchange']).upper() if unknown else grid(v['exchange']))!=his:raise ValueError('受信番号と相手GLが一致しません。')
        v.update(my_grid=own,his_grid=his,area=his if kind=='okayama_ft' else his[:2]);v['_computed_points']=1 if kind=='okayama_ft' else 0 if unknown else 1+math.floor(grid_distance(own,his)/3000)
        if unknown:v['_regional_multi']=False;v['_unknown_grid']=True
        return
    rst(v)
    if kind=='miyazaki':return miyazaki_row(e,c,v,ctx)
    own=code(d.get('own_entity'));oc=continent(d.get('own_continent'));mm=str(v['call']).upper().endswith('/MM');ownmm=str(v.get('own','')).upper().endswith('/MM');other='MM' if mm else code(v.get('country'));hc=oc if mm else continent(v.get('continent'))
    if mm:v['continent']=None
    age_number(v.get('exchange'),kind=='jarl_rtty');sent=age_number(v.get('sent'),kind=='jarl_rtty')
    if sent!=age_number(d.get('exchange_age'),kind=='jarl_rtty'):raise ValueError('実送信年齢と参加条件の申告が一致しません。')
    if kind=='aadx':
        if c['id'] in ('SOJR','SOSV') and (own not in ('JA','JD1-OGASAWARA','JD1-MINAMITORISHIMA') or ownmm):raise ValueError('SOJR/SOSVはJA又は所在地確認済みの日本島嶼DXCC識別子が必要です。')
        if c['id'] in ('SOJR','SOSV') and sent!='01' and Decimal(sent)!=ctx.get('age'):raise ValueError('SOJR/SOSVの実送信年齢と参加年齢が一致しません。')
        cutoff=first24(ctx) if c['id'].endswith('24') else None
        if cutoff and v['_contest_time']>=cutoff:v['_excluded_reason']='最初24運用時間以後（提出には保持）';return
        base=3 if v['band']=='1.9' else 2 if v['band'] in ('3.5','28') else 1
        if mm or ownmm:
            valid=(oc=='AS' if mm else hc=='AS');v['_computed_points']=base if valid else 0
            if mm or not valid:v['_regional_multi']=False
            else:
                from contest_event import wpx_prefix
                v['area']='E_'+other if oc=='AS' else 'P_'+wpx_prefix(v['call'])
            if not valid:v['_excluded_reason']='公海MMはアジアとの交信のみ有効'
        elif own==other or oc!='AS' and hc!='AS':v['_computed_points']=0;v['_regional_multi']=False;v['_excluded_reason']='同一entity又は非アジア間'
        else:
            v['_computed_points']=base*(3 if oc=='AS' and hc!='AS' else 1)
            from contest_event import wpx_prefix
            v['area']='E_'+other if oc=='AS' else 'P_'+wpx_prefix(v['call'])
    else:
        v['_computed_points']=2 if mm or oc==hc else 3
        if mm:v['_regional_multi']=False
        elif other in ('JA','K','W','VE','VK'):v['area']='A_'+('K' if other=='W' else other)+'_'+call_area(v['call'])
        else:v['area']='E_'+other

def miyazaki_row(e,c,v,ctx):
    local=e['regional']['local_a'];out=e['regional']['local_b'];sent=str(v.get('sent') or '').upper();received=str(v.get('exchange') or '').upper();own=ctx.get('declarations',{}).get('sent_region','').upper();kenjin=c['id']=='MKJ';inside=c['id'].startswith('M') and not kenjin
    allowed=[x+'KJ' for x in local] if kenjin else local if inside else out
    if own not in allowed:raise ValueError('自局の送信地域申告と県内・県外・県人区分が一致しません。')
    # The empty additional exchange is explicitly permitted only with foreign stations.
    foreign=not received
    if sent!=own and not (inside and foreign and not sent):raise ValueError('実送信番号と自局地域が一致しません。')
    if foreign:
        if not (inside or kenjin):v['_excluded_reason']='県外から一般国外局は対象外';return
        hc=continent(v.get('continent'))
        if not v.get('country') or code(v['country']) in ('JA','JD1'):raise ValueError('追加番号なしの国外局は実運用の国・地域を確認してください。')
        v['_computed_points']=1
        if kenjin or hc=='AN':v['_regional_multi']=False
        else:v['area']='DX_'+hc
    else:
        base=received[:-2] if received.endswith('KJ') else received
        if base not in local+out or received.endswith('KJ') and base not in local:raise ValueError('宮崎の市郡・県地域・KJ実交換番号を確認してください。')
        if not inside and not kenjin and base not in local:v['_excluded_reason']='県外同士は対象外';return
        v['area']=base;v['_computed_points']=1

def finish(e,c,rows,result,ctx,problems):
    kind=e.get('regional',{}).get('profile')
    if kind not in PROFILES:return
    if kind in ('ww_digi','okayama_ft'):
        grids={v.get('my_grid') for v in rows if v.get('_timing_scope') and not v.get('_event_error') and v.get('my_grid')}
        if len(grids)>1:problems.append('この大会は単一運用地です。自局GLの変更を確認してください。')
        unknown=[i for i,(v,s) in enumerate(zip(rows,result.rows)) if v.get('_unknown_grid') and s.get('eligible')]
        if unknown:
            result.total=None;result.unscored_submission=True;result.unknown_grid_count=len(unknown)
            for i in unknown:result.rows[i]['points']=None;result.rows[i]['reason']='GL未受信ZZ00：距離未確定'
            c.setdefault('_timing_summary',[]).append('受信GL不明のため総得点未確定。既知交信だけの小計を表示し、CLAIMED-SCOREは省略します。')
    if kind=='aadx' and c['id'].startswith('MS'):
        seen=set();run=None
        for i,v in sorted(enumerate(rows),key=lambda p:(p[1].get('_contest_time',datetime.min),p[0])):
            if not v.get('_timing_scope'):continue
            tokens={tuple(t) for t in result.rows[i].get('multiplier_tokens',[])}
            if v.get('tx')=='0':run=v['band']
            elif v.get('tx')=='1':
                if v['band']==run or not tokens-seen:problems.append(f'{i+1}行目: MSのMULT系列はRUNと異なる帯域の新マルチだけです。')
            seen|=tokens
    if kind=='jarl_rtty':
        d=ctx.get('declarations',{});choice=d.get('youth','').upper()
        if choice not in ('NONE','YOUTH'):problems.append('YOUTH又はNONEを指定してください。')
        if choice=='YOUTH':
            try:
                from contest_tagged_region import age_at
                if c.get('operator')!='SO' or not 0<=age_at(d.get('youth_birth'),'2026-10-17')<=25:raise ValueError('YOUTHは開始時25歳以下のSOです。')
            except (ValueError,TypeError) as ex:problems.append(str(ex))

def headers(rule,c,ctx):
    if c.get('_whole_checklog'):return {'CATEGORY-OPERATOR':'CHECKLOG'}
    kind=rule['event']['regional']['profile'];code=c['id'];d=ctx.get('declarations',{})
    if kind=='aadx':
        so=c.get('operator')=='SO';overlay=code if code in ('SOJR','SOSV') else '';h={'CATEGORY-OPERATOR':'SINGLE-OP' if so else 'MULTI-OP','CATEGORY-BAND':next((m for m,b in zip(['160M','80M','40M','20M','15M','10M'],['1.9','3.5','7','14','21','28']) if c['bands']==[b]),'ALL'),'CATEGORY-MODE':'CW' if rule['id'].endswith('cw') else 'SSB','CATEGORY-TRANSMITTER':'ONE' if so or code.startswith('MS') else 'UNLIMITED','CATEGORY-TIME':'24-HOURS' if code.endswith('24') else '', 'CATEGORY-OVERLAY':overlay}
        h['CATEGORY-POWER']=('LOW' if Decimal(str(ctx.get('power',0)))<=100 else 'HIGH') if overlay else ('LOW' if 'LP' in code else 'HIGH')
        return h
    if kind=='jarl_rtty':
        return {'CATEGORY-OPERATOR':'SINGLE-OP' if c['operator']=='SO' else 'MULTI-OP','CATEGORY-POWER':'QRP' if code=='SOQRP' else 'LOW' if code.endswith('LP') else 'HIGH','CATEGORY-BAND':'ALL','CATEGORY-MODE':'RTTY','CATEGORY-OVERLAY':'YOUTH' if d.get('youth','').upper()=='YOUTH' else ''}
    if kind=='okayama_ft':return {'CATEGORY-OPERATOR':'MULTI-OP' if c['operator']=='MO' else 'SINGLE-OP','CATEGORY-BAND':'ALL','CATEGORY-MODE':'DIGI',**({'CATEGORY-POWER':'QRP'} if code.endswith('P') else {})}
    if kind=='ww_digi':
        p=code.split('_');return {'CATEGORY-OPERATOR':'SINGLE-OP' if p[0]=='SO' else 'MULTI-OP','CATEGORY-TRANSMITTER':p[1],'CATEGORY-POWER':p[2],'CATEGORY-BAND':p[3] if len(p)>3 else 'ALL','CATEGORY-MODE':'DIGI'}
    return {}

def submission_info(rule,ctx,info):
    kind=rule.get('event',{}).get('regional',{}).get('profile');out=dict(info);d=ctx.get('declarations',{})
    if kind=='jarl_rtty' and d.get('youth','').upper()=='YOUTH':out['age']='YOUTH';out['comments']=' / '.join(x for x in [info.get('comments',''),'YOUTH 生年月日 '+d['youth_birth']] if x)
    if kind=='aadx' and ctx.get('category') in ('SOJR','SOSV'):out['SOAPBOX']='\n'.join(x for x in [info.get('SOAPBOX',''),'Age at start: '+str(ctx.get('age'))] if x)
    if kind=='miyazaki' and ctx.get('category')=='MKJ':
        op=d.get('operator_kind','').upper()
        if op not in ('SO','MO') or bool(info.get('multiop'))!=(op=='MO') or op=='MO' and not info.get('multioplist','').strip():raise ValueError('県人部門のSO/MO・運用者一覧を確認してください。')
    return out
