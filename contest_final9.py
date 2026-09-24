"""Final domestic profiles; transient calculation values, immutable source logs."""
import re
from decimal import Decimal,InvalidOperation
PROFILES={'kcwa','hyogo','hiroshima','shizuoka','shimane','iburi','toyama','qso_party'}

def clean_text(value,label):
    s=str(value or '').strip()
    if not s or len(s)>200 or any(ord(c)<32 or c in '<>' for c in s):raise ValueError(label+'を実交換記録から入力してください。')
    return s

def qrp_call(call):
    return re.search(r'/(?:QRP|Q|[0-9]Q)(?:/|$)',call.upper()) is not None

def without_qrp(call):return re.sub(r'/(?:QRP|Q)(?=/|$)','',re.sub(r'/([0-9])Q(?=/|$)',r'/\1',call.upper()))

def number(raw,codes):
    m=re.fullmatch(r'([A-Z]{2})([0-9]+)',str(raw or '').upper())
    if not m or m[1] not in codes or int(m[2])<1:raise ValueError('実交換のKCJ略称+正の連番を確認してください。再採番しません。')
    return m[1],int(m[2])

def prepare_row(e,c,v,ctx):
    kind=e.get('regional',{}).get('profile')
    if kind not in PROFILES:return
    d=ctx.get('declarations',{});local=e['regional'].get('local_a',[]);outside=e['regional'].get('local_b',[])
    if kind=='kcwa':
        from contest_last6 import rst
        if not domestic(v.get('country')):raise ValueError('KCWAは国内個人局との交信だけです。相手運用国を確認してください。')
        rst(v);own,_=number(v.get('sent'),local);region,_=number(v.get('exchange'),local)
        if own!=d.get('own_region','').upper():raise ValueError('送信略称と自局地域が異なります。')
        if v.get('other_station')!='individual':raise ValueError('KCWAの相手局は国内個人局であることを交信情報欄で確認してください。')
        v['area']=region;v['_computed_points']=1;return
    if kind=='shizuoka':
        from contest_last6 import rst
        rst(v);received=str(v.get('exchange','')).upper();sent=str(v.get('sent','')).upper();own=d.get('own_region','').upper();inside=c['id'].endswith('S')
        if own not in (local if inside else outside) or sent!=own:raise ValueError('静岡の実送信地域と部門が一致しません。')
        if received not in local+outside:raise ValueError('静岡の市区町略符号/県地域番号が不正です。')
        if not inside and received not in local:v['_excluded_reason']='県外同士は無得点';return
        own_qrp=d.get('qrp','').upper()=='YES';other_qrp=qrp_call(v['call']);v['call']=without_qrp(v['call']);v['area']=received
        high={'1200':3,'2400':5,'5600':10,'10G':20,'24000':20};v['_computed_points']=high.get(v['band'],(2 if own_qrp else 1)*(2 if other_qrp else 1));return
    if kind=='hyogo':
        from contest_last6 import rst
        rst(v);own=d.get('own_region','').upper();inside=c['id'].startswith('I-');sent=str(v.get('sent') or '').upper();raw=str(v.get('exchange') or '').upper()
        if own not in (local if inside else outside+['DX']) or sent!=('' if own=='DX' else own):raise ValueError('兵庫の送信地域と実送信番号・部門が一致しません。')
        if not raw:
            if not inside:v['_excluded_reason']='県外同士';return
            if not v.get('country') or str(v['country']).upper()=='JA':raise ValueError('番号なしの国外局の運用国・地域を確認してください。')
            v['_computed_points']=1;v['_regional_multi']=False;return
        if raw not in local+outside+['2701']:raise ValueError('兵庫の県内市郡区/県地域番号が不正です。')
        if not inside and raw not in local+['2701']:v['_excluded_reason']='県外同士';return
        v['_computed_points']=1;v['area']=raw
        if raw=='2701':v['_regional_multi']=False
        return
    if kind=='hiroshima':
        from contest_international import grid
        from contest_last6 import rst
        mode=v['mode'];ambiguous=mode in ('DSTAR','FREEDV','C4FM','DMR')
        if ambiguous:
            communication=v.get('communication','').lower()
            if communication not in ('phone','digital'):raise ValueError('音声かデータかを交信情報の通信区分で確認してください。')
            v['mode_family']=communication
        if mode in ('FT8','FT4','JT65','JT9','FREEDV'):
            if any(not re.fullmatch(r'[+-][0-9]{2}',str(v.get(k,''))) for k in ('rst_sent','rst_received')):raise ValueError('実交換dBレポートを確認してください。岡山FTのレポート省略は適用しません。')
        elif mode in ('CW','SSB','AM','FM','RTTY'):rst(v)
        else:
            for key in ('rst_sent','rst_received'):clean_text(v.get(key),'実レポート')
        sent=str(v.get('sent') or '').upper();own=d.get('own_region','').upper()
        if sent!=own or (own not in local if c['id'].startswith('N-') else not re.fullmatch('[A-R]{2}[0-9]{2}',own)):raise ValueError('広島の送信番号・県内外部門が一致しません。')
        raw=str(v.get('exchange') or '').upper()
        if raw in local:v['area']=raw;v['_computed_points']=5
        elif re.fullmatch('[A-R]{2}[0-9]{2}',raw):v['area']=raw;v['_computed_points']=1
        else:v['_excluded_reason']='受信地域番号不正（原記録保持）'
        return
    if kind=='shimane':return shimane_row(e,c,v,ctx)
    if kind=='iburi':return iburi_row(e,c,v,ctx)
    if kind=='toyama':return toyama_row(e,c,v,ctx)
    if kind=='qso_party':return party_row(e,c,v,ctx)

def finish(e,c,rows,result,ctx,problems):
    kind=e.get('regional',{}).get('profile');d=ctx.get('declarations',{})
    if kind=='kcwa':
        last={};seen={}
        for i,v in sorted(enumerate(rows),key=lambda p:(p[1].get('date',''),p[1].get('time',''),p[0])):
            if not v.get('_timing_scope'):continue
            try:
                _,n=number(v.get('sent'),e['regional']['local_a']);b=v['band']
                if n in seen.setdefault(b,set()) or n<last.get(b,0):problems.append(f'{i+1}行目: 帯域内の送信連番再使用/逆行。実番号を再採番せず確認してください。')
                seen[b].add(n);last[b]=n
            except ValueError as ex:problems.append(str(ex))
    elif kind=='hyogo':
        order=ctx.get('entry_categories',[]);n=d.get('submission_number')
        if n not in ('1','2') or c['id'] not in order or int(n)!=order.index(c['id'])+1:problems.append('提出番号1/2と、今回提出する種目の選択順が一致しません。')
    elif kind=='shizuoka':
        choice=d.get('qrp','').upper()
        if choice not in ('YES','NO'):problems.append('QRP申告はYES又はNOです。')
        if 'HP' in c['id'] and choice!='YES':problems.append('HF QRP部門はQRP申告が必要です。')
        if choice=='YES':
            low=set(c['bands'])&{'1.9','3.5','7','14','21','28','50','144','430'}
            for i,v in enumerate(rows):
                if not v.get('_timing_scope') or v['band'] not in low:continue
                try:
                    power=Decimal(str(v.get('qso_power') or ctx.get('power')))
                    if not power.is_finite() or not 0<power<=1 or not qrp_call(v.get('own','')):raise ValueError()
                except (ValueError,InvalidOperation):problems.append(f'{i+1}行目: 対象帯の全交信は1W以下・実際の自局/QRP表示が必要です。チェック指定でも除外しません。')
    elif kind=='shimane':shimane_finish(e,c,rows,result,ctx,problems)
    elif kind=='iburi':iburi_finish(e,c,rows,result,ctx,problems)
    elif kind=='toyama':toyama_finish(e,c,rows,result,ctx,problems)
    elif kind=='qso_party':party_finish(e,c,rows,result,ctx,problems)

def submission_info(rule,ctx,info):
    kind=rule.get('event',{}).get('regional',{}).get('profile');out=dict(info);d=ctx.get('declarations',{})
    if kind=='shizuoka':
        if not info.get('tel','').strip():raise ValueError('静岡の提出には電話番号が必要です。')
        out['equipment']=d.get('equipment','');out['comments']=' / '.join(x for x in [info.get('comments',''),'対象外バンドはチェック交信として0点・マルチなし。'] if x)
    if kind=='hyogo':out['_hyogo_second']=d.get('submission_number')=='2'
    if kind=='iburi':
        out['categoryname']=next((x['name'] for x in rule['event']['categories'] if x['id']==ctx.get('category')),'チェックログ')
        out['comments']=' / '.join([info.get('comments','')]+[d.get(k,'') for k in ('fixed_address','portable_address')])
    return out

def domestic(value):return str(value or '').upper() in ('JA','JAPAN','339','JD1','JD1-OGASAWARA','JD1-MINAMITORISHIMA')

def party_row(e,c,v,ctx):
    own=clean_text(ctx.get('declarations',{}).get('own_country'),'自局運用国')
    other=clean_text(v.get('country'),'相手運用国')
    for field in ('rst_sent','rst_received','sent','exchange'):clean_text(v.get(field),'実交換レポート/名前')
    v['_computed_points']=0;v['_regional_multi']=False
    if not domestic(own) and not domestic(other):v['_excluded_reason']='国外局同士は対象外'

def party_finish(e,c,rows,result,ctx,problems):
    from contest_regional import base_call
    calls={base_call(v['call']) for v,s in zip(rows,result.rows) if s.get('eligible')}
    result.party_stations=len(calls);result.total=Decimal(0)
    if len(calls)<20:problems.append(f'QSOパーティは完全な異なる20局が必要です（現在{len(calls)}局）。')

def shimane_row(e,c,v,ctx):
    from contest_last6 import rst
    rst(v);d=ctx.get('declarations',{});local=e['regional']['local_a'];out=e['regional']['local_b'];own=d.get('own_region','');received=str(v.get('exchange',''));inside=c['id'].startswith('1')
    if own not in (local if inside else out) or str(v.get('sent',''))!=own:raise ValueError('島根の自局部門と実送信地域を確認してください。')
    if not domestic(v.get('country')):v['_excluded_reason']='国内局のみ';return
    if received not in local+out:raise ValueError('島根の実受信市郡/県地域番号を確認してください。')
    if not inside and received not in local:v['_excluded_reason']='県外同士';return
    v['area']=received;v['_computed_points']=1
    if c.get('regional',{}).get('section')=='AJD':v['_computed_points']=0;v['_regional_multi']=False

def ajd_area(call):
    parts=without_qrp(call).split('/')
    if any(x in ('MM','AM') for x in parts):raise ValueError('AJD国内地上運用エリアを確認してください。')
    portable=[p for p in parts[1:] if re.fullmatch('[0-9]',p)]
    if portable:return portable[-1]
    m=re.search('[0-9]',parts[0])
    if not m:raise ValueError('AJD相手運用エリアをコールから確認できません。')
    return m[0]

def earliest_ajd(rows,results):
    from contest_regional import base_call
    edges={str(i):[] for i in range(10)}
    for i in sorted(range(len(rows)),key=lambda i:(rows[i]['date'],rows[i]['time'],i)):
        if not results[i].get('eligible'):continue
        v=rows[i];a=ajd_area(v['call']);edges[a].append((base_call(v['call']),i))
        matched={}
        def assign(area,seen):
            for call,index in edges[area]:
                if call in seen:continue
                seen.add(call)
                if call not in matched or assign(matched[call][0],seen):matched[call]=(area,index);return True
            return False
        if all(assign(a,set()) for a in edges):return sorted([x[1] for x in matched.values()],key=lambda j:(rows[j]['date'],rows[j]['time'],j))
    return []

def shimane_finish(e,c,rows,result,ctx,problems):
    d=ctx.get('declarations',{});section=c.get('regional',{}).get('section');bonus=d.get('bonus','').upper()
    if bonus not in ('YES','NO'):problems.append('移動加算の申告はYES又はNOです。')
    if section=='AJD':
        try:chosen=earliest_ajd(rows,result.rows)
        except ValueError as ex:problems.append(str(ex));chosen=[]
        result.total=Decimal(0);result.ajd_indexes=chosen;result.ajd_completion=rows[chosen[-1]]['time'] if chosen else ''
        if not chosen:problems.append('AJDは異なる国内10局で全10エリアを完成させる必要があります。')
        if bonus=='YES':problems.append('AJDに1000点加算はありません。')
    elif bonus=='YES':
        if not c['id'].startswith('1') or section not in ('HFH','HFL') or not re.fullmatch('[0-9]{4,5}',d.get('licensed_region','')) or d.get('own_region')==d.get('licensed_region') or not d.get('portable_equipment','').strip():problems.append('1000点は県内HF・設置市郡外・既設無線設備/電源不使用の場合だけです。')
        elif result.total is not None:result.total+=Decimal(1000);result.final_bonus=Decimal(1000)

def iburi_row(e,c,v,ctx):
    from contest_last6 import rst
    rst(v);d=ctx.get('declarations',{});where=v.get('own_location');inside=c['id'].startswith('I');local=e['regional']['local_a'];outside=e['regional']['local_b']
    if where not in ('fixed','portable'):raise ValueError('自局地点はfixed又はportableを交信ごとに指定してください。')
    own=d.get(where+'_region');sent=str(v.get('sent') or '');received=str(v.get('exchange') or '')
    if own not in (local if inside else outside) or sent!=own:raise ValueError('胆振日高の部門・自局地点・実送信番号が一致しません。')
    call=v.get('own','')
    if inside and ((where=='portable' and not call.endswith('/8')) or (where=='fixed' and '/' in call)):raise ValueError('管内の常置は基本コール、移動は同じ基本コール/8の実記録を選んでください。')
    if not domestic(v.get('country')):v['_excluded_reason']='国内局のみ';return
    if received not in local+outside:raise ValueError('胆振日高の市郡/県地域番号を確認してください。')
    if not inside and received not in local:v['_excluded_reason']='管外同士';return
    if received=='48':
        island=v.get('island')
        if island not in ('OG','MT'):raise ValueError('48の相手は小笠原OGか南鳥島MTかを別欄で確認してください。49/50を捏造しません。')
        v['area']=island
    else:v['area']=received
    v['_computed_points']=1

def iburi_finish(e,c,rows,result,ctx,problems):
    from contest_regional import base_call
    active=[v for v in rows if v.get('_timing_scope')];calls={v.get('own','') for v in active};d=ctx.get('declarations',{});places={v.get('own_location') for v in active}
    if len({base_call(x) for x in calls})>1:problems.append('2地点は同じ基本コールだけを統合できます。')
    if c['id'].startswith('O') and len(calls)>1:problems.append('2地点特例は管内参加だけです。')
    for p in places:
        if p in ('fixed','portable') and d.get(p+'_address') in (None,'','NONE'):problems.append('実際に運用した地点の住所を入力してください。')
    if len(places)>1 and d.get('fixed_address')==d.get('portable_address'):problems.append('同じ住所を別地点と申告できません。')
    if any(v.get('band') in ('3.8','3.8MHZ') for v in active):problems.append('3.8MHzは対象外です。3.5へ正規化しません。')

def toyama_row(e,c,v,ctx):
    d=ctx.get('declarations',{});local=e['regional']['local_a'];outside=e['regional']['local_b'];own=d.get('own_region');inside=own in local
    if own not in local+outside or (c['id'].startswith('I-') and not inside) or (c['id'].startswith('O-') and inside):raise ValueError('富山の実運用地と部門が一致しません。')
    for f in ('rst_sent','rst_received','sent','exchange'):clean_text(v.get(f),'実交換レポート・所在地・苗字')
    place=v.get('area')
    if place not in local+outside:raise ValueError('富山のマルチ用所在地を別欄で確認してください。原交換の自由文字列を変更しません。')
    if not domestic(v.get('country')):v['_excluded_reason']='国内局のみ';return
    if not inside and place not in local:v['_excluded_reason']='県外同士';return
    v['_computed_points']=1

def toyama_finish(e,c,rows,result,ctx,problems):
    if c['id']!='HANDY':return
    for i,v in enumerate(rows):
        if not v.get('_timing_scope'):continue
        try:
            p=Decimal(str(v.get('qso_power') or ctx.get('power')))
            if v['mode']!='FM' or not p.is_finite() or not 0<p<=5:raise ValueError()
        except (ValueError,InvalidOperation):problems.append(f'{i+1}行目: ハンディーはチェック指定を含む全交信FM・5W以下です。')
