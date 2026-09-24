from rule_view_verified_remaining71 import apply as apply_remaining_view
"""PSLOG101: explicitly authored 2026 regional definitions and preserved sources.

Run from any directory; sources are never rewritten. Each build validates its
schema and emits a standalone rule pack. See research notes for interpretation.
"""
from rule_view_verified_15 import apply as apply_rule_view
from pathlib import Path
from copy import deepcopy
import sys,json,re,hashlib
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'devtools'))
from build_tottori_gigahertz_2026 import base,pack
from contest_rules import loads,dumps
HF=['1.9','3.5','7','14','21','28'];VU=['50','144','430','1200'];ALL=HF+VU
UP=['1200','2400','5600','10G','24000','47000','77000','135000','248000']
PHONE=['SSB','AM','FM'];MIX=['CW']+PHONE
REG=[f'{i:02}' for i in range(2,49)]+[str(i) for i in range(101,115)]
MUNICIPAL=json.loads((ROOT/'config/db/contest/jarl_municipal_2026.json').read_text())
BUILT=[]

def municipal(prefixes,wards=True):
    return [x['code'] for x in MUNICIPAL['rows'] if x['code'][:2] in prefixes and (x['contest_usable'] if wards else x['kind']!='ward')]

def outside(prefixes=(),exclude=()):return [c for c in REG if c not in prefixes and c not in exclude]

def pred(codes):return dict(field='area',op='in',value=','.join(codes))

def make(ident,name,url,bands,windows,inside,outside_codes,source,notes,duplicate_family=False,guest='allowed',organizer=None):
    organizers={'all_kushiro':'JARL釧路根室支部','all_aomori':'JARL青森県支部','ja9_hf_phone':'JARL北陸地方本部','ja9_hf_cw':'JARL北陸地方本部','ja9_vu':'JARL北陸地方本部','all_ja5':'JARL四国地方本部','kamikawa_souya':'JARL上川宗谷支部','oshima_hiyama':'JARL渡島檜山支部','all_kumamoto':'JARL熊本県支部','iwate_winter':'JARL岩手県支部','nagasaki':'JARL長崎県支部','wakayama':'JARL和歌山県支部','all_ja4':'JARL中国地方本部','all_tohoku':'JARL東北地方本部','niigata_low_band':'JARL新潟県支部','tochigi':'JARL栃木県支部','all_kyushu':'JARL九州地方本部','kagoshima':'JARL鹿児島県支部','all_kanagawa':'JARL神奈川県支部','ja0_vhf':'JARL信越地方本部コンテスト委員会','oita':'JARL大分県支部'}
    r=base(ident,name,name,(organizer or organizers[ident]),url,bands,windows);e=r['event']
    e['exchange']=dict(kind='numbered_region',codes=inside+outside_codes,same_sent_region=True)
    e['duplicate_fields']=['call','band']+(['mode_family'] if duplicate_family else [])
    e['entrant']['guest_policy']=guest
    e['required_flags']=['国内の規約対象局として、実運用地・使用周波数・免許範囲・完全な番号交換を確認した',
      '大会原典の運用制限と提出数を確認し、未受信番号を事後に補っていない（申告得点・審査前）']
    e['regional']={'declarations':{}}
    aliases=e['normalization']['bands']
    if '1.9' in bands:aliases.update({'1.8':'1.9','1.8MHZ':'1.9'})
    for n,b in [('1.2','1200'),('2.4','2400'),('5.6','5600'),('10','10G'),('24','24000'),('47','47000'),('77','77000'),('135','135000'),('248','248000')]:
        if b in bands:
            for suffix in ['G','GHZ']:aliases[n+suffix]=b
    e['submission']=dict(formats=['JARL R1.0'],zone='JST',contest=name,instructions=notes+' 原案・原典はdocs/contest-researchに保存。2026参考版であり2027へ自動更新しません。主催受付・Windows実機は未検証。自動提出しません。')
    if any(b.endswith('000') for b in bands):e['submission']['band_labels']={b:b[:-3]+'G' for b in bands if b.endswith('000')}
    r['_build']=dict(source=source,inside=inside,outside=outside_codes)
    return r

def cat(r,code,name,bands,modes,sent,eligible=None,station=None,op=None,cap=None,minbands=1,phone=False,**kw):
    c=dict(id=code.replace('.','_'),name=name,bands=bands,modes=modes,max_power=cap,min_bands=minbands,max_bands=len(bands),min_calls=1,required_flags=[],sent_codes=sent)
    if '.' in code:c['submission_code']=code
    if eligible is not None:c['eligible']=pred(eligible)
    if station:c['station_types']=[station]
    if op:c['operator']=op
    if phone:c['required_mode_families']=['phone']
    c.update(kw);r['event']['categories'].append(c);return c

def reg(c,**kw):c.setdefault('regional',{}).update(kw);return c

def declare(r,c,ident,label):
    r['event']['regional']['declarations'][ident]=label
    c.setdefault('regional',{}).setdefault('required_declarations',[]).append(ident)

def club(r,prefix=None):r['event']['submission']['club_entry']=dict(prefix=prefix,station_types=['individual','club'])

def save(r):
    build=r.pop('_build');ident=r['id'];apply_rule_view(r);apply_remaining_view(r);data=dumps(r);loads(data)
    (ROOT/f'config/rules/{ident}_2026.txt').write_text(data+'\n')
    source=ROOT/'docs/contest-research/sources'/build['source']
    build.update(id=ident,year=2026,url=r['url'],sha256=hashlib.sha256(source.read_bytes()).hexdigest(),municipal_source_versions=MUNICIPAL['source_versions'])
    (ROOT/f'config/db/contest/{ident}_2026.json').write_text(json.dumps(build,ensure_ascii=False,indent=2)+'\n')
    pack(ROOT/f'distribution/rules/{ident}_2026_r1.zip',[r],ident+'_2026_r1');BUILT.append(r)
    print(ident,len(r['event']['categories']))
    return r

def kushiro():
    local='0106 0123 01001 01003 01026 01027 01033 01038 01055 01069'.split();out=outside(exclude=['107','110'])
    r=make('all_kushiro','第45回オール釧根コンテスト','https://www.jarl.com/senkon/kn_pdf/45con_%E8%A6%8F%E4%BF%AE%E6%AD%A33_1.pdf',ALL,[('2026-06-07 09:00','2026-06-07 21:00')],local,out,'all_kushiro_2026.pdf','1部門。R1.0希望、sk_test@zmail.plala.or.jp、締切6月30日23:59。本文・添付の指定は未記載。ゲスト不可。個人全帯はHF/VUそれぞれ必要。混合構成・他マルチ最低帯数は未記載で独自条件を追加しない。',guest='forbidden')
    for inside,cp,xp,sp,sent in [(True,'C','K','KOB',local),(False,'W','X','XOB',out)]:
        eligible=None if inside else local
        for p,modes in [(cp,['CW']),(xp,MIX)]:
            for suffix,bs in [('HF',HF),('VU',VU),('HV',ALL)]+([('UU',['144','430'])] if p==xp else []):
                c=cat(r,p+suffix,('管内' if inside else '管外')+' 個人 '+suffix+(' 電信' if p==cp else ' 電信電話'),bs,modes,sent,eligible,station='individual')
                if suffix=='HV':reg(c,required_band_groups=[HF,VU])
        c=cat(r,sp,('管内' if inside else '管外')+' 社団 全帯',ALL,MIX,sent,eligible,station='club',operators_in_comments=True)
    return save(r)

def aomori():
    local=[f'02{i:02}' for i in range(1,41)];out=outside(['02'])
    r=make('all_aomori','第20回オール青森コンテスト','https://jarl-aomori.sakura.ne.jp/contest/all-aomori/',ALL[1:],[('2026-07-25 15:00','2026-07-26 00:00'),('2026-07-26 05:00','2026-07-26 12:00')],local,out,'all_aomori_2026.html','CWのみの電信電話部門は不可。1種目。R1.0対応、主催希望R2.0と区別。ja7cua@jarl.comへ本文貼付、締切8月3日23:59。移動は同一番号内、個人同時1波・社団同帯1波/単一地点。',True)
    village={17,26,28,29,30,31,37,40}
    r['conditions']=[dict(when=pred([f'02{i:02}' for i in village]),points=3),dict(when=pred([f'02{i:02}' for i in range(11,41) if i not in village]),points=2)]
    for mixed,cw,label,sent in [('A','C','県内',local),('X','W','県外',out)]:
        eligible=local if mixed=='X' else None
        for prefix,modes in [(mixed,MIX),(cw,['CW'])]:
            for suffix,bs in [(b.replace('.',''),[b]) for b in ALL[1:]]+[('MH',HF[1:]),('MV',VU),('MO',ALL[1:])]:
                cat(r,prefix+suffix,label+' 個人 '+suffix+(' 電信電話' if prefix==mixed else ' 電信'),bs,modes,sent,eligible,station='individual',phone=prefix==mixed)
        for suffix in ['MN','CS','YL','MS']:
            c=cat(r,mixed+suffix,label+' '+dict(MN='ニューカマー',CS='シルバー',YL='YL',MS='社団')[suffix],ALL[1:],MIX,sent,eligible,station='club' if suffix=='MS' else 'individual',phone=True)
            if suffix=='MN':c['qualification']=dict(license_since='2023-07-25',license_until='2026-07-25',license_output='comments');c['required_flags'].append('初開局日を申告し、再開局や従免取得日と混同していない')
            if suffix=='CS':c['qualification']=dict(min_age=70,age_output='comments');c['required_flags'].append('年齢は2026年7月25日時点で確認した')
            if suffix=='YL':declare(r,c,'yl','YL本人申告')
            if suffix=='MS':c['operators_in_comments']=True
    club(r,'02-');return save(r)

def ja9(kind):
    local=municipal(['28','29','30'],False);out=outside(['28','29','30'])
    vu=kind=='vu';cw=kind=='hf_cw';bands=['50','144','430']+UP if vu else HF
    windows=[('2026-08-08 21:00','2026-08-09 15:00')] if vu else [('2026-11-14 21:00','2026-11-15 15:00')] if cw else [('2026-11-02 21:00','2026-11-03 15:00')]
    source='ja9_vu_2026.pdf' if vu else 'ja9_hf_2026.pdf'
    url='https://www.jarl.com/hokuriku/CONTEST/規約/2026/JA9コンテスト'+('VU' if vu else 'HF')+'2026規約.pdf'
    mail='ja9-vutest@jarl.com' if vu else 'ja9-cw@jarl.com' if cw else 'ja9-ph@jarl.com'
    r=make('ja9_'+kind,'JA9コンテスト'+('VU' if vu else 'HF 電信' if cw else 'HF 電話'),url,bands,windows,local,out,source,'R1.0。件名は運用コール、宛先'+mail+'。締切'+('8月22日24:00' if vu else '12月5日24:00' if cw else '11月23日24:00')+'。SMは2バンド以上、MMは実交信OP2名以上。クラブ対抗は北陸実運用局のみ。紙は1バンド100局超でデュープ確認表。本文/添付の固有指定なし。')
    modes=MIX+['RTTY','SSTV','PSK31','FT4','FT2','DV','DMR','DSTAR','FREEDV','C4FM','DIGITALVOICE'] if vu else ['CW'] if cw else PHONE
    if vu:
        r['event']['normalization']['bands'].update({'10.1G':'10G','10.4G':'10G','10.1GHZ':'10G','10.4GHZ':'10G','10100':'10G','10400':'10G'})
        r['points']=dict(cw=3,phone=1,digital=5);r['event']['prefer']='highest'
        r['event']['normalization']['mode_families'].update({m:'digital' for m in ['SSTV','PSK31','FT2']});r['event']['normalization']['mode_families'].update({m:'phone' for m in ['DV','DMR','DSTAR','FREEDV','C4FM','DIGITALVOICE']})
        r['event']['required_flags'].append('FT8は対象外。データ・画像の完全番号交換と、デジタル音声の直接交信を確認した')
    # Same official category code for both regions: keep geography in a mandatory
    # declared profile, implemented as explicit selection with shared public code.
    for suffix,bs in [(b.replace('.',''),[b]) for b in (bands[:7] if vu else bands)]+[('M',bands)]:
        c=cat(r,'S'+suffix,'SO '+suffix,bs,modes,local+out,op='SO',minbands=2 if suffix=='M' else 1)
    c=cat(r,'MM','MO マルチ',bands,modes,local+out,op='MO');reg(c,min_operators=2)
    # Per-QSO own region decides eligible counterpart, without adding fake codes.
    r['event']['regional']['local_codes']=local
    r['event']['regional']['club_sent_codes']=local
    club(r);return save(r)


def ja5():
    local=municipal(['36','37','38','39'],False);out=outside(['36','37','38','39'])
    r=make('all_ja5','ALL JA5コンテスト','https://www.jarl.com/shikoku/oa-08/index.html',ALL,[('2026-07-18 21:00','2026-07-19 21:00')],local,out,'all_ja5_2026.html','2026から電子のみ。R1.0、本文貼付・添付不可、ja5test@jarl.com、7月31日必着。四国内は受信市郡を県番号でマルチ集計、受信原番号は保持。1部門、社団は単帯運用でも社団部門。独自MO人数・移動・最低帯数を補わない。',guest='forbidden')
    for suffix,label,sent in [('I','四国内',local),('G','四国外',out)]:
        for p,modes in [('C',['CW']),('P',MIX)]:
            for code,bs,station in [('M',ALL,'individual')]+[(b.replace('.',''),[b],'individual') for b in ALL]+[('SD',ALL,'club')]:
                c=cat(r,p+code+suffix,label+' '+('個人' if station=='individual' else '社団')+' '+code+(' 電信' if p=='C' else ' 電信電話'),bs,modes,sent,local if suffix=='G' else None,station=station)
                if suffix=='I':reg(c,multiplier_map={x:x[:2] for x in local})
    return save(r)

def kamikawa():
    local='204 214 220 221 229 452 453 454 455 456 457 458 459 460 461 462 463 464 465 468 469 470 471 472 511 512 513 514 516 520 517 518 519'.split();out=outside(exclude=['101','103']);hf=HF[2:];vu=VU[:3];bands=hf+vu
    r=make('kamikawa_souya','第10回上川宗谷支部コンテスト','https://www.jarl.com/kamikawa/contest/2026KSContest.pdf',bands,[('2026-08-11 09:00','2026-08-11 15:00')],local,out,'kamikawa_soya_2026.pdf','管外同士も1点・マルチ対象。管外は提出種目内に異なる管内2局が必要。同じ局の移動表記や別バンドで局数を増やさない。1種目。kamikawasoya@jarl.com、8月31日（時分指定なし）、件名とファイル名はコール、Windowsファイル名の/は-。JARL版指定なし、R1.0出力。Cabrilloは受付可だが公式テンプレート未特定。')
    r['conditions']=[dict(when=pred(local),points=2)]
    for prefixes,label,sent in [('KCS','管内',local),('XWY','管外',out)]:
        for p,modes in zip(prefixes,[MIX,['CW'],PHONE]):
            for suffix,bs in [('HF',hf),('VU',vu),('AB',bands)]:
                c=cat(r,p+suffix,label+' SO '+suffix+' '+('電信電話' if p==prefixes[0] else '電信' if p==prefixes[1] else '電話'),bs,modes,sent,op='SO',cap=50 if p==prefixes[2] else None)
                if sent==out:reg(c,quotas=[dict(codes=local,min_calls=2)])
        c=cat(r,prefixes[0]+'MO',label+' MO 電信電話 全帯',bands,MIX,sent,op='MO')
        if sent==out:reg(c,quotas=[dict(codes=local,min_calls=2)])
    return save(r)

def oshima():
    local='0104 0136 01024E 01025B 01025D 01079A 01071A 01021B 01021C 01067A 01067B 01059A 01059B 01059C 01053A 01028B 01040A 01016A'.split();out=outside(exclude=['113','114']);bands=ALL[1:]
    r=make('oshima_hiyama','第34回JARL渡島檜山支部コンテスト','https://ohs.hokkaido.jp/wp-content/uploads/2026/07/第34回-JARL-渡島檜山支部コンテスト規約.pdf',bands,[('2026-09-05 18:00','2026-09-06 18:00')],local,out,'oshima_hiyama_2026.pdf','時刻変更18時～翌18時を採用。1種目・SOのみ（社団SO可）。管内外を跨がない番号変更移動可。相手移動番号・サフィックスが変わっても同局同帯1回。初期は先頭有効交信、採用変更時は前行を作業上のチェックログへ。ohcontest@edu-hakodate.jp、9月30日、時分/本文添付指定なし。')
    e=r['event'];e['exchange'].update(kind='literal_region',region_map={},same_sent_region=False);e['regional']['base_call_duplicates']=True
    modes=MIX+['DV','DMR','DSTAR','FREEDV'];e['normalization']['mode_families'].update({m:'phone' for m in modes[4:]})
    e['required_flags'].append('全運用地は管内又は管外の一方に属し、衛星・中継・インターネット経由ではない')
    for p,label,sent in [('N','管内',local),('G','管外',out)]:
        for suffix,bs in [('M',bands),('HF',HF[1:]),('VU',VU)]+[(b,[b]) for b in VU]:cat(r,p+suffix,label+' SO '+suffix,bs,modes,sent,local if p=='G' else None,op='SO')
    return save(r)

def kumamoto():
    local=municipal(['43']);out=outside(['43'])
    r=make('all_kumamoto','2026オール熊本コンテスト','https://www.jarl.com/kmtest/2026allkumamotoreg.pdf',ALL,[('2026-01-11 09:00','2026-01-11 18:00')],local,out,'all_kumamoto_2026.pdf','全局100W以下、QRP5W。電信電話は電話のみ又は混在、CWのみ不可。集中時間外も有効。対象外バンド/モードはチェックログとして残す。R1.0本文、kumamoto2026@jarl.com、件名大文字運用コール、1月18日。R2系不一致は未解消・出力対象外。受理返信なし。',True)
    for p,label,sent in [('K','県内',local),('G','県外',out)]:
        eligible=local if p=='G' else None
        for m,modes in [('F',MIX),('C',['CW'])]:
            for suffix,bs,station in [(b,[b],'individual') for b in (ALL if m=='F' else HF)]+[('M',ALL,'individual'),('SM',ALL,'club')]+([('MQ',ALL,'individual')] if m=='C' else []):
                c=cat(r,p+m+suffix,label+' '+('電信電話' if m=='F' else '電信')+' '+suffix,bs,modes,sent,eligible,station=station,cap=5 if suffix=='MQ' else 100,phone=m=='F')
                declare(r,c,'assistance','SO2R・スキマー・RBN・Jクラスターの各使用有無')
                if station=='club':c['operators_in_comments']=True
                if suffix=='MQ':declare(r,c,'qrp_rig','QRP機種名・自作時のファイナル')
    r['event']['regional']['outside_category_checklog']=True
    return save(r)

def iwate():
    local=municipal(['03'],False);out=outside(['03']);assert len(local)==24
    r=make('iwate_winter','第4回いわてWINTERコンテスト','https://jarl-iwate.com/wp-content/uploads/51ea8f1a1ed0bc896ab5d5812937aeb2.pdf',['7','144'],[('2026-02-11 09:00','2026-02-11 15:00')],local,out,'iwate_winter.pdf','個人SOのみ、ゲスト不可。7/144は別サマリーで両方可。移動50W、固定は免許範囲。県外同士は1点・マルチなしで総0も可。添付推奨、contest@jarl-iwate.com、件名コール＋部門コード、2月20日必着（時分指定なし）。紙は全手書き20局まで。',True,guest='forbidden')
    e=r['event'];e['entrant']['station_types']=['individual'];e['power_by_operation']=dict(stationary=None,portable=50);e['regional']['entry_set']=dict(max=2,kind='disjoint');e['band_modes']={'7':['CW','SSB'],'144':['CW','SSB','FM']}
    for suffix,label,sent in [('KN','県内',local),('TK','県外',out)]:
        for b in ['7','144']:
            c=cat(r,b+suffix,label+' '+b+'MHz',[b],e['band_modes'][b],sent,station='individual',op='SO')
            reg(c,points_by_code={x:2 for x in (out if suffix=='KN' else local)})
            if suffix=='TK':reg(c,multiplier_codes=local)
    return save(r)

def nagasaki():
    local=municipal(['42'],False);out=outside(['42']);bands=ALL[:-1]
    r=make('nagasaki','2026長崎県コンテスト','https://www.jarl.com/nagasaki/nstest/2026ntst.pdf',bands,[('2026-04-04 20:00','2026-04-05 00:00'),('2026-04-05 06:00','2026-04-05 12:00')],local,out,'nagasaki_2026.pdf','1部門。個人/社団および複数社団の掛け持ち運用禁止。県外も同一市郡内移動に限定（同県内自由ではない）。HF電話10W超はHFCPを選択。R1.0、nstest@jarl.com。締切原文4月14日(月)は2026の曜日と不一致、日付を動かさず正式締切要確認。紙は各バンド81局以上で重複確認表・氏名フリガナ。')
    for p,label,sent in [('N','県内',local),('A','県外',out)]:
        for st,station in [('K','individual'),('G','club')]:
            for suffix,bs,modes,cap in [('HFCW',HF,['CW'],None),('HFPH',HF,PHONE,10),('HFCP',HF,MIX,None),('UVPH',VU[:3],PHONE,None)]:cat(r,p+st+suffix,label+' '+('個人' if st=='K' else '社団')+' '+suffix,bs,modes,sent,local if p=='A' else None,station=station,cap=cap)
    return save(r)

def wakayama():
    local='2601 2602 2603 2604 2605 2606 2607 2608 2609 26001 26002 26003 26005 26006 26007'.split();out=outside(['26'])
    r=make('wakayama','第38回和歌山コンテスト','https://www.jarl.com/wakayama/pdf/wk-test/contest38kiyaku.pdf',ALL,[('2026-04-05 09:00','2026-04-05 21:00')],local,out,'wakayama_38.pdf','SOはHF1＋VU1の最大2種目、MO1種目。7＋14は不可。1種目1メール、R1.0本文・添付不可、wk-test@jarl.com。初回件名例WK-TEST JH1HST、再提出はコール＋再提出。4月19日到着（郵送も消印ではない）。移動は具体的場所を記載、証明資料を求められる場合あり。')
    r['event']['regional']['entry_set']=dict(max=2,kind='hf_vu')
    for p,label,sent in [('N','県内',local),('G','県外',out)]:
        eligible=local if p=='G' else None
        for m,modes in [('C',['CW']),('X',MIX)]:
            for suffix,bs in [(b,[b]) for b in ALL]+[('HF',HF),('VU',VU)]:cat(r,p+m+suffix,label+' SO '+m+' '+suffix,bs,modes,sent,eligible,op='SO')
        for suffix,bs in [('7',['7']),('HF',HF)]:cat(r,p+'P'+suffix,label+' SO 電話 '+suffix,bs,PHONE,sent,eligible,op='SO',cap=10)
        cat(r,p+'XMA',label+' MO 電信電話 全帯',ALL,MIX,sent,eligible,op='MO')
    club(r,'26-');return save(r)


def ja4():
    source=ROOT/'docs/contest-research/sources/all_ja4_2026.html'
    text=re.sub('<[^>]+>',' ',source.read_bytes().decode('utf-8',errors='replace'))
    local=sorted(set(re.findall(r'(?<!\d)(?:31|32|33|34|35)\d{2,4}(?!\d)',text)))
    assert len(local)==93 and '310101' in local and '350108' in local and '3101' not in local
    out=outside(['31','32','33','34','35'])
    r=make('all_ja4','第4回オールJA4コンテスト','http://ja4test.mydns.jp/ja4test_04.html',ALL,[('2026-03-15 12:00','2026-03-15 21:00')],local,out,'all_ja4_2026.html','基本1点による暫定申告。主催者の相手ログ照合による追加1点は未反映。対象外バンドも含め全大会交信を提出。最大2種目、部門対象帯域が非重複の場合のみ。Web推奨、失敗時のみjj4kme+ja4test@gmail.com。3月29日23:59、受付メールなし。Web取込後の確認・提出ボタンが必要。',True)
    r['event']['regional'].update(entry_set=dict(max=2,kind='disjoint'),checklog_code='CHL')
    r['event']['submission']['formats']=['JARL R1.0','JARL R2.1'];r['event']['submission']['required_fields']=[]
    r['event']['required_flags'].append('抽出したログに、選択種目の対象外も含む今回の全コンテスト交信が揃っている。番号が変わる場所へ移動していない')
    for p,label,sent in [('N','管内',local),('G','管外',out)]:
        for suffix,bs,op in [('HF',HF,'SO'),('VU',VU,'SO')]+[(b,[b],'SO') for b in ALL]+[('MM',ALL,'MO')]:cat(r,p+suffix,label+' '+op+' '+suffix,bs,MIX,sent,local if p=='G' else None,op=op)
    club(r);return save(r)

def tohoku():
    local=municipal(['02','03','04','05','06','07']);out=outside(['02','03','04','05','06','07']);bands=HF+VU[:3]+UP
    r=make('all_tohoku','第75回オール東北コンテスト','https://www.jarl.com/tohoku/7contest/2026JA7TEST.pdf',bands,[('2026-04-18 21:00','2026-04-19 15:00')],local,out,'all_tohoku_2026.pdf','4月19日14:59を含む。1部門、独自規約でJARLの未記載条件を一括継承しない。ゲスト不可。移動は番号不変範囲、記念局の運用は参考ログ。ja7-test@jarl-miyagi.orgへ本文貼付、件名コールのみ、5月3日23:59。紙は1バンド100局以上で重複確認資料。',True,guest='forbidden')
    e=r['event'];e['entrant'].update(station_types=['individual','club','special'],checklog_only_types=['special']);e['regional']['checklog_code']='CHKLOG';e['submission']['formats']=['JARL R1.0','JARL R2.1']
    for p,label,sent in [('','管内',local),('X','管外',out)]:
        eligible=local if p else None
        for suffix,bs,modes,op,cap in [('CA',bands,['CW'],'SO',None),('FA',bands,MIX,'SO',None)]+[(('1.8' if b=='1.9' else b),[b],MIX,'SO',None) for b in HF+VU[:3]]+[('1200UP',UP,MIX,'SO',None),('MA',bands,MIX,'MO',None)]+([('HF',HF,PHONE,'SO',10),('VU',VU[:3]+UP,PHONE,'SO',20)] if not p else []):cat(r,p+suffix,label+' '+op+' '+suffix,bs,modes,sent,eligible,op=op,cap=cap)
    return save(r)

def niigata():
    local=municipal(['08']);assert len(local)==36
    out=outside(['08']);bands=HF
    r=make('niigata_low_band','第26回新潟コンテスト（7MHz・ハイバンド・ローバンド）','https://www.jarl.com/08test/contest/2026/niigata/rule.html',bands,[('2026-05-17 13:00','2026-05-17 16:00'),('2026-05-17 16:00','2026-05-17 19:00'),('2026-06-14 19:00','2026-06-14 22:00')],local,out,'niigata_2026.html','一大会・三提出区分。旧予約ID niigata_low_bandを互換維持。2026-09-15利用者確認によりNo.9とNo.73は同一大会。新潟 ローバンドだけで独立提出できる。各区分1種目、最大3区分、区分内移動不可・区分間可。出力は区分ごと独立。R1.0、1メール1区分、件名コール＋部門コード、nitestlog@jarl.com、7月6日（電子時分未記載）。',True,guest='forbidden')
    e=r['event'];e['windows'][0]['bands']=['7'];e['windows'][1]['bands']=['14','21','28'];e['windows'][2]['bands']=['1.9','3.5'];e['regional']['entry_set']=dict(max=3,kind='sections');e['submission']['row_scope']='category';e['submission']['contest']='第26回新潟コンテスト'
    for p,label,sent in [('N','県内',local),('G','県外',out)]:
        for m,modes in [('F',PHONE),('C',['CW']),('M',MIX)]:
            for section,suffix,bs,w in [('seven','7',['7'],0)]+[('high',b,[b],1) for b in ['14','21','28']]+[('high','HM',['14','21','28'],1),('low','19',['1.9'],2),('low','35',['3.5'],2),('low','LM',['1.9','3.5'],2)]:
                c=cat(r,p+m+suffix,label+' 新潟 '+{'seven':'7MHz','high':'ハイバンド','low':'ローバンド'}[section]+' '+{'F':'電話','C':'電信','M':'電信電話'}[m]+' '+suffix,bs,modes,sent,local if p=='G' else None,op='SO',scoring_windows=[{k:v for k,v in e['windows'][w].items() if k in ('start','end')}]);reg(c,section=section)
    club(r,'08-')
    branch=deepcopy(r);branch['id']='niigata_branch';branch['name']='第26回新潟コンテスト（7MHz・ハイバンド）';branch['sort_name']=branch['name']
    branch['event']['windows']=branch['event']['windows'][:2]
    branch['event']['categories']=[c for c in branch['event']['categories'] if c['regional']['section']!='low']
    branch['event']['regional']['entry_set']['max']=2
    branch['event']['submission']['instructions']='No.73、5月分。7MHz・ハイバンドは区分別に独立提出。No.9ローバンドとは別選択。 '+branch['event']['submission']['instructions']
    save(branch)
    r['name']='第26回新潟コンテスト（ローバンド1.9/3.5MHz）';r['sort_name']=r['name']
    e['windows']=e['windows'][2:];e['categories']=[c for c in e['categories'] if c['regional']['section']=='low'];e['regional'].pop('entry_set')
    e['submission']['instructions']='No.9、ローバンド単独提出。No.73の5月分とは別選択。 '+e['submission']['instructions']
    return save(r)

def tochigi():
    codes=[x['code'] for x in MUNICIPAL['rows'] if x['contest_usable']];local=[x for x in codes if x[:2]=='15'];out=[x for x in codes if x not in local];bands=['50','144','430']+UP[:4]
    r=make('tochigi','第28回栃木コンテスト','https://www.jarl.com/tochigi/contest/28tochicon_1.pdf',bands,[('2026-07-04 17:00','2026-07-04 20:00')],local,out,'tochigi_2026.pdf','国内全局の交信が1点。通常県外は栃木1局以上、XSHFはその代わりに1エリア1局以上。未達時は明示選択でCHECKLOG。対象種目外も含む大会全交信を提出。全局1箇所・500m内、移動例外なし。tochigi_c@jarl.com、R1.0本文、添付は非推奨、件名小文字コールのみ、7月15日。')
    e=r['event'];e['entrant'].update(station_types=['individual','club','special'],checklog_only_types=['special']);e['required_flags'].append('選択した種目の外も含む全大会交信を抽出した。1箇所500m内の運用を確認した')
    for suffix,bs,modes,op in [(m+b,[b],['CW'] if m=='C' else PHONE,'SO') for m in ['C','P'] for b in ['50','144','430']]+[('XVUHF',['50','144','430'],MIX,'SO'),('XSHF',UP[:4],MIX,'SO'),('XMA',bands,MIX,'MO')]:
        c=cat(r,suffix,op+' '+suffix,bs,modes,codes,op=op)
        reg(c,quotas=[dict(codes=[x for x in codes if x[:2] in ['10','11','12','13','14','15','16','17']],min_calls=1)] if suffix=='XSHF' else [dict(codes=local,min_calls=1,unless_sent_in=local)])
    return save(r)

def kyushu():
    local=municipal([str(i) for i in range(40,48)]);out=outside([str(i) for i in range(40,48)]);bands=ALL[:-1]
    r=make('all_kyushu','第47回オール九州コンテスト','https://www.jarl.com/kyushu/contest/４７規約.pdf',bands,[('2026-11-22 21:00','2026-11-23 15:00')],local,out,'all_kyushu_2026.pdf','100W超はMOP。利用者確定仕様により1人CWのみ100W超でもKFMM/XFMMへ（自動変更しない）。実人数と提出区分を区別。1種目・1局提出、MO/SO掛け持ち禁止。R1.0本文、添付不可、件名大文字コールのみ。ja6test2026@jarl.com、12月1日（時分未記載）。紙は手書きのみ。')
    for p,label,sent in [('K','管内',local),('X','管外',out)]:
        eligible=local if p=='X' else None
        for m,modes in [('F',MIX),('C',['CW'])]:
            for suffix,bs in [(('1.8' if b=='1.9' else b),[b]) for b in bands]+[('SM',bands)]:cat(r,p+m+suffix,label+' SO '+m+' '+suffix,bs,modes,sent,eligible,op='SO',cap=100)
        c=cat(r,p+'FMM',label+' MOP（100W超の1人CWも含む）',bands,MIX,sent,eligible,op='MO')
        c['required_flags'].append('MOP提出区分と実運用者一覧を確認した。100W超の場合は1人CWのみでもこの部門を選ぶ')
        for suffix,modes in [('QRP',MIX),('CQRP',['CW']),('NEW',MIX)]:
            c=cat(r,p+suffix,label+' '+suffix,bands,modes,sent,eligible,op='SO',cap=100 if suffix=='NEW' else 5)
            if suffix=='NEW':
                c['qualification']=dict(license_since='2023-11-22',license_until='2026-11-22',license_output='comments',license_label='局免許年月日（再開局を含む）');c['required_flags'].append('NEWの局免許年月日は再開局も含む対象日として確認した')
            else:declare(r,c,'qrp_rig','QRP機種名・自作時のファイナル')
    r['event']['regional']['club_sent_codes']=local
    club(r);return save(r)

def kagoshima():
    local=municipal(['46'],False);out=outside(['46']);kj=[x+'KJ' for x in local];bands=ALL[:-1]
    r=make('kagoshima','第36回鹿児島コンテスト','https://www.jarl.com/kagoshima/contest/26/kiyaku.pdf',bands,[('2026-07-25 21:00','2026-07-26 00:00'),('2026-07-26 06:00','2026-07-26 12:00')],local+kj,out,'kagoshima_2026.pdf','SO/MO共通100W上限（利用者確定）。県人は県外運用＋過去1年以上居住、KJは送受番号に残しマルチだけ除去。実運用地をゆかり地へ変更しない。県内は同番号内、県人/県外は同都道府県内移動。ゲスト可、1種目。Webアップロード限定R1.0、メール不可、8月9日24時。紙100QSO以下。',True)
    e=r['event'];e['exchange'].update(kind='literal_region',region_map={x+'KJ':x for x in local},same_sent_region=False)
    e['required_flags'].append('自局運用地と県人のゆかり番号を区別し、運用地変更は大会が許す範囲内である')
    for p,label,sent in [('K','県内',local),('G','県外',out)]:
        for suffix,bs,modes,op,cap in [('MC',bands,['CW'],'SO',100),('MCP',bands,MIX,'SO',100),('MP',bands,PHONE,'SO',100),('QRP',bands,MIX,'SO',5),('YL',bands,MIX,'SO',100)]+[(b,[b],MIX,'SO',100) for b in HF+['50']]+[('VU',['144','430'],MIX,'SO',100),('MMC',bands,['CW'],'MO',100),('MMP',bands,MIX,'MO',100)]:
            c=cat(r,p+suffix,label+' '+op+' '+suffix,bs,modes,sent,local if p=='G' else None,op=op,cap=cap)
            if p=='K':reg(c,same_sent_region=True)
            if suffix=='QRP':declare(r,c,'qrp_rig','QRP機種名・自作時のファイナル')
            if suffix=='YL':declare(r,c,'yl','YL本人申告（県人区分との重複不可）')
    c=cat(r,'KJ','県人 SO マルチ 電信電話',bands,MIX,kj,op='SO',cap=100)
    reg(c,same_sent_region=True)
    declare(r,c,'kj_history','鹿児島居住の開始・終了年月と理由（1年以上）');declare(r,c,'actual_location','今回の県外実運用地（ゆかりの市郡とは別）')
    return save(r)


def kanagawa():
    local=municipal(['11']);out=outside(['11']);bands=ALL+['2400']
    r=make('all_kanagawa','第55回オール神奈川コンテスト','https://www.jarlkn.info/application/files/9917/7020/6189/55.pdf',bands,[('2026-06-06 15:00','2026-06-06 18:00'),('2026-06-06 21:00','2026-06-07 00:00')],local,out,'all_kanagawa_2026.pdf','1種目に2ステージ合算、片方のみ可。ステージ内移動不可、間の番号変更可。県内外を跨ぐときは片側のみ提出。一般SO全帯2バンド、他群と新人/Jr/MOは1帯可。電信電話は電話のみ又は混在、CWのみ不可。R1.0本文又はTXT添付、jarlkncontest+akn@gmail.com、件名コール、6月20日。',guest='mo_only')
    e=r['event'];e['windows'][0]['bands']=['14','21','28','50','1200','2400'];e['windows'][1]['bands']=['1.9','3.5','7','144','430'];e['regional']['sent_scope']='window'
    e['required_flags'].append('各ステージ内は移動せず、県内外を跨いだ場合は提出する一方の交信だけを選んだ')
    e['submission']['required_fields']=[]
    for p,label,sent in [('K','県内',local),('X','県外',out)]:
        for m,modes in [('P',PHONE),('C',['CW']),('X',MIX)]:
            ab=[b for b in bands if not (m=='P' and b=='14')]
            specs=[('SA',ab,'SO'),('SHL',HF[:3],'SO'),('SHH',['21','28'] if m=='P' else HF[3:],'SO'),('S50',['50'],'SO'),('S144',['144'],'SO'),('S430',['430'],'SO'),('SU',['1200','2400'],'SO'),('MA',ab,'MO')]+([('SNA',ab,'SO')] if m=='P' else [('SJA',ab,'SO'),('MJA',ab,'MO')])
            for suffix,bs,op in specs:
                c=cat(r,p+m+suffix,label+' '+op+' '+m+' '+suffix,bs,modes,sent,local if p=='X' else None,op=op,minbands=2 if suffix=='SA' else 1,phone=m=='X')
                if m=='P':
                    c['power_by_band']={b:20 if b in ['50','144','430'] else 1 if b=='1200' else 2 if b=='2400' else 10 for b in bs};c['max_power']=max(c['power_by_band'].values())
                    declare(r,c,'telephone_power','電話部門の各運用バンドの実出力（採点条件のバンド別入力と同じ値）')
                if suffix=='SNA':c['station_types']=['individual'];c['qualification']=dict(license_since='2023-06-06',license_until='2026-06-06',license_output='comments');c['required_flags'].append('局免許日は初開局日であり、再開局・従免取得日ではない')
                if suffix=='SJA':c['qualification']=dict(max_age=18,age_output='comments')
                if suffix=='MJA':c['qualification']=dict(operators_max_age=18)
    club(r,'11-');return save(r)

def ja0vhf():
    local=municipal(['08','09']);out=outside(['08','09']);bands=VU[:3]+UP
    r=make('ja0_vhf','第63回JA0-VHFコンテスト','https://www.jarl.com/zerocontest/rule2026/ja0vhf2026.pdf',bands,[('2026-05-09 21:00','2026-05-10 12:00')],local,out,'ja0_vhf_2026.pdf','管内資格と実運用場所は別。管内は基本コール0又は5月7日JARL会員届出住所が信越、かつ信越運用。資格のない信越移動局はSGSM/SGCM。CW優先、個人CW交信は同一提出の電信部門内訳。対象外バンドも0点で提出。途中の場所変更不可。R1.0、ja0contest@gmail.com、Fromはjarl.com以外。電子5月26日必着、紙5月25日消印。',guest='forbidden')
    e=r['event'];e['prefer']='cw';e['regional'].update(local_codes=local,cw_award=True);e['regional']['declarations']['junior_birthdate']='ジュニア申告する場合だけ生年月日 YYYY-MM-DD（管内個人・2008-04-02以降）'
    e['required_flags'].append('運用途中に場所を変えていない。移動時のコール表記と、全バンドの大会交信が提出対象に揃っている')
    for p,label,pref in [('NN','長野','09'),('NI','新潟','08')]:
        sent=[x for x in local if x[:2]==pref]
        for suffix,bs,station in [('SM',bands,'individual')]+[('S'+b,[b],'individual') for b in VU[:3]]+[('S1200',UP,'individual'),('CM',bands,'club')]:
            c=cat(r,p+suffix,label+' 管内 '+('個人' if station=='individual' else '社団')+' '+suffix,bs,MIX,sent,station=station)
            c['required_flags'].append('管内資格は基本コール0、又は2026年5月7日時点のJARL会員住所届出が新潟/長野であり、今回も信越で実運用した（/0付加だけでは資格にならない）')
            declare(r,c,'inside_basis','管内資格の根拠（基本コール0又は5月7日時点の会員住所届出）')
            if station=='individual':reg(c,junior_since='2008-04-02')
    for suffix,station in [('SM','individual'),('CM','club')]:
        c=cat(r,'SG'+suffix,'管外 '+('個人' if station=='individual' else '社団')+' 全帯',bands,MIX,local+out,station=station);reg(c,multiplier_codes=local)
    club(r);return save(r)

def oita():
    local=municipal(['44'],False);out=outside(['44']);kj=[x+'KJ' for x in local];hf=['3.5','7','21','28'];vu=VU[:3]+UP;bands=hf+vu
    r=make('oita','第24回大分コンテスト','https://jarl-oita.blogspot.com/2026/05/blog-post.html',bands,[('2026-06-13 21:00','2026-06-14 15:00')],local+kj,out,'oita_2026.html','利用者確定の全帯得点合計×全帯マルチ合計を採用。2026は県内SOマルチ50MHz以上。電話はSSB/FM/AM/DV/DMR等モード別点、データ通信対象外。1部門・対象外バンドは出力しない。R1.0本文・添付不可、oitatest@jarl.com、件名コール、6月30日24時。管外部門のエリア判定基準・県人移動範囲は原典未明示、申告根拠の確認が必要。')
    e=r['event'];e['exchange'].update(kind='literal_region',region_map={x+'KJ':x for x in local},same_sent_region=True);e['submission']['row_scope']='category';e['duplicate_fields']=['call','band','mode_group']
    phones=PHONE+['DV','DMR','DSTAR','FREEDV'];modes=['CW']+phones;e['mode_groups']={m:m for m in modes};e['normalization']['mode_families'].update({m:'phone' for m in phones[3:]})
    for suffix,bs in [('HF',hf),('50',['50']),('MM',vu)]:
        for prefix,ms in [('K',modes),('PK',phones)]:cat(r,prefix+suffix,'県内 SO '+prefix+' '+suffix,bs,ms,local,op='SO')
    for code,bs in [('KHM',hf),('KVUM',vu)]:
        c=cat(r,code,'県内 MO '+code,bs,modes,local,station='club',op='MO',operators_in_comments=True);reg(c,min_operators=2)
        declare(r,c,'operation_location','県内運用市町村（同一郡でも別町村へ移動不可）')
    for code,bs,ms in [('KHJ',hf,modes),('PKHJ',hf,phones),('KVJ',vu,modes)]:
        c=cat(r,code,'県人 SO '+code,bs,ms,kj,op='SO');declare(r,c,'kj_history','大分出身又は1年以上居住の時期・理由');declare(r,c,'actual_location','県人の実運用地・移動範囲を確認した根拠')
    for area in ['1','2','3','4','5','6','7','8','9','0']:
        for p,bs,ms in [('HG',hf,modes),('PHG',hf,phones),('VG',vu,modes)]:
            c=cat(r,p+area,'県外 '+area+'エリア SO '+p,bs,ms,out,local,op='SO')
            declare(r,c,'area_basis','選択した提出エリアの判定根拠（基本コール/運用地の規約上の扱いを確認）')
    e['required_flags'].append('同時2波や中継を使用せず、県内は同一市町村、県外は同一都府県支庁内での運用を確認した')
    for c in e['categories']:
        if c.get('operator')=='SO':c['station_types']=['individual']
    for c in e['categories']:
        c.get('regional',{}).get('required_declarations',[])[:]=[x for x in c.get('regional',{}).get('required_declarations',[]) if x not in ('area_basis','kj_history','actual_location')]
    return save(r)

if __name__=='__main__':
    kushiro();aomori();ja9('hf_phone');ja9('hf_cw');ja9('vu');ja5();kamikawa();oshima();kumamoto();iwate();nagasaki();wakayama();ja4();tohoku();niigata();tochigi();kyushu();kagoshima();kanagawa();ja0vhf();oita()
    pack(ROOT/'distribution/rules/regional_2026_r1.zip',BUILT,'regional_2026_r1')
