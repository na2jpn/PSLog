"""Declarative entry qualifications; ages/dates are confirmed working inputs."""
from datetime import datetime
import math,re,unicodedata

def date_value(value):
    if not isinstance(value,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',value):raise ValueError('局免許年月日はYYYY-MM-DDで入力してください。')
    return datetime.strptime(value,'%Y-%m-%d').date()

def validate_qualification(q):
    if not isinstance(q,dict) or not q or set(q)-{'min_age','max_age','license_since','license_until','operators_max_age','age_output','license_output','yl_or_younger_than','reference_date','license_label'}:raise ValueError('参加資格の項目が不正です。')
    if 'license_label' in q and q['license_label'] not in ('初回局免許年月日','局免許年月日（再開局を含む）'):raise ValueError('免許日ラベルが不正です。')
    if ('yl_or_younger_than' in q)!=('reference_date' in q):raise ValueError('YL又は若年資格には年齢境界と基準日が必要です。')
    if 'yl_or_younger_than' in q:
        if type(q['yl_or_younger_than']) is not int or not 1<=q['yl_or_younger_than']<=150:raise ValueError('若年資格の年齢が不正です。')
        date_value(q['reference_date'])
    if 'age_output' in q and (q['age_output'] not in ('field','comments') or not {'min_age','max_age'}.intersection(q)):raise ValueError('年齢の出力先が不正です。')
    if 'license_output' in q and (q['license_output'] not in ('field','comments') or 'license_since' not in q):raise ValueError('局免許日の出力先が不正です。')
    for key in ('min_age','max_age','operators_max_age'):
        if key in q and (type(q[key]) is not int or not 0<=q[key]<=150):raise ValueError('年齢条件は0～150の整数です。')
    if q.get('min_age',0)>q.get('max_age',150):raise ValueError('年齢条件の上下限が逆です。')
    if ('license_since' in q)!=('license_until' in q):raise ValueError('局免許日の範囲は開始・終了を両方指定してください。')
    if 'license_since' in q and date_value(q['license_since'])>date_value(q['license_until']):raise ValueError('局免許日の範囲が逆です。')

def operators(text):
    result=[]
    for i,line in enumerate(unicodedata.normalize('NFKC',text).splitlines(),1):
        if not line.strip():continue
        parts=line.rsplit(' / ',1)
        if len(parts)!=2 or not re.fullmatch('[0-9]{1,3}',parts[1].strip()):raise ValueError(f'運用者 {i}行目は「コール又は氏名 / 年齢」で入力してください。')
        result.append(dict(name=parts[0].strip(),age=int(parts[1].strip())))
    return result

def operator_text(values):
    return ' '.join(f'{v["name"]} ({v["age"]}歳)' for v in values)

def check_qualification(category,ctx):
    q=category.get('qualification',{});problems=[]
    if 'yl_or_younger_than' in q:
        try:
            if ctx.get('qualification_basis')=='young':
                from contest_tagged_region import age_at
                if not 0<=age_at(ctx.get('birthdate'),q['reference_date'])<q['yl_or_younger_than']:raise ValueError('この種目の若年資格は規約年齢未満です。')
            elif ctx.get('qualification_basis')!='yl':raise ValueError('YL又は若年のどちらで参加するか選択してください。')
        except ValueError as ex:problems.append(str(ex))
    if 'min_age' in q or 'max_age' in q:
        age=ctx.get('age')
        if type(age) is not int or not q.get('min_age',0)<=age<=q.get('max_age',150):problems.append(f'運用時年齢を確認してください。条件: {q.get("min_age",0)}～{q.get("max_age",150)}歳')
    if 'license_since' in q:
        try:
            d=date_value(ctx.get('licensedate'))
            if not date_value(q['license_since'])<=d<=date_value(q['license_until']):raise ValueError('局免許年月日がニューカマーの対象期間外です。')
        except ValueError as ex:problems.append(str(ex))
    if 'operators_max_age' in q:
        values=ctx.get('operators')
        if not isinstance(values,list) or not 1<=len(values)<=1000:problems.append('全運用者のコール又は氏名と年齢を入力してください。')
        else:
            seen=set()
            for i,v in enumerate(values,1):
                if not isinstance(v,dict) or set(v)!={'name','age'}:problems.append(f'運用者 {i}の項目が不正です。');continue
                name=v['name'];age=v['age']
                if not isinstance(name,str) or not name.strip() or any(ord(c)<32 or c in '<>' for c in name):problems.append(f'運用者 {i}の名前が不正です。')
                elif name.strip().casefold() in seen:problems.append(f'運用者 {i}が重複しています。')
                else:seen.add(name.strip().casefold())
                if type(age) is not int or not 0<=age<=q['operators_max_age']:problems.append(f'運用者 {i}は{q["operators_max_age"]}歳以下という条件を満たしません。')
    return problems

def band_power(category,ctx,band):
    global_power=ctx.get('power');caps=category.get('power_by_band',{})
    if band not in caps:return global_power
    values=ctx.get('power_by_band',{})
    if not isinstance(values,dict):raise ValueError('バンド別最大電力が不正です。')
    value=values.get(band,global_power)
    if type(value) not in (int,float) or not math.isfinite(value) or value<=0:raise ValueError(band+'MHzの最大電力を入力してください。')
    if value>caps[band]:raise ValueError(f'{band}MHzは{caps[band]}W以下です。バンド別の実運用最大電力を確認してください。')
    if type(global_power) in (int,float) and value>global_power:raise ValueError('バンド別最大電力が全体の最大電力を超えています。')
    return value

def qualification_submission(category,ctx,info,format):
    """Ensure submitted qualifications match the ones used for eligibility."""
    from contest_export import clean
    q=category.get('qualification',{})
    if 'min_age' in q or 'max_age' in q:
        if q.get('age_output','field')=='field':
            if format!='JARL R2.1':raise ValueError('年齢欄を確実に出力するため、この種目はJARL R2.1を選択してください。')
            if clean(info.get('age',''),'年齢')!=str(ctx.get('age')):raise ValueError('提出年齢が参加条件で確認した年齢と一致しません。')
    if 'license_since' in q and q.get('license_output','field')=='field':
        if format!='JARL R2.1':raise ValueError('局免許年月日欄を出力するため、この種目はJARL R2.1を選択してください。')
        if clean(info.get('licensedate',''),'局免許年月日')!=ctx.get('licensedate'):raise ValueError('提出する局免許年月日が参加条件と一致しません。')
    if 'operators_max_age' in q:
        if clean(info.get('multioplist',''),'運用者一覧')!=clean(operator_text(ctx['operators']),'運用者一覧'):raise ValueError('運用者・年齢一覧が参加条件と一致しません。')

def submission_comments(rule,ctx,info):
    if ctx.get('submission_mode')=='checklog':return info
    category=next((c for c in rule.get('event',{}).get('categories',[]) if c['id']==ctx.get('category')),{})
    q=category.get('qualification',{});extra=[]
    if q.get('age_output')=='comments' or q.get('license_output')=='comments':
        problems=check_qualification(category,ctx)
        if problems:raise ValueError('\n'.join(problems))
        if q.get('age_output')=='comments':extra.append(f'運用者年齢: {ctx["age"]}歳')
        if q.get('license_output')=='comments':extra.append(f'{q.get("license_label","初回局免許年月日")}: {ctx["licensedate"]}')
    if 'yl_or_younger_than' in q:
        problems=check_qualification(category,ctx)
        if problems:raise ValueError('\n'.join(problems))
        extra.append('参加資格: 性別 女性（YL）' if ctx['qualification_basis']=='yl' else '参加資格: 生年月日 '+ctx['birthdate'])
    if category.get('operators_in_comments') or category.get('mo_operators_in_comments') and info.get('multiop') is True:
        from contest_export import clean
        text=clean(info.get('multioplist',''),'全運用者コール' if category.get('operator_list_format')=='calls' else '全運用者の姓名・無線従事者資格',True)
        if category.get('operator_list_format')=='calls':
            from model import validate_station
            calls=re.split(r'[,;、\s]+',text);validated=[validate_station(x,'') for x in calls]
            if len(set(validated))!=len(validated):raise ValueError('運用者のコールが重複しています。')
            extra.append('全運用者コール: '+', '.join(validated))
        else:extra.append('全運用者（姓名・無線従事者資格）: '+text)
    if not extra:return info
    out=dict(info);out['comments']=' '.join(x for x in [info.get('comments','').strip()]+extra if x);return out
