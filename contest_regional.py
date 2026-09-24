"""Data-only regional event extensions. Never modify stored QSO records."""
import re
from decimal import Decimal


def base_call(call):
    parts=str(call).strip().upper().split('/')
    candidates=[p for p in parts if re.fullmatch(r'[A-Z0-9]*[0-9][A-Z]{1,4}',p)]
    if len(candidates)!=1:raise ValueError('同一局判定の基本コールを一意に確認できません。')
    return candidates[0]


def validate(event):
    from contest_rules import keys,number
    from contest_event import lists
    spec=event.get('regional',{})
    keys(spec,set(spec).intersection({'base_call_duplicates','sent_scope','checklog_code','entry_set','declarations','local_codes','outside_category_checklog','cw_award','club_sent_codes','profile','local_a','local_b','postal_codes','checklog_prefixes','missing_exchange'}),'地域大会拡張')
    if 'cw_award' in spec and type(spec['cw_award']) is not bool:raise ValueError('電信表彰指定は真偽値です。')
    if 'outside_category_checklog' in spec and type(spec['outside_category_checklog']) is not bool:raise ValueError('種目外チェックログ指定は真偽値です。')
    if 'base_call_duplicates' in spec and type(spec['base_call_duplicates']) is not bool:raise ValueError('基本コール重複指定は真偽値です。')
    if 'sent_scope' in spec and spec['sent_scope']!='window':raise ValueError('送信番号の区間指定が不正です。')
    if 'checklog_code' in spec and not re.fullmatch('[A-Z0-9_-]{1,40}',spec['checklog_code']):raise ValueError('チェックログコードが不正です。')
    if 'local_codes' in spec:lists(spec['local_codes'],'管内番号',10000)
    if 'club_sent_codes' in spec:lists(spec['club_sent_codes'],'クラブ対抗運用地番号',10000)
    declarations=spec.get('declarations',{})
    if not isinstance(declarations,dict) or len(declarations)>50:raise ValueError('追加申告の定義が不正です。')
    for k,v in declarations.items():
        if not re.fullmatch('[a-z][a-z0-9_]{0,39}',k) or not isinstance(v,str) or not v.strip() or any(x in v for x in '\r\n<>'):raise ValueError('追加申告の表記が不正です。')
    policy=spec.get('entry_set')
    if policy:
        keys(policy,('max','kind'),'複数提出')
        if type(policy['max']) is not int or not 1<=policy['max']<=10 or policy['kind'] not in ('disjoint','hf_vu','sections','singles_up','modes_disjoint','akita'):raise ValueError('複数提出条件が不正です。')
    for c in event['categories']:
        s=c.get('regional',{})
        keys(s,set(s).intersection({'quotas','min_operators','required_declarations','multiplier_map','multiplier_codes','points_by_code','required_band_groups','section','same_sent_region','junior_since','selected_bands','operator_assignments','half_only','entry_group','band_minima','birthdate_output','age_output','license_output'}),'部門地域拡張')
        if 'junior_since' in s:
            from contest_qualification import date_value
            date_value(s['junior_since'])
            if 'junior_birthdate' not in declarations:raise ValueError('ジュニア申告欄が必要です。')
        if 'same_sent_region' in s and type(s['same_sent_region']) is not bool:raise ValueError('同一送信地域条件は真偽値です。')
        if 'section' in s and (not isinstance(s['section'],str) or not s['section'].strip()):raise ValueError('提出区分が不正です。')
        if 'required_declarations' in s:
            lists(s['required_declarations'],'必要な追加申告')
            if not set(s['required_declarations'])<=set(declarations):raise ValueError('未定義の追加申告です。')
        if 'min_operators' in s and (type(s['min_operators']) is not int or not 1<=s['min_operators']<=1000):raise ValueError('実交信運用者数が不正です。')
        for name in ('multiplier_map','points_by_code'):
            if name not in s:continue
            mapping=s[name]
            if not isinstance(mapping,dict) or not mapping or len(mapping)>10000:raise ValueError('地域別対応表が不正です。')
            for k,v in mapping.items():
                if not isinstance(k,str) or not k:raise ValueError('対応表の番号が不正です。')
                if name=='points_by_code':
                    number(v,'地域別得点')
                    if v<0:raise ValueError('地域別得点が負数です。')
                elif not isinstance(v,str) or not v.strip():raise ValueError('マルチ変換先が不正です。')
        if 'multiplier_codes' in s:lists(s['multiplier_codes'],'マルチ対象番号',10000)
        groups=s.get('required_band_groups',[])
        if not isinstance(groups,list) or len(groups)>30:raise ValueError('必須帯域群が不正です。')
        for g in groups:
            lists(g,'必須帯域群')
            if not g or not set(g)<=set(c['bands']):raise ValueError('必須帯域群は種目対象バンドから指定してください。')
        quotas=s.get('quotas',[])
        if not isinstance(quotas,list) or len(quotas)>20:raise ValueError('地域別必要局数が不正です。')
        for q in quotas:
            keys(q,{'codes','min_calls'}|set(q).intersection({'unless_sent_in'}),'地域別必要局数');lists(q['codes'],'対象番号',10000)
            if 'unless_sent_in' in q:lists(q['unless_sent_in'],'自局地域による最低局数免除',10000)
            if type(q['min_calls']) is not int or not 1<=q['min_calls']<=100000:raise ValueError('必要局数が不正です。')


    from contest_regional_extended import validate as extended_validate
    extended_validate(event)

def check_context(event,category,ctx):
    from contest_export import clean
    if ctx.get('submission_mode')=='checklog':return []
    from contest_regional_extended import check_context as extended_check
    problems=extended_check(event,category,ctx)
    for ident in category.get('regional',{}).get('required_declarations',[]):
        try:clean(ctx.get('declarations',{}).get(ident,''),event['regional']['declarations'][ident],True)
        except (ValueError,AttributeError) as ex:problems.append(str(ex))
    since=category.get('regional',{}).get('junior_since')
    birth=ctx.get('declarations',{}).get('junior_birthdate','')
    if since and birth:
        try:
            from contest_qualification import date_value
            if not date_value(since)<=date_value(birth)<=date_value(event['windows'][0]['start'][:10]):raise ValueError('ジュニア申告の生年月日が対象期間外です。')
        except ValueError as ex:problems.append(str(ex))
    policy=event.get('regional',{}).get('entry_set')
    if policy:
        selected=ctx.get('entry_categories')
        if not isinstance(selected,list) or not selected or len(selected)!=len(set(selected)) or len(selected)>policy['max'] or category['id'] not in selected:
            return problems+['今回提出する全種目を選択し、上限と現在の種目を確認してください。']
        cats={c['id']:c for c in event['categories']}
        if any(k not in cats for k in selected):return problems+['提出セットに未知の種目があります。']
        if policy['kind'] in ('singles_up','modes_disjoint','akita'):return problems
        seen=set()
        for ident in selected:
            c=cats[ident];bands=set(c['bands'])
            group=({c.get('regional',{}).get('section')} if policy['kind']=='sections' else
                   {'HF' if float(b.replace('G','000'))<30 else 'VU' for b in bands} if policy['kind']=='hf_vu' else bands)
            if seen & group:problems.append('提出する種目の帯域・区分が重複しています。実交信を分割しても併願できません。')
            seen|=group
    return problems


def prepare_row(event,category,v,windows):
    s=category.get('regional',{});raw=v.get('exchange','');area=v.get('area','')
    if event.get('regional',{}).get('cw_award') and v.get('mode')=='CW':
        if any(not re.fullmatch('[1-5][1-9][1-9]',str(v.get(k,''))) for k in ['rst_sent','rst_received']):raise ValueError('電信交信の実送受信RSTは3桁で確認してください。599を自動補完しません。')
    local=event.get('regional',{}).get('local_codes')
    if local and event.get('regional',{}).get('profile')!='shiga' and v.get('_sent_region') not in local and raw not in local:v['_excluded_reason']='管外同士の交信は対象外'
    if 'points_by_code' in s and raw in s['points_by_code']:v['_computed_points']=s['points_by_code'][raw]
    if 'multiplier_codes' in s:v['_regional_multi']=raw in s['multiplier_codes']
    if 'multiplier_map' in s:v['area']=s['multiplier_map'].get(area,area)
    if event.get('regional',{}).get('sent_scope')=='window':
        v['_sent_region_scope']=next((str(i) for i,(a,z,bands) in enumerate(windows) if a<=v['_contest_time']<z and (not bands or v['band'] in bands)), 'outside')


def finish(category,valid,problems,operated=None):
    s=category.get('regional',{})
    bands={v['band'] for v in valid}
    for group in s.get('required_band_groups',[]):
        if not bands.intersection(group):problems.append('必要な帯域群で有効交信がありません: '+', '.join(group)+' MHz')
    for q in s.get('quotas',[]):
        if q.get('unless_sent_in') and valid and all(v.get('_sent_region') in q['unless_sent_in'] for v in valid):continue
        try:calls={base_call(v['call']) for v in valid if v.get('exchange') in q['codes']}
        except ValueError as ex:problems.append(str(ex));continue
        if len(calls)<q['min_calls']:problems.append(f'提出種目内の対象地域局との交信は {len(calls)} 局／必要 {q["min_calls"]} 局です。')
    if s.get('min_operators'):
        names=[v.get('operator_name','').strip().upper() for v in (valid if operated is None else operated)]
        if not names or any(not n for n in names):problems.append('有効交信ごとの実運用者を交信情報画面で割り当ててください。')
        elif len(set(names))<s['min_operators']:problems.append(f'実際に交信した運用者が最低 {s["min_operators"]} 人に届きません。名簿だけでは満たしません。')


def highest(rule,rows):
    from contest_rules import family,matches
    best={}
    for i,v in enumerate(rows):
        if v.get('_excluded_reason') or v.get('_event_error'):continue
        try:
            if not matches(rule['scoring']['eligible'],v):continue
            p=rule['points'][v.get('mode_family',family(v['mode']))]
            for c in rule['conditions']:
                if matches(c['when'],v):p=c['points'];break
            p=Decimal(str(v.get('_computed_points',p)));k=v['_duplicate_key']
            if k not in best or p>best[k][0]:best[k]=(p,i)
        except (ValueError,KeyError,TypeError):continue
    for i,v in enumerate(rows):
        k=v.get('_duplicate_key')
        if not v.get('_excluded_reason') and not v.get('_event_error') and k in best and i!=best[k][1]:v['_excluded_reason']='同局・同バンドの高得点交信を採用（同点は先頭）'


def submission_info(rule,ctx,info,rows):
    if ctx.get('submission_mode')=='checklog':return info
    e=rule.get('event',{});c=next((c for c in e.get('categories',[]) if c['id']==ctx.get('category')),{});problems=check_context(e,c,ctx)
    if problems:raise ValueError('\n'.join(problems))
    extra=[]
    for ident in c.get('regional',{}).get('required_declarations',[]):extra.append(e['regional']['declarations'][ident]+': '+ctx['declarations'][ident])
    if c.get('regional',{}).get('min_operators'):
        extra.append('交信担当: '+'; '.join(f'{v["date"]} {v["time"]} {v["band"]}MHz {v["call"]}={v.get("operator_name", "未割当")}' for v in rows))
    birth=ctx.get('declarations',{}).get('junior_birthdate','')
    if c.get('regional',{}).get('junior_since') and birth:extra.append('ジュニア部門 生年月日: '+birth)
    if e.get('regional',{}).get('cw_award') and ctx.get('station_type')=='individual':
        from contest_rules import score
        from copy import deepcopy
        from contest_normalization import working_values
        cw=[v for v in rows if working_values(e,v.get('band',''),v.get('mode',''),v.get('contest_band',''))[1]=='CW']
        if cw:
            subrule=deepcopy(rule);subcat=next(x for x in subrule['event']['categories'] if x['id']==c['id']);subcat['min_bands']=0;subcat['min_calls']=0
            result=score(subrule,cw,ctx)
            if result.total is not None and any(x.get('eligible') for x in result.rows):extra.append(f'電信部門: CWのみ {result.points}点 × {result.multi1}マルチ = {result.total}点（主催審査前）')
    if not extra:return info
    out=dict(info);out['comments']=' '.join([info.get('comments','')]+extra);return out
