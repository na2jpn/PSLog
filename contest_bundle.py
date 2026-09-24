"""One Hiroshima WAS email-body file from independently verified categories."""
from contest_export import ContestPlan
from contest_regional import base_call

def item(rule,context,own,prepared):
    if rule.get('id')!='hiroshima_was' or prepared.encoding!='cp932':raise ValueError('提出セットの結合は広島WASのJARLテキスト用です。')
    c=next(c for c in rule['event']['categories'] if c['id']==context['category'])
    return dict(plan=prepared,category=c['id'],group=c.get('regional',{}).get('entry_group'),bands=list(c['bands']),expected=list(context.get('entry_categories',[])),own=base_call(own),year=rule['year'])

def combine(items):
    if not 1<=len(items)<=2:raise ValueError('広島WASは1部門又は単帯2部門です。')
    first=items[0];actual={x['category'] for x in items}
    if len(actual)!=len(items) or any(set(x['expected'])!=actual or x['own']!=first['own'] or x['year']!=first['year'] for x in items):raise ValueError('提出セットの部門・自局・年度が一致しません。選択した全部門を追加してください。')
    if len(items)==2 and (any(x['group']!='single' for x in items) or set(first['bands'])&set(items[1]['bands'])):raise ValueError('結合できるのは重ならない単帯2部門です。')
    sessions=[];guards=[];texts=[];warnings=[]
    for x in items:
        p=x['plan']
        for s in p.sessions:s.snapshot.check(s.path)
        for path,snap in p.guards:snap.check(path)
        sessions+=p.sessions;guards+=p.guards;texts.append(p.data.rstrip(b'\r\n'));warnings+=p.warnings
    return ContestPlan(sessions,guards,b'\r\n\r\n'.join(texts)+b'\r\n',first['own']+'_WAS_set.txt','cp932',sum(x['plan'].qsos for x in items),warnings+['この全体を1通のメール本文へ貼付してください。添付・分割不可。'])
