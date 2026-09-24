"""Declared operator QSO counts; never infer ages, family, or missing QSOs."""
import re,unicodedata
HISTORY='参加中の全交信を対象ログに含め、重複・無得点を含む担当交信数を実運用記録で確認した'
ROLES=('', '子','父','母','祖父','祖母')

def validate(s):
    from contest_rules import keys
    keys(s,{'max_age','min_percent','family_pair'}|set(s).intersection({'manual_claim'}),'担当交信割合')
    if 'manual_claim' in s and type(s['manual_claim']) is not bool:raise ValueError('本人申告指定が不正です。')
    if type(s['max_age']) is not int or not 0<=s['max_age']<=150 or type(s['min_percent']) is not int or not 1<=s['min_percent']<=100 or type(s['family_pair']) is not bool:raise ValueError('担当交信割合の年齢・割合・家族指定が不正です。')

def parse(text):
    result=[]
    for line in unicodedata.normalize('NFKC',text).splitlines():
        if not line.strip():continue
        p=[x.strip() for x in line.split(' / ')]
        if len(p) not in (3,4) or not re.fullmatch('[0-9]{1,3}',p[1]) or not re.fullmatch('[0-9]{1,9}',p[2]):raise ValueError('担当者は「コール又は氏名 / 年齢 / 交信数 / 続柄」で入力してください。')
        result.append(dict(name=p[0],age=int(p[1]),qsos=int(p[2]),role=p[3] if len(p)==4 else ''))
    return result

def checked_ops(ctx):
    ops=ctx.get('qso_operators')
    if not isinstance(ops,list) or not 1<=len(ops)<=1000:raise ValueError('全担当者の年齢・担当交信数を入力してください。')
    seen=set()
    for o in ops:
        if not isinstance(o,dict) or set(o)!={'name','age','qsos','role'}:raise ValueError('担当者の入力項目が不正です。')
        n=o['name']
        if not isinstance(n,str) or not n.strip() or len(n)>200 or any(ord(c)<32 or c in '<>' for c in n) or n.strip().casefold() in seen:raise ValueError('担当者の名前が空欄・重複・不正です。')
        seen.add(n.strip().casefold())
        if type(o['age']) is not int or not 0<=o['age']<=150 or type(o['qsos']) is not int or not 0<=o['qsos']<=100000000 or o['role'] not in ROLES:raise ValueError('担当者の年齢・交信数・続柄が不正です。')
    return ops

def check(category,ctx,operation_count):
    s=category['participation'];errors=[]
    if s.get('manual_claim'):
        try:checked_ops(ctx)
        except (ValueError,TypeError) as ex:return [str(ex)]
        return []
    try:
        ops=checked_ops(ctx);total=sum(o['qsos'] for o in ops);young=sum(o['qsos'] for o in ops if o['age']<=s['max_age'])
        if not total or total!=operation_count:errors.append(f'担当交信数の合計{total}件と、開催中の対象ログ{operation_count}件が一致しません。全運用ログ・担当数を確認してください。')
        if young*100<total*s['min_percent']:errors.append(f'{s["max_age"]}歳以下の担当交信が{young}/{total}件で、{s["min_percent"]}％に届きません。')
        if category.get('operator')=='SO' and len(ops)!=1:errors.append('シングルオペは担当者1名で入力してください。')
        if not isinstance(ctx.get('flags'),dict) or ctx['flags'].get(HISTORY) is not True:errors.append('未確認: '+HISTORY)
        if s['family_pair']:
            children=[o for o in ops if o['role']=='子'];parents=[o for o in ops if o['role'] in ('父','母','祖父','祖母')]
            if len(ops)!=2 or len(children)!=1 or len(parents)!=1 or children[0]['age']>s['max_age']:errors.append('PMMKは20歳以下の子と、その父母又は祖父母の合計2名です。')
            from model import validate_station
            try:
                if not isinstance(ctx.get('child_call'),str):raise ValueError()
                validate_station(ctx['child_call'],'')
            except ValueError:errors.append('子のコールサインを入力してください。')
    except (ValueError,TypeError) as ex:errors.append(str(ex))
    return errors

def operator_text(ctx):return ' '.join(o['name'].strip() for o in checked_ops(ctx))

def submission_info(rule,ctx,info,own):
    if ctx.get('submission_mode')=='checklog':return info
    c=next((c for c in rule.get('event',{}).get('categories',[]) if c['id']==ctx.get('category')),{})
    if 'participation' not in c:return info
    ops=checked_ops(ctx);s=c['participation'];out=dict(info)
    if s['family_pair']:
        from model import validate_station
        child=validate_station(ctx.get('child_call',''),'')
        base=lambda call:re.sub(r'/(?:[0-9]|JD1|P)$','',call.upper())
        if base(child)!=base(own):raise ValueError('PMMKは子のコールサインのログで提出してください。')
    if c.get('operator')=='MO':
        names=operator_text(ctx)
        if info.get('multioplist','').strip() and info['multioplist'].strip()!=names:raise ValueError('提出する運用者一覧が担当交信数の担当者と一致しません。')
        out['multioplist']=names
    detail=' / '.join(f'{o["name"]} {o["age"]}歳 {o["qsos"]}交信'+(' '+o['role'] if o['role'] else '') for o in ops)
    if s['family_pair']:detail+=' / 子のコールサイン '+ctx['child_call']
    out['comments']=' '.join(x for x in [info.get('comments','').strip(),'担当交信: '+detail] if x)
    return out
