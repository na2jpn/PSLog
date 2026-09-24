"""Editable submission calendar, separate from immutable QSO timestamps."""
from copy import deepcopy
from datetime import datetime
FMT='%Y-%m-%d %H:%M'

def parse(text,event):
    lines=[x.strip() for x in text.splitlines() if x.strip()]
    if len(lines)!=len(event['windows']):raise ValueError('開催区間は規約と同じ行数で指定してください。各区間の日時は変更できます。')
    result=[]
    for line,w in zip(lines,event['windows']):
        parts=[x.strip() for x in line.split(' / ')]
        if len(parts)!=2:raise ValueError('日時は「YYYY-MM-DD HH:MM / YYYY-MM-DD HH:MM」で入力してください。')
        a,z=map(lambda x:datetime.strptime(x,FMT),parts)
        if a>=z:raise ValueError('開始日時は終了日時より前にしてください。')
        result.append(dict(start=a.strftime(FMT),end=z.strftime(FMT),bands=list(w['bands'])))
    return result

def working_rule(rule,ctx):
    if not rule.get('event') or not ctx or not ctx.get('calendar_windows') or rule.get('_calendar_applied'):return rule
    r=deepcopy(rule);e=r['event'];old=e['windows'];new=ctx['calendar_windows']
    new=parse('\n'.join(w['start']+' / '+w['end'] for w in new),e)
    for c in e['categories']:
        for w in c.get('scoring_windows',[]):
            for a,b in zip(old,new):
                if a['start']<=w['start']<w['end']<=a['end']:
                    if w['start']==a['start'] and w['end']==a['end']:w.update(start=b['start'],end=b['end'])
                    else:
                        delta=datetime.strptime(b['start'],FMT)-datetime.strptime(a['start'],FMT)
                        w.update(start=(datetime.strptime(w['start'],FMT)+delta).strftime(FMT),end=(datetime.strptime(w['end'],FMT)+delta).strftime(FMT))
                    break
    e['windows']=new;r['_calendar_applied']=True
    return r
