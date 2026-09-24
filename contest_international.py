"""Explicit international contest processing on submission copies only."""
import re
from copy import deepcopy
from dataclasses import replace
from contest_event import grid_center

PROFILES={'jarl_rtty','aadx','ww_digi','okayama_ft','cq_vhf','cq160','cq_ww','cq_ww_rtty','cq_wpx','cq_wpx_rtty'}

def profile(rule):return rule.get('event',{}).get('regional',{}).get('profile') in PROFILES

def grid(value):
    value=str(value or '').strip().upper()
    if not re.fullmatch('[A-R]{2}[0-9]{2}(?:[A-X]{2})?',value):raise ValueError('実交換の4桁又は6桁GLを確認してください。')
    return value[:4]

def prepare_row(e,c,v,ctx):
    if e.get('regional',{}).get('profile')=='cq160':return prepare_160(e,c,v,ctx)
    if e.get('regional',{}).get('profile')!='cq_vhf':return
    own=grid(v.get('my_grid'));his=grid(v.get('his_grid'))
    for field,g in [('sent',own),('exchange',his)]:
        if v.get(field) and grid(v[field])!=g:raise ValueError('交換番号と提出用GLが一致しません。実記録を確認してください。')
    v['my_grid']=own;v['his_grid']=his
    rover=c['id']=='ROVER'
    v['area']=(own+'_'+his) if rover else his
    v['_computed_points']=1 if v['band']=='50' else 2
    v['_vhf_rover']=rover
    if rover and not str(v.get('own','')).upper().endswith('/R'):raise ValueError('Roverの提出コールには/Rを付け、実際の運用コールと一致させてください。')


def finish(e,c,rows,result,ctx,problems):
    if e.get('regional',{}).get('profile')!='cq_vhf':return
    valid=[v for v in rows if v.get('_timing_scope') and not v.get('_event_error')]
    grids={v['my_grid'] for v in valid if v.get('my_grid')}
    if c['id']=='ROVER':
        if len(grids)<2:problems.append('Roverは2つ以上のGLでの運用が必要です。')
        try:
            count=int(ctx.get('declarations',{}).get('operator_count',''))
            if count not in (1,2):raise ValueError()
        except (ValueError,TypeError):problems.append('Roverの実運用者数は1又は2を申告してください。')
    elif len(grids)>1:problems.append('Rover以外は単一運用地・同一GLです。')
    if c['id']=='HILLTOPPER' and valid:
        blocks=ctx.get('operating_blocks',[])
        if blocks:
            from contest_timing import stamp
            if (max(stamp(b['end']) for b in blocks)-min(stamp(b['start']) for b in blocks)).total_seconds()>21600:problems.append('Hilltopperの申告運用区間全体は連続6時間以内です。')
        times=[v['_contest_time'] for v in valid]
        if (max(times)-min(times)).total_seconds()>=21600:problems.append('Hilltopperは連続6時間以内です。')
    calls={}
    for v in valid:
        if v.get('his_grid'):calls.setdefault(v['call'].upper(),set()).add(v['his_grid'])
    if any(len(gs)>1 and not call.endswith('/R') for call,gs in calls.items()):problems.append('相手のGL変更があります。Roverの運用コール/Rと実記録を確認してください。')


def expected_headers(rule,c,ctx):
    if not profile(rule):return {}
    if c.get('_whole_checklog'):return {'CATEGORY-OPERATOR':'CHECKLOG'}
    code=c['id'];kind=rule['event']['regional']['profile']
    if kind in ('jarl_rtty','aadx','ww_digi','okayama_ft'):
        from contest_last6 import headers
        return headers(rule,c,ctx)
    if kind=='cq_vhf':
        op='SINGLE-OP' if code.startswith('SO_') else {'ROVER':'ROVER','HILLTOPPER':'HILLTOPPER','MO':'MULTI-OP'}[code]
        power=code.split('_')[1] if code.startswith('SO_') else 'LOW' if code=='HILLTOPPER' else None
        band=code.split('_')[2] if code.startswith('SO_') else 'ALL'
        h={'CATEGORY-OPERATOR':op,'CATEGORY-BAND':band,'CATEGORY-MODE':'DG' if rule['id'].endswith('digi') else None}
        if power:h['CATEGORY-POWER']=power
        return {k:v for k,v in h.items() if v is not None}
    if kind.startswith(('cq_ww','cq_wpx')):
        from contest_cq import headers
        return headers(rule,c,ctx)
    if kind=='cq160':
        parts=code.split('_');headers={'CATEGORY-OPERATOR':'MULTI-OP' if parts[0]=='MO' else 'SINGLE-OP','CATEGORY-BAND':'160M','CATEGORY-POWER':parts[-1],'CATEGORY-MODE':'CW' if rule['id'].endswith('cw') else 'SSB','CATEGORY-TRANSMITTER':'ONE','CATEGORY-ASSISTED':'ASSISTED' if parts[0] in ('SA','MO') or parts[-1]=='QRP' else 'NON-ASSISTED'}
        if parts[-1]=='QRP':headers.pop('CATEGORY-ASSISTED')
        return headers
    return {}


def export_values(selection,rule,draft,info,template,ctx):
    from contest_normalization import working_values
    from contest_export import key
    contest_id={'all_asian_dx_cw':'AADX-CW','all_asian_dx_phone':'AADX-SSB','all_okayama_ft':'WW-DIGI'}.get(rule['id'],rule['id'].upper())
    if not template or template.get('rule_id')!=rule['id'] or (rule['id']!='jarl_world_wide_rtty' and template.get('contest')!=contest_id):raise ValueError('この大会に対応したCabrilloテンプレートを選択してください。')
    if rule['id']!='jarl_world_wide_rtty' and info.get('CONTEST',template['contest'])!=template['contest']:raise ValueError('Cabrillo大会名が採点対象と一致しません。')
    c=next((v for v in rule['event']['categories'] if v['id']==ctx.get('category')), {})
    if ctx.get('submission_mode')=='checklog':c={'_whole_checklog':True}
    expected=expected_headers(rule,c,ctx)
    defaults={h['tag']:h['default'] for h in template['headers']}
    for k,v in expected.items():
        if info.get(k,defaults.get(k))!=v:raise ValueError('採点部門とCabrilloヘッダーが異なります: '+k+' = '+v)
    fields=[c['source'] for c in template['columns']]
    kind=rule['event']['regional']['profile']
    expected_fields=['frequency','mode','date','time','own','my_grid','call','his_grid'] if kind in ('cq_vhf','ww_digi','okayama_ft') else ['frequency','mode','date','time','own','rst_sent','sent','call','rst_received','received']
    if kind in ('aadx','ww_digi','okayama_ft'):expected_fields+=['tx']
    if kind.startswith(('cq_ww','cq_wpx')):
        expected_fields+=['tx']
        if kind=='cq_ww_rtty':expected_fields=['frequency','mode','date','time','own','rst_sent','sent','sent','call','rst_received','received','received','tx']
    if fields!=expected_fields:raise ValueError('大会指定のCabrillo交換列順と異なります。')
    if not info.get('EMAIL',defaults.get('EMAIL','')).strip():raise ValueError('EMAILを入力してください。')
    if kind=='cq_vhf' and not rule['id'].endswith('digi') and info.get('CATEGORY-MODE',defaults.get('CATEGORY-MODE')) not in ('SSB','CW','FM','MIXED'):raise ValueError('CQ VHF音声・電信部門のMODEが不正です。')
    if kind=='ww_digi' and len(info.get('ADDRESS','').splitlines())>4:raise ValueError('WW-DIGIのADDRESSは4行以内です。')
    d=deepcopy(draft);rows=[]
    for row in selection.rows:
        own,q,p,n=row;data=d.setdefault(key(row),{});b,m=working_values(rule['event'],q.band,q.mode,data.get('contest_band',''))
        if rule['id']=='cq-vhf-digi' and m not in template['modes']:m='DG'
        if m not in template['modes']:raise ValueError('この大会のCabrilloに対応しないモードです: '+m)
        if kind.startswith(('cq_ww','cq_wpx')):
            if not c.get('timing',{}).get('band_change',{}).get('tx_ids'):data['tx']=data.get('tx') or '0'
            if kind=='cq_ww_rtty':
                for field in ('sent','received'):
                    value=str(data.get(field,'')).strip()
                    if len(value.split())==1:data[field]=value+' DX'
        if kind in ('cq_vhf','ww_digi','okayama_ft'):
            data['my_grid']=grid(data.get('my_grid'));data['his_grid']='ZZ00' if kind=='ww_digi' and data.get('his_grid','').upper()=='ZZ00' else grid(data.get('his_grid'))
        if kind=='aadx' and c.get('operator')=='MO' and str(data.get('tx','')) not in tuple('012345'):raise ValueError('AADX MOは実際の送信機ID0～5が必要です。')
        if kind in ('aadx','ww_digi','okayama_ft'):
            if not c.get('timing',{}).get('band_change',{}).get('tx_ids'):data['tx']=data.get('tx') or '0'
        if kind=='cq_ww_rtty':
            from contest_cq import rtty_number
            rtty_number(data.get('sent'),ctx.get('declarations',{}).get('own_cq_entity',''))
            rtty_number(data.get('received'),'MM' if q.call.upper().endswith('/MM') else entity(data.get('cq_entity')))
        if kind=='cq_vhf' and not rule['id'].endswith('digi'):
            header_mode=info.get('CATEGORY-MODE',defaults.get('CATEGORY-MODE'))
            if header_mode!='MIXED' and m!=header_mode:raise ValueError('CQ VHFのMODEヘッダーと提出交信のモードが一致しません。')
        rows.append((own,replace(q,band=b,mode=m),p,n))
    if kind=='ww_digi':rows.sort(key=lambda row:(row[1].date,row[1].time,row[3]))
    return replace(selection,rows=rows),d


US_STATES=set('AL AZ AR CA CO CT DE FL GA ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC'.split())
VE_PROVINCES=set('NF LB NB NS PEI QC ON MB SK AB BC NT YT NU'.split())
VE_ALIAS={'VO1':'NF','VO2':'LB','VY2':'PEI','PE':'PEI','VE2':'QC','VE3':'ON','VE4':'MB','VE5':'SK','VE6':'AB','VE7':'BC','VE8':'NT','NWT':'NT','VY1':'YT','VY0':'NU'}

def entity(value):
    value=str(value or '').strip().upper()
    if not re.fullmatch('[A-Z0-9]+(?:/[A-Z0-9]+)*',value):raise ValueError('CQ用カントリー識別子を別欄で確認してください（JA、DL、本土米K、カナダVEなど）。')
    return value

def exchange_160(raw,code):
    raw=str(raw or '').strip().upper()
    if code=='K':
        if raw not in US_STATES:raise ValueError('米国本土は48州又はDCの実交換番号が必要です。AK/HIは別カントリーです。')
        return 'K_'+raw
    if code=='VE':
        value=VE_ALIAS.get(raw,raw)
        if value not in VE_PROVINCES:raise ValueError('カナダの実交換番号を14地域へ対応させてください。')
        return 'VE_'+value
    if not re.fullmatch('[0-9]{1,2}',raw) or not 1<=int(raw)<=40:raise ValueError('米加本土以外は実交換CQゾーン1～40です。ゾーンはマルチにはしません。')
    return code

def prepare_160(e,c,v,ctx):
    d=ctx.get('declarations',{});own=entity(d.get('own_cq_entity'));continent=str(d.get('own_continent','')).upper()
    if continent not in ('AF','AN','AS','EU','NA','OC','SA'):raise ValueError('自局の運用大陸を確認してください。')
    exchange_160(v.get('sent'),own)
    pat='[1-5][1-9][1-9]' if v['mode']=='CW' else '[1-5][1-9]'
    for field in ('rst_sent','rst_received'):
        if not re.fullmatch(pat,str(v.get(field,''))):raise ValueError('実際に交換したRS(T)を入力してください。')
    if str(v['call']).upper().endswith('/MM'):
        if not str(v.get('exchange','')).strip():raise ValueError('海上移動局の実受信番号を保持してください。')
        v['_computed_points']=5;v['_regional_multi']=False;v['continent']=None;return
    other=entity(v.get('cq_entity'));other_continent=str(v.get('continent') or '').upper()
    if other_continent not in ('AF','AN','AS','EU','NA','OC','SA'):raise ValueError('相手の実運用地の大陸を確認してください。')
    v['area']=exchange_160(v.get('exchange'),other)
    v['_computed_points']=2 if own==other else 5 if continent==other_continent else 10
