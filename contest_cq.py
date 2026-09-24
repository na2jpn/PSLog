"""CQ WW/WPX points, independent multipliers and separate overlay claims."""
from datetime import datetime,timedelta
from copy import deepcopy
import re

PROFILES={'cq_ww','cq_ww_rtty','cq_wpx','cq_wpx_rtty'}

def zone(raw):
    if not re.fullmatch('[0-9]{1,2}',str(raw)) or not 1<=int(raw)<=40:raise ValueError('実交換CQゾーン1～40を確認してください。')
    return str(int(raw))

def geography(v,ctx):
    from contest_international import entity
    d=ctx.get('declarations',{});own=entity(d.get('own_cq_entity'));oc=d.get('own_continent','').upper();hc=str(v.get('continent') or '').upper()
    if oc not in ('AF','AN','AS','EU','NA','OC','SA') or hc not in ('AF','AN','AS','EU','NA','OC','SA'):raise ValueError('自他局の実運用地の大陸を確認してください。')
    mm=str(v['call']).upper().endswith('/MM');other='MM' if mm else entity(v.get('cq_entity'))
    return own,oc,other,hc,mm

def rtty_number(raw,entity):
    from contest_international import exchange_160
    parts=str(raw or '').strip().upper().split()
    if not parts:raise ValueError('RTTYの実交換ゾーンが空欄です。')
    z=zone(parts[0]);qth=parts[1] if len(parts)==2 else ''
    if len(parts)>2:raise ValueError('RTTY交換はゾーンと必要な州・地域です。')
    if entity in ('K','VE'):
        if not qth:raise ValueError('米加本土の州・地域番号を確認してください。DXで埋めることはできません。')
        multiplier=exchange_160(qth,entity)
    else:
        if qth not in ('','DX'):raise ValueError('米加本土以外のRTTY地域欄はDXです。')
        multiplier=None
    return z,multiplier

def prepare_row(e,c,v,ctx):
    kind=e.get('regional',{}).get('profile')
    if kind not in PROFILES:return
    cutoff=ctx.get('_cq_overlay_cutoff')
    if cutoff and v['_contest_time']>=datetime.strptime(cutoff,'%Y-%m-%d %H:%M'):v['_excluded_reason']='CLASSICの最初24時間以降';return
    own,oc,other,hc,mm=geography(v,ctx);rtty=kind.endswith('rtty');wpx='wpx' in kind
    pattern='[1-5][1-9]' if v['mode']=='SSB' else '[1-5][1-9][1-9]'
    if any(not re.fullmatch(pattern,str(v.get(k,''))) for k in ('rst_sent','rst_received')):raise ValueError('実際に交換したRS(T)を確認してください。')
    if wpx:
        for field in ('sent','exchange'):
            if not re.fullmatch('[0-9]{1,6}',str(v.get(field,''))) or int(v[field])<1:raise ValueError('WPXは実際の正の連番です。再採番はしません。')
        from contest_event import wpx_prefix
        v['prefix']=wpx_prefix(v['call']);low=v['band'] in ('1.9','3.5','7');factor=2 if low else 1
        v['_computed_points']=(1*factor if rtty else 1) if own==other else 3*factor if oc!=hc else (2 if rtty or oc=='NA' else 1)*factor
    else:
        if rtty:
            sent,_=rtty_number(v.get('sent'),own);received,qth=rtty_number(v.get('exchange'),other)
            v['prefix']=qth or 'DX';v['_skip_multis']=[] if qth else ['wve']
        else:sent=zone(v.get('sent'));received=zone(v.get('exchange'));v['_skip_multis']=[]
        if sent!=zone(ctx.get('declarations',{}).get('own_cq_zone','')):raise ValueError('実送信ゾーンと自局の運用ゾーンが一致しません。')
        v['area']=received;v['country']=other
        if mm:v['_skip_multis']+=['country','wve']
        v['_computed_points']=(1 if rtty else 0) if own==other else 3 if oc!=hc else 2 if rtty or oc=='NA' else 1


def headers(rule,c,ctx):
    kind=rule['event']['regional']['profile'];p=c['id'].split('_');so=p[0] in ('SO','SA');wpx='wpx' in kind
    h={'CATEGORY-OPERATOR':'SINGLE-OP' if so else 'MULTI-OP','CATEGORY-BAND':p[2] if so else 'ALL','CATEGORY-POWER':p[1] if so else p[-1],
       'CATEGORY-MODE':'RTTY' if kind.endswith('rtty') else 'CW' if rule['id'].endswith('cw') else 'SSB',
       'CATEGORY-TRANSMITTER':'ONE' if so or p[0]=='MS' else 'TWO' if p[0]=='M2' else 'UNLIMITED',
       'CATEGORY-ASSISTED':'ASSISTED' if wpx or p[0]!='SO' else 'NON-ASSISTED','CATEGORY-STATION':'DISTRIBUTED' if p[0]=='MD' else 'FIXED'}
    overlay=ctx.get('declarations',{}).get('overlay','NONE').strip().upper()
    h['CATEGORY-OVERLAY']='' if overlay=='NONE' else overlay
    if overlay=='CLASSIC':h['CATEGORY-ASSISTED']='NON-ASSISTED'
    return h


def finish(rule_event,c,rows,result,ctx,problems):
    e=rule_event;kind=e.get('regional',{}).get('profile')
    if kind not in PROFILES:return
    timed=[(i,v) for i,v in enumerate(rows) if v.get('_timing_scope')]
    if c['id'].startswith('MS') and 'wpx' not in kind:
        seen=set();run=None
        for i,v in sorted(timed,key=lambda pair:(pair[1]['_contest_time'],pair[0])):
            s=result.rows[i];tokens={tuple(t) for t in s.get('multiplier_tokens',[])};tx=v.get('tx')
            if tx=='0':run=v['band']
            elif tx=='1':
                if v['band']==run:problems.append(f'{i+1}行目: MULT系列はRUNと異なるバンドが必要です。')
                if not tokens-seen:problems.append(f'{i+1}行目: MULT系列は新しいマルチの交信だけです。')
            seen|=tokens
    if 'wpx' in kind:
        # Validate actual sequences without changing gaps, padding or row order.
        seen={};last={};band_serial=c['id'].startswith(('M2','MM','MD'))
        for i,v in sorted(timed,key=lambda pair:(pair[1]['_contest_time'],pair[0])):
            raw=str(v.get('sent',''));scope=v['band'] if band_serial else '*'
            if not raw.isdigit():continue
            n=int(raw)
            if n in seen.setdefault(scope,set()):problems.append(f'{i+1}行目: 送信連番が同じ系列内で再使用されています。実交換記録を確認してください。')
            if scope in last and n<last[scope]:problems.append(f'{i+1}行目: 時系列に対して送信連番が逆行しています。元番号を再採番せず確認してください。')
            seen[scope].add(n);last[scope]=n


def overlay(rule,c,rows,result,ctx,problems):
    e=rule['event'];kind=e.get('regional',{}).get('profile')
    if kind not in PROFILES or ctx.get('_skip_cq_overlay'):return
    d=ctx.get('declarations',{});choice=d.get('overlay','NONE').strip().upper();wpx='wpx' in kind
    if choice=='NONE':return
    if c.get('operator')!='SO':problems.append('OverlayはSOだけです。');return
    if choice not in ('CLASSIC','ROOKIE','YOUTH') and not (wpx and choice=='TB-WIRES'):problems.append('この大会のOverlay区分が不正です。');return
    evidence=d.get('overlay_evidence','').strip();start=datetime.strptime(e['windows'][0]['start'],'%Y-%m-%d %H:%M')
    cutoff=None
    try:
        if choice in ('ROOKIE','YOUTH'):
            date=datetime.strptime(evidence,'%Y-%m-%d')
            if date>start:raise ValueError('資格の日付が大会開始より後です。')
            if choice=='ROOKIE':
                boundary=start.replace(year=start.year-3,hour=0,minute=0)
                if date<boundary or not wpx and date==boundary:raise ValueError('ROOKIEはWWで3年未満、WPXで3年以下です。')
            else:
                age=start.year-date.year-((start.month,start.day)<(date.month,date.day))
                if age>25:raise ValueError('YOUTHは開始時25歳以下です。')
        elif choice=='CLASSIC':
            if c['id'].startswith('SA_'):raise ValueError('Assisted部門はCLASSICへ申告できません。')
            from contest_timing import parse_blocks,check_operating,stamp
            blocks=parse_blocks(evidence.replace(';','\n'));windows=[(stamp(w['start']),stamp(w['end']),w['bands']) for w in e['windows']]
            p,_=check_operating({'max_minutes':100000,'min_off_minutes':60},windows,[(i,v) for i,v in enumerate(rows) if v.get('_timing_scope')],dict(ctx,operating_blocks=blocks))
            if p:raise ValueError('; '.join(p))
            budget=1440;last=None
            for b in sorted(blocks,key=lambda b:b['start']):
                a,z=stamp(b['start']),stamp(b['end']);gap=0 if last is None else int((a-last).total_seconds()/60)
                if last and gap<60:
                    if gap>=budget:cutoff=last+timedelta(minutes=budget);break
                    budget-=gap
                duration=int((z-a).total_seconds()/60)
                if duration>=budget:cutoff=a+timedelta(minutes=budget);break
                budget-=duration;last=z
        elif not evidence:raise ValueError('TB-WIRESのアンテナ構成を記入してください。')
        copy=deepcopy(rule);cat=next(x for x in copy['event']['categories'] if x['id']==c['id']);cat['bands']=list(dict.fromkeys(b for w in e['windows'] for b in w['bands']));cat['min_bands']=0;cat['max_bands']=len(cat['bands']);cat['min_calls']=0
        context=deepcopy(ctx);context['_skip_cq_overlay']=True
        if cutoff:context['_cq_overlay_cutoff']=cutoff.strftime('%Y-%m-%d %H:%M')
        # Rebuild from original working values: rows passed here are already
        # annotated, so strip transient keys and re-run the event from clean copies.
        clean_rows=[{k:v for k,v in row.items() if not k.startswith('_')} for row in rows]
        from contest_rules import score
        score_value=score(copy,clean_rows,context)
        if score_value.problems:raise ValueError('; '.join(score_value.problems[:3]))
        result.overlay_score=score_value.total;result.overlay_category=choice
        c.setdefault('_timing_summary',[]).append(f'{choice} 全帯域別集計（本体得点と別）: {score_value.total}')
    except (ValueError,TypeError) as ex:problems.append('Overlay: '+str(ex))

def submission_info(rule,ctx,info):
    if rule.get('event',{}).get('regional',{}).get('profile') not in PROFILES:return info
    d=ctx.get('declarations',{});choice=d.get('overlay','NONE').strip().upper()
    if choice=='NONE':return info
    out=dict(info);evidence=d.get('overlay_evidence','').strip()
    label={'ROOKIE':'First licensed','YOUTH':'Birth date','TB-WIRES':'Antenna configuration','CLASSIC':'Operating periods UTC'}.get(choice,'Overlay')
    text=choice+' '+label+': '+evidence
    # ASCII Cabrillo can contain only confirmed ASCII facts; physical-operation
    # Japanese confirmation labels are not copied into the output.
    if any(ord(ch)>126 for ch in text):raise ValueError('CabrilloのOverlay根拠は半角英数で記入してください。')
    import textwrap
    extra='\n'.join(textwrap.wrap(text,width=75,break_long_words=True,break_on_hyphens=False))
    out['SOAPBOX']='\n'.join(v for v in (info.get('SOAPBOX','').strip(),extra) if v)
    return out
