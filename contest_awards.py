"""Optional contest award requests; independent of the entered scoring band.

Only an explicitly selected, verified request is appended to a submission copy.
The source log and the user's comments are never overwritten.
"""
from copy import deepcopy
import re

def validate_awards(spec,event):
    from contest_rules import keys
    from contest_event import lists
    if not isinstance(spec,list) or not 1<=len(spec)<=20:raise ValueError('大会内アワードは1～20件です。')
    if event.get('exchange',{}).get('kind')!='numbered_region':raise ValueError('大会内アワードには数字地域番号辞書が必要です。')
    ids=set();codes=set(event['exchange']['codes'])
    for a in spec:
        keys(a,('id','name','groups'),'大会内アワード')
        if not isinstance(a['id'],str) or not re.fullmatch('[a-z][a-z0-9_]{0,39}',a['id']) or a['id'] in ids:raise ValueError('アワードIDが不正または重複しています。')
        ids.add(a['id'])
        if not isinstance(a['name'],str) or not a['name'].strip() or any(c in a['name'] for c in '\r\n\t<>'):raise ValueError('アワード名が不正です。')
        if not isinstance(a['groups'],list) or not 1<=len(a['groups'])<=20:raise ValueError('達成条件のグループが不正です。')
        for g in a['groups']:
            keys(g,('codes','min_count'),'達成条件');lists(g['codes'],'対象番号')
            if not set(g['codes'])<=codes or type(g['min_count']) is not int or not 1<=g['min_count']<=len(g['codes']):raise ValueError('達成条件の番号・必要数が不正です。')

def candidates(rule,entries,context):
    from contest_rules import score
    spec=rule.get('event',{}).get('awards',[])
    if not spec:return []
    # A single-band entry may earn an award using other valid contest bands.
    # Keep declared home region, allowed mode and operator eligibility intact.
    r=deepcopy(rule);e=r['event'];category=next((c for c in e['categories'] if c['id']==context.get('category')),None)
    problems=[];codes=set()
    if context.get('submission_mode')=='checklog' or category is None:problems=['エントリーする参加部門を選択してください。']
    else:
        category['bands']=list(dict.fromkeys(b for w in e['windows'] for b in w['bands'] if not category.get('operation_bands') or b in category['operation_bands']));category['min_bands']=1;category['max_bands']=len(category['bands'])
        result=score(r,entries,context);problems=result.problems
        if not problems:codes={code for row in result.rows if row.get('eligible') for code in row.get('multiplier_values',[])}
    output=[]
    for a in spec:
        counts=[len(codes.intersection(g['codes'])) for g in a['groups']]
        output.append(dict(id=a['id'],name=a['name'],eligible=not problems and all(n>=g['min_count'] for n,g in zip(counts,a['groups'])),counts=counts,required=[g['min_count'] for g in a['groups']],problems=problems))
    return output

def submission_info(rule,entries,context,info):
    requested=info.get('award_requests',[])
    if not isinstance(requested,list) or any(not isinstance(x,str) for x in requested) or len(set(requested))!=len(requested):raise ValueError('アワード申請の指定が不正です。')
    if not requested:return info
    available={a['id']:a for a in candidates(rule,entries,context)}
    result=dict(info);sentences=[]
    for ident in requested:
        a=available.get(ident)
        if a is None or not a['eligible']:raise ValueError('選択したアワードの達成条件を確認できません。対象ログ・番号・申請選択を再確認してください。')
        sentences.append(a['name']+'を申請します。')
    comments=str(info.get('comments','')).strip()
    result['comments']=' '.join(([comments] if comments else [])+sentences)
    return result
