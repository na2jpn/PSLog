"""Submission-time category/stage validation and specialized scoring helpers.

Dates in entries are canonical JST. All annotations are transient copies;
original QSO files and transmitted serial numbers are never edited here.
"""
from datetime import datetime,timedelta
import math,re

MODES=('CW','SSB','FM','AM','RTTY','FT4','FT8','MSK144','Q65','USB','LSB')
SPECIALS=('none','wpx_prefix','grid_distance')

def grid_center(grid):
    if not isinstance(grid,str) or not re.fullmatch('[A-Ra-r]{2}[0-9]{2}',grid):
        raise ValueError('距離計算には有効な4桁GLが必要です（ZZ00は距離未確定）。')
    g=grid.upper();return (-90+(ord(g[1])-65)*10+int(g[3])+0.5,-180+(ord(g[0])-65)*20+int(g[2])*2+1)

def grid_distance(a,b):
    lat1,lon1=map(math.radians,grid_center(a));lat2,lon2=map(math.radians,grid_center(b))
    h=math.sin((lat2-lat1)/2)**2+math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2
    return 6371.0088*2*math.asin(math.sqrt(min(1,max(0,h))))

def wpx_prefix(call):
    c=call.strip().upper()
    if not re.fullmatch('[A-Z0-9]+(?:/[A-Z0-9]+)*',c):raise ValueError('プリフィックス判定用コールが不正です。')
    parts=[x for x in c.split('/') if x not in ('P','M','MM','AM','A','E','J','QRP')]
    def prefix(s):
        m=re.match(r'([A-Z0-9]*[0-9])',s)
        return m.group(1) if m else s[:2]+'0'
    if len(parts)==1:return prefix(parts[0])
    if len(parts)==2:
        base,portable=sorted(parts,key=len,reverse=True)
        if len(base)==len(portable):raise ValueError('移動プリフィックスを一意に判定できません。手動確認が必要です。')
        if portable.isdigit():return re.sub('[0-9]+$',portable,prefix(base))
        return prefix(portable)
    raise ValueError('複数の移動指定は手動確認が必要です。')

def lists(values,label,maximum=1000):
    if not isinstance(values,list) or len(values)>maximum or any(not isinstance(v,str) or not v.strip() for v in values) or len(set(values))!=len(values):raise ValueError(label+'は重複のない文字列配列です。')

def validate_event(e):
    from contest_rules import keys,number
    keys(e,set(('timezone','windows','categories','required_flags','duplicate_fields','prefer','special'))|set(e).intersection({'submission','exchange','band_modes','normalization','station_factor','entrant','awards','mode_groups','mode_confirmations','band_choices','operating_locations','power_by_operation','newcomer_claim','regional','rule_view'}),'大会条件')
    if 'rule_view' in e:
        view=e['rule_view']
        allowed={'participants','power','movement','call_method','counterparts','frequency','restrictions','exchange','repeat','submission_notes','submission_deadline','points_display','multipliers_display'}
        if not isinstance(view,dict) or not view or not set(view)<=allowed:
            raise ValueError('ルール表示データの項目が不正です。')
        for key,value in view.items():
            if not isinstance(value,str) or not value.strip() or len(value)>5000 or '\x00' in value:
                raise ValueError('ルール表示データは5000文字以内の文字列です。')
    for field in ('mode_groups','mode_confirmations'):
        if field in e:
            mapping=e[field]
            if not isinstance(mapping,dict) or not mapping or len(mapping)>1000:raise ValueError('モード別条件は対応表で指定してください。')
            for mode,value in mapping.items():
                if not isinstance(mode,str) or not re.fullmatch('[A-Z0-9_-]{1,40}',mode) or not isinstance(value,str) or not value.strip() or any(x in value for x in '\r\n\t'):raise ValueError('モード別条件の表記が不正です。')
    if 'mode_group' in e.get('duplicate_fields',[]) and not e.get('mode_groups'):raise ValueError('重複分類の対応表を指定してください。')
    if 'newcomer_claim' in e:
        from contest_newcomer import validate
        validate(e['newcomer_claim'],e)
    if 'power_by_operation' in e:
        from contest_operation_power import validate
        validate(e['power_by_operation'])
    if 'operating_locations' in e:
        from contest_locations import validate
        validate(e['operating_locations'])
    if 'entrant' in e:
        from contest_station import validate_entrant
        validate_entrant(e['entrant'])
    if 'station_factor' in e and e['station_factor']!='jarl_fd':raise ValueError('未対応の局種係数です。')
    if 'normalization' in e:
        from contest_normalization import validate
        validate(e['normalization'])
    if 'band_modes' in e:
        if not isinstance(e['band_modes'],dict) or not e['band_modes']:raise ValueError('バンド別モードが不正です。')
        for band,modes in e['band_modes'].items():
            if not isinstance(band,str) or not band:raise ValueError('バンドが不正です。')
            lists(modes,'バンド別モード')
    if 'exchange' in e:
        from contest_jarl import validate_exchange
        validate_exchange(e['exchange'])
    if 'awards' in e:
        from contest_awards import validate_awards
        validate_awards(e['awards'],e)
    if 'submission' in e:
        q=e['submission'];keys(q,set(('formats','zone','contest','instructions'))|set(q).intersection({'jarl_tx','required_fields','order','club_entry','allowed_zones','row_scope','band_labels'}),'提出条件');lists(q['formats'],'提出形式')
        if 'band_labels' in q:
            labels=q['band_labels'];bands={b for w in e['windows'] for b in w['bands']}
            if not isinstance(labels,dict) or not labels or not set(labels)<=bands:raise ValueError('提出バンド表記は大会対象バンドの対応表で指定してください。')
            if any(not isinstance(v,str) or not re.fullmatch(r'[0-9]+(?:\.[0-9]+)?(?:G|MHz|GHz)?',v) for v in labels.values()):raise ValueError('提出バンド表記が不正です。')
            if len({labels.get(b,b) for b in bands})!=len(bands):raise ValueError('提出表記で別の採点バンドを統合できません。')
        if 'allowed_zones' in q:
            lists(q['allowed_zones'],'提出時刻基準')
            if not q['allowed_zones'] or not set(q['allowed_zones'])<={'JST','UTC'} or q['zone'] not in q['allowed_zones']:raise ValueError('提出時刻基準の候補が不正です。')
        if 'row_scope' in q and q['row_scope'] not in ('all','category'):raise ValueError('提出行の範囲が不正です。')
        if 'club_entry' in q:
            from contest_club import validate as validate_club
            validate_club(q['club_entry'],e)
        if 'order' in q and q['order'] not in ('time','band_time'):raise ValueError('提出順が不正です。')
        if 'jarl_tx' in q and type(q['jarl_tx']) is not bool:raise ValueError('JARL系列出力の指定が不正です。')
        if 'required_fields' in q:
            lists(q['required_fields'],'提出必須項目')
            if not set(q['required_fields'])<= {'email','opplace','multioplist','licensedate','age'}:raise ValueError('未対応の提出必須項目です。')
        if not q['formats'] or not set(q['formats'])<= {'JARL R1.0','JARL R2.1','Cabrillo','zLog令和版CSV','所定様式PDF'} or q['zone'] not in ('JST','UTC') or not isinstance(q['contest'],str) or not isinstance(q['instructions'],str):raise ValueError('提出条件が不正です。')
    if e['timezone'] not in ('JST','UTC') or e['prefer'] not in ('first','cw','highest') or e['special'] not in SPECIALS:raise ValueError('未対応の大会条件です。')
    lists(e['required_flags'],'確認事項');lists(e['duplicate_fields'],'重複キー')
    if not {'call','band'}<=set(e['duplicate_fields']) or not set(e['duplicate_fields'])<= {'call','band','mode_family','mode_group','my_grid','his_grid','own'}:raise ValueError('重複キーが不正です。')
    if not isinstance(e['windows'],list) or not 1<=len(e['windows'])<=50:raise ValueError('開催区間は1～50件です。')
    for w in e['windows']:
        keys(w,('start','end','bands'),'開催区間');lists(w['bands'],'バンド')
        try:
            a=datetime.strptime(w['start'],'%Y-%m-%d %H:%M');b=datetime.strptime(w['end'],'%Y-%m-%d %H:%M')
            if a>=b:raise ValueError()
        except (TypeError,ValueError):raise ValueError('開催区間の日時が不正です。開始以上・終了未満で扱います。')
    if not isinstance(e['categories'],list) or not 1<=len(e['categories'])<=1000:raise ValueError('部門を指定してください。')
    if 'band_choices' in e:
        from contest_normalization import validate_choices
        validate_choices(e)
    seen=set();submission_codes=set()
    for c in e['categories']:
        keys(c,set(('id','name','bands','modes','max_power','min_bands','max_bands','min_calls','required_flags'))|set(c).intersection({'operator','eligible','timing','min_power_exclusive','required_mode_families','qualification','power_by_band','scoring_windows','excluded_band_subsets','sent_codes','participation','fallback_category','operation_bands','submission_code','station_types','operators_in_comments','mo_operators_in_comments','location_group','operator_list_format','regional'}),'部門')
        if 'operator_list_format' in c and (c['operator_list_format'] not in ('full','calls') or not (c.get('operators_in_comments') or c.get('mo_operators_in_comments'))):raise ValueError('運用者一覧の形式指定が不正です。')
        if 'location_group' in c and c['location_group'] not in e.get('operating_locations',{}).get('groups',{}):raise ValueError('部門の運用地グループが不正です。')
        if 'submission_code' in c:
            code=c['submission_code']
            if not isinstance(code,str) or not code.strip() or code!=code.strip() or len(code)>80 or any(ord(x)<32 or ord(x)==127 or x in '<>' for x in code):raise ValueError('提出部門コードが不正です。')
            try:code.encode('cp932')
            except UnicodeEncodeError:raise ValueError('提出部門コードはJARL出力の文字コードで表現してください。')
        if 'station_types' in c:
            lists(c['station_types'],'部門の局種')
            if not c['station_types'] or not set(c['station_types'])<=set(e.get('entrant',{}).get('station_types',[])):raise ValueError('部門の局種は大会の参加局種から指定してください。')
        if 'mo_operators_in_comments' in c and type(c['mo_operators_in_comments']) is not bool:raise ValueError('MO運用者の意見欄記載は真偽値です。')
        if 'operators_in_comments' in c and type(c['operators_in_comments']) is not bool:raise ValueError('運用者の意見欄記載は真偽値です。')
        if 'operation_bands' in c:
            lists(c['operation_bands'],'運用可能バンド')
            if not c['operation_bands'] or not set(c['bands'])<=set(c['operation_bands']):raise ValueError('採点バンドは運用可能バンドに含めてください。')
        if '*' in c['modes'] and (c['modes']!=['*'] or e.get('mode_groups') or 'mode_family' in e['duplicate_fields'] or c.get('required_mode_families')):raise ValueError('全許可モードはモード分類による部門・重複制限と併用できません。')
        if 'participation' in c:
            from contest_participation import validate
            validate(c['participation'])
        if 'fallback_category' in c and (c['fallback_category']==c['id'] or c['fallback_category'] not in {v['id'] for v in e['categories']}):raise ValueError('変更先の参加部門が不正です。')
        if 'excluded_band_subsets' in c:
            groups=c['excluded_band_subsets']
            if not isinstance(groups,list) or not 1<=len(groups)<=50:raise ValueError('除外するバンド構成は1～50件です。')
            for group in groups:
                lists(group,'除外バンド構成')
                if not group or not set(group)<=set(c['bands']):raise ValueError('除外バンド構成は部門内のバンドを指定してください。')
        if 'sent_codes' in c:
            lists(c['sent_codes'],'自局の地域番号',maximum=10000)
            if e.get('exchange',{}).get('kind') not in ('numbered_region','tagged_region','literal_region','postal_region') or not c['sent_codes'] or not set(c['sent_codes'])<=set(e['exchange']['codes']):raise ValueError('部門の自局番号は数字地域番号辞書から指定してください。')
        if 'scoring_windows' in c:
            from contest_timing import stamp
            periods=c['scoring_windows']
            if not isinstance(periods,list) or not 1<=len(periods)<=50:raise ValueError('種目の採点時間枠は1～50件です。')
            intervals=[]
            for w in periods:
                keys(w,('start','end'),'種目の採点時間枠');a,z=stamp(w['start']),stamp(w['end'])
                if a>=z or not any(stamp(v['start'])<=a<z<=stamp(v['end']) for v in e['windows']):raise ValueError('種目の採点時間枠は大会の開催区間内で指定してください。')
                intervals.append((a,z))
            intervals.sort()
            if any(z>a2 for (a,z),(a2,z2) in zip(intervals,intervals[1:])):raise ValueError('種目の採点時間枠が重複しています。')
        if 'qualification' in c:
            from contest_qualification import validate_qualification
            validate_qualification(c['qualification'])
        if 'power_by_band' in c:
            if not isinstance(c['power_by_band'],dict) or not c['power_by_band'] or not set(c['power_by_band'])<=set(c['bands']):raise ValueError('バンド別電力上限が不正です。')
            for value in c['power_by_band'].values():
                number(value,'バンド別電力')
                if value<=0:raise ValueError('バンド別上限は0より大きい値です。')
        if 'min_power_exclusive' in c:
            number(c['min_power_exclusive'],'電力下限')
            if c['max_power'] is not None:number(c['max_power'],'最大電力')
            if c['max_power'] is not None and c['min_power_exclusive']>=c['max_power']:raise ValueError('電力区分の下限と上限が矛盾しています。')
        if 'required_mode_families' in c:
            lists(c['required_mode_families'],'必要なモード分類')
            if not set(c['required_mode_families'])<= {'phone','cw','digital'}:raise ValueError('モード分類が不正です。')
        if 'eligible' in c:
            from contest_rules import condition
            condition(c['eligible'])
        if 'timing' in c:
            from contest_timing import validate_timing
            validate_timing(c['timing'])
        if 'operator' in c and c['operator'] not in ('SO','MO'):raise ValueError('運用者区分が不正です。')
        if not isinstance(c['id'],str) or not re.fullmatch('[A-Za-z0-9_-]{1,80}',c['id']) or c['id'] in seen or not isinstance(c['name'],str) or not c['name'].strip():raise ValueError('部門識別子・名称が不正です。')
        public=c.get('submission_code',c['id'])
        if e.get('regional',{}).get('profile')=='iburi':public=(public,c['name'])
        if public in submission_codes:raise ValueError('提出部門コードが重複しています。')
        submission_codes.add(public)
        seen.add(c['id'])
        for key in ('bands','modes','required_flags'):lists(c[key],key)
        if c['max_power'] is not None:number(c['max_power'],'最大電力')
        for key in ('min_bands','max_bands','min_calls'):
            if type(c[key]) is not int or not 0<=c[key]<=100000:raise ValueError('最低交信数・バンド数が不正です。')
        if c['min_bands']>c['max_bands']:raise ValueError('最低バンド数が上限を超えています。')

    from contest_regional import validate as validate_regional
    validate_regional(e)

def prepare(rule,entries,context):
    from contest_rules import family,matches
    e=rule['event'];ctx=context or {};problems=[];rows=[dict(x) for x in entries]
    if e.get('entrant',{}).get('station_types'):
        if ctx.get('station_type') not in e['entrant']['station_types']:problems.append('参加できる自局の局種を申告してください。社団局・特別局などの参加可否は大会規約に従います。')
    from contest_operation_power import check as check_operation_power
    try:check_operation_power(e,ctx)
    except ValueError as ex:problems.append(str(ex))
    if ctx.get('submission_mode','entry') not in ('entry','checklog'):return rows,['提出目的が不正です。'],None
    if ctx.get('submission_mode')=='checklog':
        from contest_normalization import working_values,mode_family
        for v in rows:
            try:v['band'],v['mode']=working_values(e,v.get('band',''),v.get('mode',''),v.get('contest_band',''))
            except ValueError as ex:v['_event_error']=str(ex)
            v['mode_family']=mode_family(e,v['mode']);v['_excluded_reason']='全体チェックログ';v['_whole_checklog']=True
        return rows,problems,{'_whole_checklog':True}
    if ctx.get('station_type') in e.get('entrant',{}).get('checklog_only_types',[]):problems.append('この局種は競技エントリーできません。提出目的を全体チェックログに変更してください。')
    category=next((c for c in e['categories'] if c['id']==ctx.get('category')),None)
    if category is None:return rows,['参加部門を選択してください。'],None
    category=dict(category)
    category['_extended_event']=e;category['_extended_context']=ctx;category['_extended_rule']=rule
    from contest_locations import check as check_location
    try:check_location(e,category,ctx)
    except ValueError as ex:problems.append(str(ex))
    if category.get('station_types') and ctx.get('station_type') not in category['station_types']:problems.append('自局の局種と参加部門が一致しません。個人局・社団局の種目を確認してください。')
    if e.get('station_factor')=='jarl_fd':
        from contest_station import factor
        if rule['multi2']['kind']!='off' or rule['formula']!='total' or rule['scoring']['bonus']!=0:problems.append('FD局種係数は第二マルチoff・全体積・加算点0のルールで指定してください。')
        try:category['_station_factor']=factor(ctx)
        except ValueError as ex:problems.append(str(ex))
    from contest_qualification import check_qualification,band_power
    problems.extend(check_qualification(category,ctx))
    from contest_regional import check_context
    problems.extend(check_context(e,category,ctx))
    power=ctx.get('power')
    if type(power) not in (int,float) or not math.isfinite(power) or power<=0 or (category['max_power'] is not None and power>category['max_power']):problems.append('実運用の最大電力を確認してください。部門上限: '+str(category['max_power'])+' W')
    elif 'min_power_exclusive' in category and power<=category['min_power_exclusive']:problems.append(f'この部門の最大電力は {category["min_power_exclusive"]} Wを超える必要があります。')
    flags=ctx.get('flags',{})
    from contest_confirmations import active_flags
    for flag in active_flags(e,category):
        if not isinstance(flags,dict) or flags.get(flag) is not True:problems.append('未確認: '+flag)
    windows=[(datetime.strptime(w['start'],'%Y-%m-%d %H:%M'),datetime.strptime(w['end'],'%Y-%m-%d %H:%M'),set(w['bands'])) for w in e['windows']]
    scoring_windows=[(datetime.strptime(w['start'],'%Y-%m-%d %H:%M'),datetime.strptime(w['end'],'%Y-%m-%d %H:%M')) for w in category.get('scoring_windows',[])]
    for i,v in enumerate(rows):
        try:
            dt=datetime.strptime(v.get('date','')+' '+v.get('time',''),'%Y-%m-%d %H:%M')
            if e['timezone']=='UTC':dt-=timedelta(hours=9)
            from contest_normalization import working_values,mode_family
            band,mode=working_values(e,v.get('band',''),v.get('mode',''),v.get('contest_band',''))
            v['band']=band;v['mode']=mode
            # Exact known modes or a whitespace-delimited submode, never a
            # substring match such as NOTFT8. Canonical log mode is untouched.
            base=mode.split()[0] if mode else ''
            v['mode_family']='digital' if rule['id']=='cq-vhf-digi' else mode_family(e,mode)
            if category['modes']==['*']:
                if len(set(rule['points'].values()))!=1:raise ValueError('全許可モードでは通常点を全分類で同じ値にしてください。')
                v['_uniform_mode_points']=rule['points']['cw']
            if not any(start<=dt<end and (not bands or band in bands) for start,end,bands in windows):
                if not ctx.get('calendar_advisory'):v['_excluded_reason']='開催時間・ステージ対象外';continue
                category.setdefault('_calendar_warnings',set()).add('指定した開催日時の外に交信があります。日時を確認してください（採点・出力は継続）。')
            v['_contest_time']=dt;v['_timing_scope']=True
            if category.get('operation_bands') and band not in category['operation_bands']:raise ValueError('参加部門で運用できないバンドです。採点から除くだけではこの部門へ参加できません。')
            if type(v.get('checklog',False)) is not bool:raise ValueError('チェックログ指定は真偽値です。')
            if v.get('checklog'):
                v['_excluded_reason']='明示チェックログ（提出行頭X）';continue
            if scoring_windows and not any(a<=dt<z for a,z in scoring_windows):
                if not ctx.get('calendar_advisory'):v['_excluded_reason']='種目の採点時間枠外';continue
                category.setdefault('_calendar_warnings',set()).add('種目の標準時間枠外の交信も含めて処理します。')
            if 'band_modes' in e and base not in e['band_modes'].get(band,[]):
                v['_excluded_reason']='大会のバンド別モード対象外';continue
            if band not in category['bands'] or (category['modes']!=['*'] and base not in category['modes']):
                v['_excluded_reason']='参加部門のバンド・モード対象外';continue
            if base in e.get('mode_confirmations',{}):
                mode_flag=e['mode_confirmations'][base]
                from contest_confirmations import show_confirmation
                if show_confirmation(mode_flag) and (not isinstance(flags,dict) or flags.get(mode_flag) is not True):raise ValueError('未確認: '+mode_flag)
            if e.get('mode_groups'):
                if base not in e['mode_groups']:raise ValueError('このモードの重複分類が未設定です。')
                v['mode_group']=e['mode_groups'][base]
            actual_band_power=band_power(category,ctx,band)
            if v.get('exchange') in e.get('regional',{}).get('missing_exchange',[]):
                v['_excluded_reason']='受信番号未取得（照合用に保持）';continue
            if 'exchange' in e:
                from contest_jarl import prepare_exchange
                prepare_exchange(e['exchange'],v,actual_band_power)
                if category.get('sent_codes') and v['_sent_region'] not in category['sent_codes']:raise ValueError('送信番号の運用地と参加部門の地域区分が一致しません。')
            if e.get('exchange',{}).get('kind')=='tagged_region':
                from contest_tagged_region import check_sent
                check_sent(e['exchange'],v)
                if category.get('qualification',{}).get('yl_or_younger_than'):
                    if v['_sent_tag']!=e['exchange']['operator_tag']:raise ValueError('YL/YM部門の送信番号にはYが必要です。')
                    if ctx.get('qualification_basis')=='yl' and v.get('operator_yl') is not True:raise ValueError('YL参加資格とY送信行の実運用者情報が一致しません。')
                    if ctx.get('qualification_basis')=='young' and v.get('operator_birthdate')!=ctx.get('birthdate'):raise ValueError('若年参加資格とY送信行の生年月日が一致しません。')
            from contest_regional_extended import prepare_row as extended_row
            extended_row(e,category,v,ctx)
            from contest_remaining9 import prepare_row as next_row
            next_row(e,category,v,ctx)
            from contest_international import prepare_row as international_row
            international_row(e,category,v,ctx)
            from contest_cq import prepare_row as cq_row
            cq_row(e,category,v,ctx)
            from contest_last6 import prepare_row as last_row
            last_row(e,category,v,ctx)
            from contest_final9 import prepare_row as final_row
            final_row(e,category,v,ctx)
            if 'eligible' in category and not matches(category['eligible'],v):
                v['_excluded_reason']='参加部門の交信相手条件対象外';continue
            if e.get('exchange',{}).get('kind')=='tagged_region':
                from contest_tagged_region import points
                points(e['exchange'],v)
            from contest_regional import prepare_row
            prepare_row(e,category,v,windows)
            if e['special']=='wpx_prefix':v['prefix']=v.get('prefix') or wpx_prefix(v['call'])
            if e['special']=='grid_distance':
                distance=grid_distance(v.get('my_grid'),v.get('his_grid'));v['_computed_points']=1+math.floor(distance/3000);v['_distance_km']=distance
            dup=[]
            for field in e['duplicate_fields']:
                value=v.get(field)
                if field=='call' and e.get('regional',{}).get('base_call_duplicates'):
                    from contest_regional import base_call
                    value=base_call(value)
                if value is None or not str(value).strip():raise ValueError('重複判定情報が未設定: '+field)
                dup.append(str(value).strip().upper())
            v['_duplicate_key']=tuple(dup)
        except (ValueError,TypeError,KeyError) as ex:v['_event_error']=str(ex);v['_excluded_reason']='大会条件未確定'
    if e.get('exchange',{}).get('kind')=='tagged_region' and category.get('operator')=='SO':
        names={v.get('operator_name','').strip() for v in rows if v.get('_sent_tag')==e['exchange']['operator_tag']}
        if len(names)>1:problems.append('SO部門でY送信の実運用者が複数指定されています。')
    from contest_timing import check_timing
    if e.get('exchange',{}).get('same_sent_region') or category.get('regional',{}).get('same_sent_region'):
        scopes={}
        for v in rows:
            if '_sent_region' in v:scopes.setdefault(v.get('_sent_region_scope','region'),set()).add(v.get('_postal_sent',v['_sent_region']))
        if any(len(regions)>1 for regions in scopes.values()):problems.append('同じ番号体系で送信地域が複数あります。移動範囲の条件と送信番号を確認してください。')
    if e.get('exchange',{}).get('parent_regions'):
        parents={v['_sent_parent'] for v in rows if v.get('_sent_parent')}
        if len(parents)>1:problems.append('低域の送信地域と高域の市郡区の所在地が一致しません。')
    timing_problems,category['_timing_summary']=check_timing(category,windows,rows,ctx)
    category['_timing_summary'].extend(sorted(category.get('_calendar_warnings',set())))
    problems.extend(timing_problems)
    if category.get('participation',{}).get('manual_claim'):
        from contest_participation import checked_ops
        try:
            ops=checked_ops(ctx);n=sum(o['qsos'] for o in ops);young=sum(o['qsos'] for o in ops if o['age']<=category['participation']['max_age'])
            category['_timing_summary'].append(f'本人申告の担当数: 若年{young}／全体{n}。参加資格は本人判断、原ログ件数との一致は強制しません。')
        except ValueError:pass
    if category.get('participation'):
        from contest_participation import check
        problems.extend(check(category,ctx,sum(bool(v.get('_timing_scope')) for v in rows)))
    if e['prefer']=='cw':
        for i,v in enumerate(rows):
            if v.get('_excluded_reason') or v.get('_event_error'):continue
            try:
                if not matches(rule['scoring']['eligible'],v):v['_excluded_reason']='採点対象外'
            except ValueError as ex:v['_event_error']=str(ex);v['_excluded_reason']='大会条件未確定'
        cw={v['_duplicate_key'] for v in rows if not v.get('_excluded_reason') and not v.get('_event_error') and v.get('mode','').upper()=='CW'}
        for v in rows:
            if not v.get('_excluded_reason') and v.get('mode','').upper()!='CW' and v.get('_duplicate_key') in cw:v['_excluded_reason']='同局・同バンドのCW交信を優先'
    if e['prefer']=='highest':
        from contest_regional import highest
        highest(rule,rows)
    return rows,problems,category

def finish(result,rows,category,problems):
    if category and category.get('_whole_checklog'):
        result.problems.extend(problems)
        if result.problems:result.total=None
        if not result.problems:result.total=0;result.multi2=1
        return result
    if category:
        if '_station_factor' in category:
            result.multi2=category['_station_factor']
            if result.total is not None:result.total=result.points*result.multi1*result.multi2
        # Include valid zero-point multiplier contacts, exclude DUP and rows
        # rejected by rule eligibility. Per-row flags are from the scorer.
        valid=[v for v,s in zip(rows,result.rows) if s.get('eligible')]
        from contest_regional import finish as finish_regional
        operated=[v for v in rows if v.get('_duplicate_key') and not v.get('_event_error') and (not v.get('_excluded_reason') or str(v['_excluded_reason']).startswith('同局・同バンドの高得点'))]
        finish_regional(category,valid,problems,operated)
        from contest_regional_extended import finish as extended_finish
        extended_finish(category.get('_extended_event',{}),category,rows,result,category.get('_extended_context',{}),problems)
        from contest_remaining9 import finish as next_finish
        next_finish(category.get('_extended_event',{}),category,rows,result,category.get('_extended_context',{}),problems)
        from contest_international import finish as international_finish
        international_finish(category.get('_extended_event',{}),category,rows,result,category.get('_extended_context',{}),problems)
        from contest_cq import finish as cq_finish,overlay as cq_overlay
        cq_finish(category.get('_extended_event',{}),category,rows,result,category.get('_extended_context',{}),problems)
        cq_overlay(category['_extended_rule'],category,rows,result,category.get('_extended_context',{}),problems)
        from contest_last6 import finish as last_finish
        last_finish(category.get('_extended_event',{}),category,rows,result,category.get('_extended_context',{}),problems)
        from contest_final9 import finish as final_finish
        final_finish(category.get('_extended_event',{}),category,rows,result,category.get('_extended_context',{}),problems)
        bands={v['band'] for v in valid};calls={v['call'].strip().upper() for v in valid}
        if not category['min_bands']<=len(bands)<=category['max_bands']:problems.append(f'有効交信バンド数 {len(bands)} は部門条件外です。')
        for group in category.get('excluded_band_subsets',[]):
            if bands and bands<=set(group):problems.append('このバンド構成だけでは選択した全帯種目に参加できません。HF・上位帯域などの該当種目を確認してください。')
        if len(calls)<category['min_calls']:problems.append(f'有効相手局数 {len(calls)} は最低 {category["min_calls"]} 局に届きません。')
        from contest_rules import family
        # Participation mode includes a complete duplicate QSO; a duplicate
        # does not erase the fact that telephone was also operated.
        modes={v.get('mode_family',family(v['mode'])) for v,s in zip(rows,result.rows) if s.get('points') is not None and not v.get('_excluded_reason') and not v.get('_event_error')}
        for mode in category.get('required_mode_families',[]):
            if mode not in modes:problems.append('参加部門に必要な交信モードがありません: '+{'phone':'電話','cw':'電信','digital':'デジタル'}[mode])
    result.problems.extend(problems)
    result.timing_summary=category.get('_timing_summary',[]) if category else []
    if result.problems:result.total=None
    return result
