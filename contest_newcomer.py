"""Optional newcomer award declaration, separate from category and QSO scoring."""

def validate(spec,event):
    from contest_rules import keys
    from contest_qualification import date_value
    from contest_event import lists
    keys(spec,('name','license_since','license_until','operators','station_types'),'ニューカマー申告')
    if not isinstance(spec['name'],str) or not spec['name'].strip() or any(ord(c)<32 or c in '<>' for c in spec['name']):raise ValueError('ニューカマー申告の名称が不正です。')
    if date_value(spec['license_since'])>date_value(spec['license_until']):raise ValueError('ニューカマー対象期間が逆です。')
    lists(spec['operators'],'対象運用者区分');lists(spec['station_types'],'対象局種')
    if not spec['operators'] or not set(spec['operators'])<={'SO','MO'} or not spec['station_types'] or not set(spec['station_types'])<=set(event.get('entrant',{}).get('station_types',[])):raise ValueError('ニューカマー対象の区分が不正です。')

def check(event,category,ctx):
    spec=event.get('newcomer_claim')
    if not spec:return
    if type(ctx.get('newcomer_requested',False)) is not bool:raise ValueError('ニューカマー申告の指定は真偽値です。')
    if not ctx.get('newcomer_requested'):return
    if ctx.get('submission_mode')=='checklog' or category.get('operator') not in spec['operators'] or ctx.get('station_type') not in spec['station_types']:raise ValueError('この提出区分はニューカマー申告の対象外です。申告を解除してください。')
    if ctx.get('newcomer_first_license') is not True:raise ValueError('初開局であり再開局ではないことを確認してください。')
    from contest_qualification import date_value
    d=date_value(ctx.get('newcomer_licensedate'))
    if not date_value(spec['license_since'])<=d<=date_value(spec['license_until']):raise ValueError('初開局日がニューカマー対象期間外です。')

def submission_info(rule,ctx,info):
    event=rule.get('event',{});category=next((c for c in event.get('categories',[]) if c['id']==ctx.get('category')),{})
    check(event,category,ctx)
    if not event.get('newcomer_claim') or not ctx.get('newcomer_requested'):return info
    result=dict(info);statement=event['newcomer_claim']['name']+'を申告します（初開局日: '+ctx['newcomer_licensedate']+'、再開局ではありません）。'
    result['comments']=' '.join(x for x in (info.get('comments','').strip(),statement) if x);return result
