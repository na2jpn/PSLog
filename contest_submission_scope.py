"""Optional category-specific export view; never delete source or zero-point QSOs."""
from datetime import datetime,timedelta
from sota_export import Selection
from contest_normalization import working_values
from contest_export import key

def select(selection,rule,draft,context):
    event=rule.get('event',{})
    if rule.get('id')=='shimane' and context.get('category') in ('1D','1H'):
        from contest import entries
        from contest_rules import score
        result=score(rule,entries(selection,draft),context)
        if not result.problems and getattr(result,'ajd_indexes',[]):return Selection(list(selection.sessions),[selection.rows[i] for i in result.ajd_indexes])
    if rule.get('id')=='shizuoka':
        # Keep all domestic bands, but the rule explicitly omits foreign QSOs.
        return Selection(list(selection.sessions),[row for row in selection.rows if str(draft.get(key(row),{}).get('country') or '').upper() in ('','JA','JAPAN','339','JD1','JD1-OGASAWARA','JD1-MINAMITORISHIMA')])
    if event.get('submission',{}).get('row_scope')!='category' or context.get('submission_mode')=='checklog':return selection
    category=next((c for c in event.get('categories',[]) if c['id']==context.get('category')),None)
    if category is None:return selection
    if rule.get('id')=='toyama_emergency':category=dict(category,bands=list(dict.fromkeys(b for w in event['windows'] for b in w['bands'])),modes=['*'])
    rows=[]
    for row in selection.rows:
        q=row[1]
        try:
            band,mode=working_values(event,q.band,q.mode,draft.get(key(row),{}).get('contest_band',''));base=mode.split()[0] if mode else ''
            stamp=datetime.strptime(q.date+' '+q.time,'%Y-%m-%d %H:%M')
            if event['timezone']=='UTC':stamp-=timedelta(hours=9)
            if not context.get('calendar_advisory') and not any(datetime.strptime(w['start'],'%Y-%m-%d %H:%M')<=stamp<datetime.strptime(w['end'],'%Y-%m-%d %H:%M') and (not w['bands'] or band in w['bands']) for w in event['windows']):continue
            if band not in category['bands'] or category['modes']!=['*'] and base not in category['modes']:continue
            if event.get('band_modes') and base not in event['band_modes'].get(band,[]):continue
            if not context.get('calendar_advisory') and category.get('scoring_windows') and not any(datetime.strptime(w['start'],'%Y-%m-%d %H:%M')<=stamp<datetime.strptime(w['end'],'%Y-%m-%d %H:%M') for w in category['scoring_windows']):continue
        except (TypeError,ValueError):pass  # Keep errors visible to normal validation.
        rows.append(row)
    return Selection(list(selection.sessions),rows)
