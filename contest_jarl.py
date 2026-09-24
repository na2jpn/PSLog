"""Explicit JARL regional exchange rules; not applied to arbitrary contests."""
import math,re

def validate_exchange(e):
    from contest_rules import keys
    from contest_event import lists
    if e.get('kind')=='postal_region':
        keys(e,('kind','codes','same_sent_region'),'郵便番号・市郡区規則');lists(e['codes'],'県外番号',10000)
        if type(e['same_sent_region']) is not bool or any(c not in ('LOCAL','OUT') and not re.fullmatch('[0-9]{4,6}',c) for c in e['codes']):raise ValueError('県外市郡区辞書が不正です。')
        return
    if e.get('kind')=='tagged_region':
        from contest_tagged_region import validate
        validate(e);return
    if e.get('kind')=='literal_region':
        keys(e,('kind','codes','same_sent_region','region_map'),'大会専用文字番号')
        codes=e['codes'];lists(codes,'大会専用番号',10000)
        if not codes or any(not re.fullmatch('[A-Z0-9]{1,8}',c) for c in codes) or type(e['same_sent_region']) is not bool:raise ValueError('大会専用文字番号が不正です。')
        m=e['region_map']
        if not isinstance(m,dict) or not set(m)<=set(codes) or any(not isinstance(v,str) or not re.fullmatch('[A-Z0-9]{1,8}',v) for v in m.values()):raise ValueError('大会専用番号のマルチ対応が不正です。')
        return
    if e.get('kind')=='numbered_region':
        keys(e,('kind','codes','same_sent_region'),'数字地域番号規則')
        codes=e['codes']
        if type(e['same_sent_region']) is not bool or not isinstance(codes,list) or not 1<=len(codes)<=10000 or any(not isinstance(c,str) or not re.fullmatch('[0-9]{2,6}',c) for c in codes) or len(set(codes))!=len(codes):raise ValueError('数字地域番号辞書が不正です。')
        return
    if e.get('kind')=='jarl_band_power':
        keys(e,set(('kind','same_sent_region','profiles'))|set(e).intersection({'parent_regions','same_sent_region_across_profiles'}),'バンド別交換番号規則')
        if 'same_sent_region_across_profiles' in e and type(e['same_sent_region_across_profiles']) is not bool:raise ValueError('プロファイル共通送信地域の指定が不正です。')
        if type(e['same_sent_region']) is not bool:raise ValueError('同一送信地域の指定が不正です。')
        if not isinstance(e['profiles'],list) or not 1<=len(e['profiles'])<=30:raise ValueError('交換番号プロファイルは1～30件です。')
        ids=set();bands=set()
        for p in e['profiles']:
            keys(p,set(('id','bands','codes','code_lengths','m_threshold','points'))|set(p).intersection({'power_letters'}),'交換番号プロファイル')
            if 'power_letters' in p:
                lists(p['power_letters'],'電力文字')
                if not p['power_letters'] or not set(p['power_letters'])<=set('HMLP'):raise ValueError('電力文字が不正です。')
            if not isinstance(p['id'],str) or not re.fullmatch('[a-z0-9_]{1,40}',p['id']) or p['id'] in ids:raise ValueError('交換番号プロファイルIDが不正です。')
            ids.add(p['id']);lists(p['bands'],'対象バンド')
            if not p['bands'] or bands.intersection(p['bands']):raise ValueError('交換番号の対象バンドが空か重複しています。')
            bands.update(p['bands'])
            lens=p['code_lengths']
            if not isinstance(lens,list) or not lens or any(type(n) is not int or not 2<=n<=6 for n in lens) or len(set(lens))!=len(lens):raise ValueError('番号桁数は2～6の重複しない整数です。')
            codes=p['codes']
            if not isinstance(codes,list) or not 1<=len(codes)<=10000 or any(not isinstance(c,str) or not re.fullmatch('[0-9]{2,6}',c) or len(c) not in lens for c in codes) or len(set(codes))!=len(codes):raise ValueError('地域番号辞書が不正です。')
            if type(p['m_threshold']) not in (int,float) or p['m_threshold'] not in (10,20):raise ValueError('Mの電力境界は10W又は20Wです。')
            if type(p['points']) not in (int,float) or not math.isfinite(p['points']) or p['points']<0:raise ValueError('交信得点が不正です。')
        if 'parent_regions' in e:
            parent=e['parent_regions'];allcodes={c for p in e['profiles'] for c in p['codes']};lowcodes={c for c in allcodes if len(c)<=3}
            if not isinstance(parent,dict) or not set(parent)<=allcodes or any(v not in lowcodes for v in parent.values()):raise ValueError('地域番号の親子対応が不正です。')
        return
    keys(e,('kind','regions','same_sent_region'),'交換番号規則')
    if e['kind']!='jarl_region_power' or type(e['same_sent_region']) is not bool:raise ValueError('未対応の交換番号規則です。')
    lists(e['regions'],'都府県地域番号')
    if not e['regions'] or any(not re.fullmatch('[0-9]{2,3}',r) for r in e['regions']):raise ValueError('都府県地域番号は2～3桁です。')

def prepare_exchange(spec,v,power):
    if spec['kind']=='postal_region':
        def decode(value):
            raw=str(value or '').strip()
            if re.fullmatch('[0-9]{7}',raw):return raw,'LOCAL'
            if raw in spec['codes'] and raw not in ('LOCAL','OUT'):return raw,'OUT'
            raise ValueError('県内は郵便番号7桁、県外は運用市郡区番号を入力してください。')
        received,kind=decode(v.get('exchange'));sent,ownkind=decode(v.get('sent'))
        if v.get('area') and str(v['area']).strip()!=received:raise ValueError('地域補助と実受信番号が一致しません。')
        v.update(area=received,_sent_region=ownkind,_sent_region_scope='postal',_postal_sent=sent)
        return
    if spec['kind']=='tagged_region':
        from contest_tagged_region import prepare
        prepare(spec,v);return
    if spec['kind'] in ('numbered_region','literal_region'):
        def decode(value,label):
            s=str(value or '').strip()
            if s not in spec['codes']:raise ValueError(label+'は大会専用辞書にある地域番号を入力してください（先頭0を保持）。')
            return s
        received=decode(v.get('exchange'),'受信番号');sent=decode(v.get('sent'),'送信番号')
        if v.get('area') and str(v['area']).strip()!=received:raise ValueError('補助入力の地域と受信ナンバーの地域が一致しません。')
        v.update(area=spec.get('region_map',{}).get(received,received),_sent_region=sent)
        return
    if spec['kind']=='jarl_band_power':
        p=next((p for p in spec['profiles'] if v['band'] in p['bands']),None)
        if p is None:raise ValueError('このバンドの交換番号規則が未設定です。')
        def decode(value,label):
            m=re.fullmatch('([0-9]{2,6})([HMLP])',str(value or '').strip().upper())
            if not m or m[2] not in p.get('power_letters',list('HMLP')) or len(m[1]) not in p['code_lengths'] or m[1] not in p['codes']:raise ValueError(label+'の地域番号・桁数・電力文字を確認してください。')
            return m[1],m[2]
        received,_=decode(v.get('exchange'),'受信番号');sent,letter=decode(v.get('sent'),'送信番号')
        if v.get('area') and str(v['area']).strip()!=received:raise ValueError('補助入力の地域と受信ナンバーの地域が一致しません。')
        if type(power) in (int,float) and math.isfinite(power) and power<={'H':100,'M':p['m_threshold'],'L':5,'P':0}[letter]:raise ValueError('送信番号の電力文字と申告した最大電力が矛盾しています。')
        v.update(area=received,_sent_region=sent,_sent_region_scope='shared' if spec.get('same_sent_region_across_profiles') else p['id'],_computed_points=p['points'])
        if 'parent_regions' in spec:
            v['_sent_parent']=sent if len(sent)<=3 else spec['parent_regions'].get(sent)
        return
    def decode(value,label):
        s=str(value or '').strip().upper();m=re.fullmatch('([0-9]{2,3})([HMLP])',s)
        if not m or m[1] not in spec['regions']:raise ValueError(label+'は有効な都府県地域番号＋H/M/L/Pを確認してください。')
        return m[1],m[2]
    received,_=decode(v.get('exchange'),'受信番号')
    sent,letter=decode(v.get('sent'),'送信番号')
    if v.get('area') and str(v['area']).strip()!=received:raise ValueError('補助入力の地域と受信ナンバーの地域が一致しません。')
    v['area']=received;v['_sent_region']=sent
    if type(power) in (int,float) and math.isfinite(power):
        threshold={'H':100,'M':20 if str(v['band'])=='50' else 10,'L':5,'P':0}[letter]
        if power<=threshold:raise ValueError('送信番号の電力文字と申告した最大電力が矛盾しています。')

def jarl_tx_ids(rule,category):
    ids=category.get('timing',{}).get('band_change',{}).get('tx_ids',[])
    if not ids:return []
    if not rule.get('event',{}).get('submission',{}).get('jarl_tx'):
        raise ValueError('この部門は送信系列の出力が必要です。JARL系列表記の指定がありません。')
    # PSLog's canonical working values are the numeric IDs. No automatic
    # renumbering of existing per-QSO identifiers during export.
    if len(ids)>2 or any(not re.fullmatch('[0-9]',x) for x in ids):
        raise ValueError('JARL出力の送信系列は異なる1桁数字を最大2種類指定してください。')
    return ids
