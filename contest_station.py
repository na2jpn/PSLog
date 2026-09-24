"""Declared operating circumstances; never infer FD class from a callsign."""
import re
A_CONFIRM='移動目的・既設設備/電源の条件・移動表記を確認し、途中で局種を切り替えていない'

def validate_entrant(spec):
    from contest_rules import keys
    keys(spec,set(('station_types','guest_policy'))|set(spec).intersection({'checklog_only_types'}),'参加局の条件')
    kinds=spec['station_types']
    if not isinstance(kinds,list) or any(not isinstance(k,str) or k not in ('individual','club','special') for k in kinds) or len(kinds)!=len(set(kinds)):raise ValueError('参加できる局種が不正です。')
    if 'checklog_only_types' in spec:
        values=spec['checklog_only_types']
        if not isinstance(values,list) or not values or any(not isinstance(x,str) for x in values) or len(values)!=len(set(values)) or not set(values)<=set(kinds):raise ValueError('チェックログ限定の局種が不正です。')
    if spec['guest_policy'] not in ('allowed','mo_only','forbidden'):raise ValueError('ゲスト運用の条件が不正です。')

def factor(context):
    c=context.get('fd_class')
    if c not in ('A','B','HOME'):raise ValueError('FD局種 A／B／ホームを選択してください。')
    if c=='A' and context.get('fd_confirmed') is not True:raise ValueError('FD局種Aの設備・電源・移動表記の条件を確認してください。')
    return 2 if c=='A' else 1

def check_submission(rule,context,info,own):
    from contest_export import clean
    from model import validate_station
    for k in ('portable','guest'):
        if type(info.get(k,False)) is not bool:raise ValueError('移動・ゲストの指定が不正です。')
    from contest_operation_power import check_submission as check_operation_submission
    check_operation_submission(rule.get('event',{}),context,info,own)
    entrant=rule.get('event',{}).get('entrant',{})
    if entrant.get('station_types') and context.get('station_type') not in entrant['station_types']:raise ValueError('この大会に参加できる自局の局種を確認してください。')
    if context.get('station_type') in entrant.get('checklog_only_types',[]) and context.get('submission_mode')!='checklog':raise ValueError('この局種はチェックログで提出してください。')
    guest=info.get('guest') or bool(str(info.get('opcall','')).strip())
    if guest:
        policy=entrant.get('guest_policy','allowed')
        if policy=='forbidden':raise ValueError('この大会はゲスト運用で参加できません。')
        category=next((c for c in rule.get('event',{}).get('categories',[]) if c['id']==context.get('category')), {})
        if policy=='mo_only' and context.get('submission_mode','entry')!='checklog' and category.get('operator')!='MO':raise ValueError('この大会のゲスト・補助者を伴う運用はマルチオペ部門です。')
    portable=info.get('portable',False) or bool(re.search(r'/(?:[0-9]|JD1|P)$',own.upper()))
    if portable and not clean(info.get('opplace',''),'運用地'):raise ValueError('移動運用の提出には運用地を入力してください。')
    if info.get('guest'):
        op=clean(info.get('opcall',''),'ゲストOPコール',True)
        validate_station(op,'')
    if rule.get('event',{}).get('station_factor')=='jarl_fd' and context.get('submission_mode','entry')!='checklog':
        n=factor(context)
        if info.get('fd') is not True:raise ValueError('FDの第二マルチをサマリーに出力してください。')
        if context['fd_class'] in ('A','B') and not clean(info.get('opplace',''),'運用地'):raise ValueError('FD移動局は具体的な運用地を入力してください。')
        if context['fd_class']=='A':
            if not re.search(r'/(?:[0-9]|JD1|P)$',own.upper()):raise ValueError('FD局種Aは移動表記付きの自局ログを選択してください。')
            supply=clean(info.get('powersupply',''),'使用電源',True)
            if supply in ('安定化電源','電源','DC','AC/DC'):raise ValueError('変換機器名だけでなく電池・発電機等の供給源を記載してください。')
        return n
