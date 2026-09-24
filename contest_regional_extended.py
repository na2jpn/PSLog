"""Validated extensions for the PSLOG101 remaining-28 batch.

All inputs are submission working data. No network lookup or original-log edits.
"""
import re
from itertools import combinations
from datetime import datetime

PROFILES={'kcwa','hyogo','hiroshima','shizuoka','shimane','iburi','toyama','qso_party','aadx','jarl_rtty','ww_digi','okayama_ft','miyazaki','ja0_serial','shiga','tsugaru','gunma','scalg','ishikari','ja8','mie','kanagawa_postal','saitama','cq_vhf','cq160','nara','kyoto','cq_ww','cq_ww_rtty','cq_wpx','cq_wpx_rtty'}

def validate(event):
    from contest_rules import keys
    from contest_event import lists
    s=event.get('regional',{})
    if 'profile' in s and (not isinstance(s['profile'],str) or s['profile'] not in PROFILES):raise ValueError('未対応の地域大会処理です。')
    for k in ('local_a','local_b','postal_codes','checklog_prefixes'):
        if k in s:lists(s[k],k,10000)
    if s.get('profile')=='shiga' and not s.get('local_codes'):raise ValueError('滋賀の地域辞書が必要です。')
    if s.get('profile')=='tsugaru' and (not s.get('local_a') or not s.get('local_b') or set(s['local_a'])&set(s['local_b'])):raise ValueError('津軽海峡の2区域辞書が不正です。')
    if s.get('profile')=='kanagawa_postal' and (not s.get('postal_codes') or any(not re.fullmatch('[0-9]{7}',v) for v in s['postal_codes'])):raise ValueError('郵便番号辞書が不正です。')
    if 'missing_exchange' in s and (not isinstance(s['missing_exchange'],list) or not set(s['missing_exchange'])<={'?','--'}):raise ValueError('未取得番号の表記が不正です。')
    if any(not re.fullmatch('[A-Z0-9]{1,8}',v) for v in s.get('checklog_prefixes',[])):raise ValueError('チェックログの接頭辞が不正です。')
    for c in event['categories']:
        x=c.get('regional',{})
        for key in ('selected_bands','operator_assignments','half_only'):
            if key in x and type(x[key]) is not bool:raise ValueError('種目の追加指定は真偽値です。')
        if 'entry_group' in x and (not isinstance(x['entry_group'],str) or not x['entry_group']):raise ValueError('提出グループが不正です。')
        if 'band_minima' in x and (not isinstance(x['band_minima'],list) or len(x['band_minima'])>30):raise ValueError('帯域群の最低数は30件以下の配列です。')
        for group in x.get('band_minima',[]):
            keys(group,('bands','min'),'帯域群最低数');lists(group['bands'],'帯域群')
            if not set(group['bands'])<=set(c['bands']) or type(group['min']) is not int or not 1<=group['min']<=len(group['bands']):raise ValueError('帯域群の最低数が不正です。')
        for k in ('birthdate_output','age_output','license_output'):
            if k in x and type(x[k]) is not bool:raise ValueError('資格の出力指定は真偽値です。')

def bands_value(value):
    return [v for v in re.split(r'[,、\s]+',str(value).strip()) if v]

def check_context(e,c,ctx):
    x=c.get('regional',{});d=ctx.get('declarations',{});errors=[]
    if e.get('regional',{}).get('profile')=='scalg':
        try:
            acquired=d.get('cw_license','')
            if c['id']=='5':
                when=datetime.strptime(acquired,'%Y-%m-%d').date()
                if not datetime(2025,7,21).date()<=when<=datetime(2026,7,20).date():raise ValueError('ビギナーのCW従免初取得日は2025-07-21～2026-07-20です。')
                birth=datetime.strptime(d.get('beginner_birthdate',''),'%Y-%m-%d').date()
                if birth>when:raise ValueError('生年月日と初取得日が矛盾しています。')
            elif not re.fullmatch(r'(?:19|20)\d{2}',acquired) or not 1900<=int(acquired)<=2026:raise ValueError('CW従免初取得年は確認した西暦4桁を入力してください。')
            if c['id']=='6' and (not re.fullmatch(r'\d{4}',d.get('senior_birthyear','')) or 2026-int(d['senior_birthyear']) not in (ctx.get('age'),ctx.get('age',0)+1)):raise ValueError('シニアの生年と参加時の年齢を確認してください。')
        except ValueError as ex:errors.append(str(ex))
    if d.get('om_birthdate') and c['id'] in ('YO','4O','GO'):
        try:
            from contest_tagged_region import age_at
            age=age_at(d['om_birthdate'],'2026-05-31')
            if age<70 or age!=ctx.get('age'):raise ValueError('OMの生年月日と5月31日時点の70歳以上という年齢申告が一致しません。')
        except ValueError as ex:errors.append(str(ex))
    if 'junior_birth' in x.get('required_declarations',[]):
        try:
            from contest_tagged_region import age_at
            age=age_at(d['junior_birth'],'2026-09-12')
            if not 0<=age<=18 or age!=ctx.get('age'):raise ValueError('秋田ジュニアの生年月日と開始時年齢が一致しません。')
        except ValueError as ex:errors.append(str(ex))
    if x.get('selected_bands'):
        bands=bands_value(d.get('scoring_bands',''))
        if len(bands)!=3 or len(set(bands))!=3 or not set(bands)<=set(c['bands']):errors.append('採点する異なる3バンドをMHz表記で指定してください（例 7, 50, 144）。')
    if x.get('half_only') and d.get('half_date') not in {w['start'][:10] for w in e['windows']}:errors.append('ハーフは運用した一方の日付をYYYY-MM-DDで指定してください。')
    policy=e.get('regional',{}).get('entry_set',{})
    if policy.get('kind') not in ('singles_up','modes_disjoint','akita'):return errors
    cats={x['id']:x for x in e['categories']};selected=[cats[k] for k in ctx.get('entry_categories',[]) if k in cats]
    for a,b in combinations(selected,2):
        ga=a.get('regional',{}).get('entry_group');gb=b.get('regional',{}).get('entry_group')
        if policy['kind']=='singles_up' and {ga,gb}!={'single','up'}:errors.append('併願は通常単帯1種目と1200MHz以上1種目だけです。')
        if policy['kind']=='modes_disjoint' and (ga=='exclusive' or gb=='exclusive' or set(a['bands'])&set(b['bands']) and set(a['modes'])&set(b['modes'])):errors.append('同じ交信を重ねる提出、又はOM/MOと他種目の併願はできません。')
        if policy['kind']=='akita':
            if ga==gb:errors.append('同一種目名称の電信電話・電話の併願はできません。')
            # The original does not settle allowed-vs-actual band sets. Clear
            # non-overlap is accepted; ambiguous cases require the declared
            # interpretation and BOTH actual submission band lists.
            if len(a['bands'])>1 and len(b['bands'])>1 and set(a['bands'])&set(b['bands']):
                raw=d.get('entry_band_sets','');mapping={}
                try:
                    for part in raw.split(';'):
                        k,v=part.strip().split('=',1);mapping[k]=set(bands_value(v))
                    aa=mapping[a['id']];bb=mapping[b['id']]
                    if aa & bb:errors.append('申告したマルチ2種目の使用バンドが重複しています（規約の禁止組み合わせ）。')
                    if not aa or not bb or not aa<=set(a['bands']) or not bb<=set(b['bands']) or aa&bb:raise ValueError()
                    # No mandatory proof of an interpretation absent from the rule.
                except (KeyError,ValueError):pass  # Unspecified band-set interpretation is left to the entrant.
    return errors

def prepare_row(e,c,v,ctx):
    s=e.get('regional',{});x=c.get('regional',{});d=ctx.get('declarations',{});p=s.get('profile');raw=v.get('exchange','');sent=v.get('_sent_region','')
    if s.get('checklog_prefixes') and str(v.get('own','')).upper().startswith(tuple(s['checklog_prefixes'])):raise ValueError('この自局コールは全体チェックログで提出してください。')
    if p=='scalg':
        acquired=d.get('cw_license','')
        if len(acquired)<4 or sent!=acquired[:4][-2:]:raise ValueError('実送信番号と申告したCW従免初取得年が一致しません。原記録を確認してください。')
    if x.get('selected_bands') and v['band'] not in bands_value(d.get('scoring_bands','')):v['_excluded_reason']='選択した3バンドの採点対象外'
    if p=='shiga':
        from contest_regional import base_call
        v['_computed_points']=6 if base_call(v['call'])=='JL3ZKV' else 5 if raw in s['local_codes'] else 1
    if p=='tsugaru':
        a=s['local_a'];b=s['local_b'];own=0 if sent in a else 1 if sent in b else 2;his=0 if raw in a else 1 if raw in b else 2
        v['_computed_points']=1 if own==2 or his==2 else 2 if own==his else 3
        v['_sent_region_scope']='region';v['_sent_region']=str(own)
    if p=='ja8':v['_sent_region']=sent[:-1]
    if p=='mie':v['_sent_region']=re.sub(r'^\d+','',sent) or 'OUT'
    if p=='ja0_serial':
        from contest_regional import base_call
        def inside(call):
            base=base_call(call);m=re.search(r'\d(?=[A-Z]+$)',base)
            return bool(m and m[0]=='0') or '0' in str(call).upper().split('/')[1:]
        own=v.get('own','');base=base_call(v['call']);hit=inside(v['call'])
        v['_computed_points']=3 if hit else 1
        if inside(own):v['area']=re.match(r'[A-Z0-9]*[0-9]',base)[0]
        else:v['area']=base[1]+'_'+base[-1];v['_regional_multi']=hit
    if p=='ishikari' and (sent=='01006' or raw=='01006'):
        # Abuta county straddles branch areas. Never infer branch from 01006.
        if not d.get('abuta_locality','').strip():raise ValueError('01006は後志と胆振にまたがります。送受信の該当局・町村と後志所属の確認を申告してください。')
    if p=='kanagawa_postal':
        if sent=='OUT' and len(raw)!=7:v['_excluded_reason']='県外同士の交信は対象外'
        actual_sent=v.get('_postal_sent','')
        if len(raw)==7 and raw not in s['postal_codes'] or len(actual_sent)==7 and actual_sent not in s['postal_codes']:
            if not d.get('postal_confirmation','').strip():raise ValueError('参照表未収録の郵便番号です。神奈川県内の地名と確認根拠を申告してください。未収録だけで無効にはしません。')

def finish(e,c,rows,result,ctx,errors):
    x=c.get('regional',{});d=ctx.get('declarations',{});p=e.get('regional',{}).get('profile')
    valid=[v for v,s in zip(rows,result.rows) if s.get('eligible')];bands={v['band'] for v in valid}
    for group in x.get('band_minima',[]):
        if len(bands&set(group['bands']))<group['min']:errors.append('必要な帯域群の交信不足: '+','.join(group['bands'])+f' のうち{group["min"]}バンド以上')
    if x.get('half_only'):
        dates={v['_contest_time'].strftime('%Y-%m-%d') for v in rows if v.get('_timing_scope')}
        if dates!={d.get('half_date')}:errors.append('ハーフは運用自体を片側に限定します。チェック行を含め両日運用したログは不可です。')
    if x.get('selected_bands') and bands!=set(bands_value(d.get('scoring_bands',''))):errors.append('選択した3バンドそれぞれに有効交信が必要です。')
    if x.get('operator_assignments'):
        operated=[v for v in rows if v.get('_timing_scope')]
        if not operated or any(not v.get('operator_name','').strip() for v in operated):errors.append('開催中の全交信について実運用者を交信情報画面で指定してください。')
        if c.get('participation'):
            from collections import Counter
            actual=Counter(v.get('operator_name','').strip() for v in operated)
            declared={o['name'].strip():o['qsos'] for o in ctx.get('qso_operators',[])}
            if dict(actual)!=declared:errors.append('QSOごとの担当者と、担当交信数の申告が一致しません。')
    if p=='shiga' and c['id'].startswith('O'):
        n=len({v['band'] for v in valid if v.get('exchange') in e['regional']['local_codes']});result.multi2=n
        if result.total is not None:result.total=result.points*result.multi1*n
    if p=='gunma':
        modes={v['mode_family'] for v in rows if v.get('_duplicate_key') and not v.get('_event_error') and not v.get('_excluded_reason')}
        code=c['id'];target=code
        if len(code)>2 and code[1]=='C' and modes in ({'cw'},{'phone'}):target=code[0]+('A' if modes=={'cw'} else 'B')+code[2:]
        if len(code)==2 and code[1] in 'DEFGHIJKL':
            m='cw' if code[1] in 'DEF' else 'phone' if code[1] in 'GHI' else next(iter(modes)) if len(modes)==1 else 'mixed'
            scope=0 if any(float(b.replace('G','000'))<30 for b in bands) and any(float(b.replace('G','000'))>=30 for b in bands) else 1 if bands and all(float(b.replace('G','000'))<30 for b in bands) else 2
            target=code[0]+{'cw':'DEF','phone':'GHI','mixed':'JKL'}[m][scope]
        if target!=code:errors.append(f'運用実績による集計部門は {target} です。申告部門 {code} から変更して確認してください（自動変更しません）。')
    policy=e.get('regional',{}).get('entry_set',{})
    if policy.get('kind')=='akita' and len(ctx.get('entry_categories',[]))>1:
        c.setdefault('_timing_summary',[]).append('秋田の併願は2種目まで。規約の禁止3条件を確認してください。未明示の判定根拠入力は必須にしません。')
        cats={v['id']:v for v in e['categories']}
        for ident in ctx['entry_categories']:
            other=cats.get(ident,{})
            if ident!=c['id'] and len(c['bands'])>1 and len(bands)==1 and set(other.get('bands',[]))==bands:errors.append('1バンドのみのマルチと、そのシングル種目の併願はできません。')
        if d.get('entry_band_sets'):
            mapping=dict(part.strip().split('=',1) for part in d['entry_band_sets'].split(';') if '=' in part)
            if c['id'] in mapping and bands!=set(bands_value(mapping[c['id']])):errors.append('現在の提出実バンド集合と併願用の申告集合が一致しません。')

def submission_info(rule,ctx,info,rows):
    if ctx.get('submission_mode')=='checklog':
        if rule.get('event',{}).get('regional',{}).get('profile')!='scalg':return info
        from contest_regional import submission_info as original_info
        context=dict(ctx,submission_mode='entry')
        if not any(c['id']==ctx.get('category') for c in rule['event']['categories']):raise ValueError('チェックログ8でも運用時の該当部門を選び、必須事項を入力してください。')
        out=original_info(rule,context,info,rows)
        return submission_info(rule,context,out,rows)
    e=rule['event'];c=next(v for v in e['categories'] if v['id']==ctx['category']);x=c.get('regional',{});p=e.get('regional',{}).get('profile');d=ctx.get('declarations',{});extra=[]
    for ident in ('abuta_locality','postal_confirmation','entry_band_sets','entry_basis','youth_denominator','area_basis','kj_history','actual_location'):
        if ident in e.get('regional',{}).get('declarations',{}) and d.get(ident,'').strip():extra.append(e['regional']['declarations'][ident]+': '+d[ident])
    if x.get('operator_assignments'):extra.append('交信担当: '+'; '.join(f'{v["date"]} {v["time"]} {v["band"]} {v["call"]}={v.get("operator_name", "未割当")}' for v in rows))
    if p=='kanagawa_postal' or x.get('selected_bands'):
        from contest_rules import score
        result=score(rule,rows,ctx)
        excluded=sorted({v['band'] for v,z in zip(rows,result.rows) if z.get('reason') in ('参加部門のバンド・モード対象外','選択した3バンドの採点対象外')})
        if excluded:extra.append('採点対象外のチェックバンド: '+', '.join(excluded)+' MHz（交信行は保持・0点）')
    if p=='shiga' and c['id'].startswith('O'):
        from contest_rules import score
        s=score(rule,rows,ctx);extra.append(f'得点計算: {s.points}点 × {s.multi1}地域マルチ × 滋賀交信バンド係数{s.multi2} = {s.total}（審査前、FD係数ではありません）')
    if p=='scalg':
        from contest_rules import score
        s=score(rule,rows,ctx)
        extra.append(f'3 交信局数{len({v["call"] for v,z in zip(rows,s.rows) if z.get("eligible")})}局・{s.points}点・{s.multi1}マルチ・総得点{s.total}')
        if ctx.get('station_type')=='club' and not str(info.get('opcall','')).strip():raise ValueError('5 社団SOの実運用者個人コールを入力してください。')
    if x.get('birthdate_output'):extra.append('生年月日: '+ctx.get('birthdate',''))
    if extra:info=dict(info,comments=' '.join([info.get('comments','')]+extra))
    return info
