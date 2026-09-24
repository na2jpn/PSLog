from rule_view_verified_remaining71 import apply as apply_remaining_view
"""Explicit archived-year contest definitions. No generated future dates."""
from rule_view_verified_15 import apply as apply_rule_view
from build_regional_2026 import *
import unicodedata,zipfile
BUILT=[]
SOURCES=ROOT/'docs/contest-research/sources'

def make2(ident,name,org,bands,windows,local,out,source,notes,**kw):
    aliases={'all_ja0_35':'all_ja0_80m_40m','all_ja0_7':'all_ja0_80m_40m','oidemase_yamaguchi':'oidemase_yamaguchi_hf'}
    entries=json.loads((ROOT/'config/rules/TARGETS_73.json').read_text())['contests']+json.loads((ROOT/'config/rules/ADDITIONAL_RESEARCH.json').read_text())['contests']
    url=next(((v.get('rules_url') or '') for v in entries if v['id']==aliases.get(ident,ident)),'')
    r=make(ident,name,url,bands,windows,local,out,source,notes,organizer=org,**kw)
    r['event']['exchange'].update(kind='literal_region',region_map={})
    return r

def write(r):
    build=r.pop('_build');ident=r['id'];year=r['year'];source=SOURCES/build['source']
    build.update(id=ident,year=year,municipal_source_versions=MUNICIPAL['source_versions'],sha256=hashlib.sha256(source.read_bytes()).hexdigest())
    apply_rule_view(r);apply_remaining_view(r);data=dumps(r);loads(data);(ROOT/f'config/rules/{ident}_{year}.txt').write_text(data+'\n')
    (ROOT/f'config/db/contest/{ident}_{year}.json').write_text(json.dumps(build,ensure_ascii=False,indent=2)+'\n')
    pack(ROOT/f'distribution/rules/{ident}_{year}_r1.zip',[r],ident+f'_{year}_r1');BUILT.append(r);print(ident,len(r['event']['categories']));return r

def two(r,local,out):return [('','管内',local,None),('X','管外',out,local)]
def flag(r,text):r['event']['required_flags'].append(text)
def phones(r,modes):r['event']['normalization']['mode_families'].update({m:'phone' for m in modes})
def points_bands(r,mapping):r['conditions']=[dict(when=dict(field='band',op='eq',value=b),points=p) for b,p in mapping.items()]
def extra(r,c,k,label):declare(r,c,k,label)

def ishikari():
    local=[f'0101{i:02}' for i in range(1,11)]+'0103 0117 0124 0131 0134 0135 01006 01008 01009 01010 01034 01035 01039 01062 01063 01075'.split();out=outside(exclude=['106','108']);bands=ALL+['2400']
    r=make2('ishikari','2026石狩後志支部コンテスト','JARL石狩後志支部',bands,[('2026-06-06 21:00','2026-06-07 00:00'),('2026-06-07 06:00','2026-06-07 21:00')],local,out,'ishikari_2026.html','1種目、土曜個人と日曜社団は別局での例外。JARL R1.0/R2.1 TXTをWeb提出、6月30日。高校生以下は学年申告。01006は後志所属を町村で確認。')
    e=r['event'];e['regional'].update(profile='ishikari',local_codes=local);e['regional']['declarations']['abuta_locality']='01006の該当自他局・町村名と後志所属の確認根拠（該当時）';e['submission']['formats']=['JARL R1.0','JARL R2.1']
    for p,ms in [('C',['CW']),('X',MIX)]:
        for suffix,bs in [(b.replace('.',''),[b]) for b in bands]+[('M',bands)]:cat(r,p+suffix,'個人 '+p+' '+suffix,bs,ms,local+out,station='individual')
    c=cat(r,'JM','個人 ジュニア',bands,MIX,local+out,station='individual');extra(r,c,'grade','ジュニア本人の学年（高校生以下）');c['required_flags'].append('高校生以下であることを学年で確認した')
    cat(r,'MM','社団 電信電話',bands,MIX,local+out,station='club',operators_in_comments=True)
    flag(r,'運用中は送信番号の地域を変えず、原典の同時送信制限を確認した。01006の胆振側は管内市郡として扱わない')
    return write(r)

def yamagata():
    local='YM YN TR ST SJ SG KM MY NG TD HG OB NY YZ OI ID OG SR KH AS OE NS KN TK MK SN NK YB KY SK OK TZ FN MR MG'.split();out=outside(['05']);r=make2('yamagata_sakuranbo','第8回山形さくらんぼQSOコンテスト','JARL山形県支部',ALL,[('2026-06-13 05:00','2026-06-13 21:00'),('2026-06-13 21:00','2026-06-14 13:00')],local,out,'yamagata_sakuranbo_2026.pdf','1部門、HFとVUの時間を区別。R1.0 Web、6月21日23:59。個人参加者のクラブ局掛け持ち不可。登録地域クラブ限定。YCへのHF2+VU1条件の適用は原典未明示、独自強制しない。')
    e=r['event'];e['windows'][0]['bands']=HF;e['windows'][1]['bands']=VU
    for p,sent,eligible in [('Y',local,None),('X',out,local)]:
        for suffix,bs,n in [('ALL',ALL,1),('HF',HF,2),('HHF',HF[3:],1),('VU',VU,2)]+[(b,[b],1) for b in ['1.9','3.5','7','50','144','430']]+[('YL',ALL,1),('J',ALL,1)]:
            c=cat(r,p+suffix,p+' 個人 '+suffix,bs,MIX,sent,eligible,station='individual',minbands=n)
            if suffix=='ALL':reg(c,band_minima=[dict(bands=HF,min=2),dict(bands=VU,min=1)])
            if suffix=='YL':extra(r,c,'yl','YL本人申告')
            if suffix=='J':extra(r,c,'grade','ジュニアの学年（中学生以下）');c['required_flags'].append('中学生以下の本人であることを学年で確認した')
    c=cat(r,'YC','山形登録地域クラブ',ALL,MIX,local,station='club',operators_in_comments=True);extra(r,c,'registered_club','JARL山形県支部登録地域クラブの名称と登録根拠')
    flag(r,'同一送信地域の範囲で運用し、個人参加とクラブ参加の掛け持ちはしていない')
    return write(r)

def yamanashi():
    local=['1701','1702']+[f'17{i:02}' for i in range(4,15)]+['17002','17003','17004','17007','17008'];out=[f'{i:02}' for i in range(1,51) if i!=17];a=['7','21','28','50'];b=['144','430','1200']
    r=make2('yamanashi','第21回山梨コンテスト','JARL山梨県支部',a+b,[('2026-06-14 10:00','2026-06-14 12:00')],local,out,'yamanashi_2026.pdf','SOのみ（社団SO可）。R1.0 Web専用、6月28日24:00、メール不可。県内外とも山梨1局以上。Oは英字。新人社団資格は原典未明示、該当時に参加根拠を記載。',duplicate_family=True)
    r['conditions']=[dict(when=pred(local),points=3)];r['event']['submission']['row_scope']='category'
    for p,sent in [('Y',local),('O',out)]:
        for suffix,bs,new in [('1',a,False),('2',a,True),('3',b,False),('4',b,True)]:
            c=cat(r,p+'-'+suffix,p+' SO '+('新人 ' if new else '一般 ')+('A' if bs==a else 'B'),bs,MIX,sent,op='SO');reg(c,quotas=[dict(codes=local,min_calls=1)])
            if new:c['qualification']=dict(license_since='2023-06-14',license_until='2026-06-14',license_output='comments');c['required_flags'].append('初めての局免許で以前の免許がなく、山梨コンテスト初参加である');extra(r,c,'new_eligibility','新人の参加資格の確認根拠（社団の場合も明記）')
            extra(r,c,'operator_identity','実運用者の氏名・個人コール（社団SOも記載）')
    flag(r,'SO全作業1人・同時1波、開催中は運用場所を変更していない')
    return write(r)

def ja8():
    local=[str(i) for i in range(101,115)];out=[f'{i:02}' for i in range(2,49)];tags=dict(zip('ABCDEFGHIJ',range(1,11)));tags.update(M=1,X=3);lc=[c+t for c in local for t in tags];oc=[c+t for c in out for t in tags];bands=HF+VU[:3]+UP[:4]
    r=make2('all_ja8','2026 ALL JA8コンテスト','JARL北海道地方本部',bands,[('2026-06-27 21:00','2026-06-28 00:00'),('2026-06-28 06:00','2026-06-28 18:00')],lc,oc,'all_ja8_2026.pdf','1種目、R2.1専用Web提出、7月8日必着。問い合わせallja8@jarl.comへ送信しても不受理。Mと年代非公開Xを原記録どおり保持。奨励賞は10代かつA、年齢だけで付与しない。')
    e=r['event'];e['exchange']['region_map']={c:c[:-1] for c in lc+oc};e['regional'].update(profile='ja8',checklog_code='CHK');e['submission']['formats']=['JARL R2.1']
    for p,sent,eligible in [('H',lc,None),('G',oc,local)]:
        for m,ms in [('W',['CW']),('X',MIX)]:
            for suffix,bs in [('01',bands)]+list(zip(['02','03','04','06','08','10','11'],[[b] for b in HF+['50']])):
                c=cat(r,p+m+suffix,p+' SO '+m+' '+suffix,bs,ms,sent,eligible,op='SO');reg(c,points_by_code={x:tags[x[-1]] for x in lc+oc})
        for suffix,bs,op in [('12',['144','430']+UP[:4],'SO'),('21',bands,'MO')]:
            c=cat(r,p+'X'+suffix,p+' '+op+' '+suffix,bs,MIX,sent,eligible,op=op);reg(c,points_by_code={x:tags[x[-1]] for x in lc+oc})
    flag(r,'送信年代は実運用者・平均でなく大会の年代符号規定に沿う値で確認し、公開しない場合のXを勝手に年齢へ変えていない。SO移動の例外以外は場所を変更していない')
    e['rule_view']={
        'restrictions':'常置場所を離れてコンテスト参加のために移動するシングルオペは、運用開始時のマルチプライヤー内で場所変更を認められます。年代別符号はマルチオペがM、年代非公開を希望する場合はXです。10代・符号Aの参加者には奨励賞があります。その他の交信禁止事項はJARLコンテスト規約によります。',
        'submission_notes':'電子ログはJARL北海道地方本部のログ提出専用サイトから提出。問い合わせ用メールアドレス allja8@jarl.com に送っても受け付けられません。締切は2026年7月8日必着。紙ログは交信100局まで、記入項目はすべて手書き。',
    }
    return write(r)

def okhotsk():
    local='0108 0111 0119 01005B 01005D 01005E 01036A 01036B 01036C 01070D 01070E 01070F 01070H 01070I 01070J 01048A 01048B 01048C'.split();out=outside(exclude=['104'])
    r=make2('okhotsk','第50回オホーツクコンテスト（最終回・2026）','JARLオホーツク支部',ALL,[('2026-07-18 18:00','2026-07-19 18:00')],local,out,'okhotsk_2026.pdf','第50回で終了の保存版。次年度日程を生成しない。1種目、R1.0/R2.1、jr8ivs@jarl.com、8月7日到着、本文/添付指定なし。SOの同一番号内移動特例、MOは一箇所。')
    r['event']['submission']['formats']=['JARL R1.0','JARL R2.1']
    for p,sent,eligible in [('H',local,None),('',out,local)]:
        for suffix,bs,ms,op in [('XA',ALL,MIX,'SO'),('CA',ALL,['CW'],'SO')]+[('X'+b.replace('.',''),[b],MIX,'SO') for b in ALL]+[('MXA',ALL,MIX,'MO')]:cat(r,p+suffix,('管内 ' if p else '管外 ')+suffix,bs,ms,sent,eligible,op=op)
    return write(r)

def miyagi():
    text=unicodedata.normalize('NFKC',(SOURCES/'all_miyagi_2026.txt').read_text());local=sorted(set(re.findall(r'(?<![A-Z0-9])\d{2}(?:C|W|G[A-Z])(?![A-Z])',text)));assert len(local)==39,len(local)
    out=outside(['06']);bands=HF+VU[:3]+UP
    r=make2('all_miyagi','第47回オール宮城コンテスト','JARL宮城県支部',bands,[('2026-01-17 18:00','2026-01-18 12:00'),('2026-01-17 18:00','2026-01-18 13:00')],local,out,'all_miyagi_2026.pdf','R1.0/R2.1、mg-test@jarl-miyagi.org、件名コール、2月2日23:59。通常単帯1つ＋1200UPのみ例外2提出。対象外の参考ログは得点対象外。',duplicate_family=True,guest='forbidden')
    e=r['event'];e['windows'][0]['bands']=HF+VU[:3];e['windows'][1]['bands']=UP;e['regional'].update(entry_set=dict(max=2,kind='singles_up'),checklog_code='CHKLOG');e['submission']['formats']=['JARL R1.0','JARL R2.1'];e['entrant'].update(station_types=['individual','club','special'],checklog_only_types=['special']);points_bands(r,{**{'144':2,'430':2},**{b:3 for b in UP}})
    for p,label,sent,eligible in two(r,local,out):
        for suffix,bs,ms,op,g in [('CA',bands,['CW'],'SO','multi'),('FA',bands,MIX,'SO','multi'),('Jr',bands,MIX,'SO','multi')]+[(('1.8' if b=='1.9' else b),[b],MIX,'SO','single') for b in HF+VU[:3]]+[('1200UP',UP,MIX,'SO','up'),('FC',bands,MIX,'MO','multi')]:
            c=cat(r,p+suffix,label+' '+suffix,bs,ms,sent,eligible,op=op);reg(c,entry_group=g)
            if suffix=='Jr':c['qualification']=dict(max_age=22,age_output='comments')
    return write(r)

def kansai():
    local=municipal(['22','23','24','25','26','27']);out=outside(['22','23','24','25','26','27']);bands=['28']+VU[:3]+UP
    r=make2('kansai_vus','関西V・U・Sコンテスト（旧・関西VHF）','JARL関西地方本部',bands,[('2026-05-10 08:00','2026-05-10 16:00')],local,out,'kansai_vus_2026.html','1種目、R1.0/R2.1本文、添付不可、ja3test@jarl.com、5月31日23:59。全大会交信を出力。ゲスト補助はMO、MO参加者の別場所別コール例外あり。記念局は一般と同等。',guest='mo_only')
    e=r['event'];e['submission']['formats']=['JARL R1.0','JARL R2.1'];e['entrant']['station_types'].append('special');e['normalization']['bands'].update({'10.1G':'10G','10.4G':'10G','10.1GHZ':'10G','10.4GHZ':'10G'})
    for p,sent,eligible in [('K',local,None),('',out,local)]:
        for m,ms in [('C',['CW']),('F',MIX)]:
            for suffix,bs,op in [('M',bands,'SO')]+[(b,[b],'SO') for b in bands[:7]]+[('10G',UP[3:],'SO'),('C',bands,'MO')]:
                c=cat(r,p+m+suffix,p+' '+op+' '+m+' '+suffix,bs,ms,sent,eligible,op=op,phone=m=='F',minbands=2 if suffix=='M' else 1)
                if suffix=='M':c['excluded_band_subsets']=[UP[3:]]
    flag(r,'全大会交信を含めた。外部情報で事後の番号修正をせず、指定周波数・SO移動例外・リモート設備一所在地・MO同帯同時送信禁止を確認した')
    return write(r)

KCJ='SY RM KK SC IS NM SB TC KR HD IR HY OM OH AM IT AT YM MG FS NI NN TK KN CB ST IB TG GM YN SO GF AC ME KT SI NR OS WK HG TY FI IK OY SN YG TT HS KA TS EH KC FO SG NS KM OT MZ KG ON OG MT'.split()
def kcj(top=False):
    ident='kcj-topband' if top else 'kcj';bands=['1.9'] if top else HF+['50'];zone=[str(n) for n in range(1,41)]+[f'{n:02}' for n in range(1,10)];start='2026-02-14' if top else '2026-08-15';end='2026-02-15' if top else '2026-08-16'
    r=make2(ident,('第42回KCJトップバンド' if top else '第47回KCJ')+'コンテスト','全国CW同好会（KCJ）',bands,[(start+' 21:00',end+' 21:00')],KCJ,zone,'kcj_topband_2026.pdf' if top else 'kcj_2026.pdf','主催相互照合前の暫定申告。全行・DUPを残す。JARL JSTをWebへ（推奨）。メール '+('2026toptest@kcj-cw.com、3月2日必着' if top else '2026kcjtest@kcj-cw.com、8月31日必着')+'、件名コール、本文推奨、添付なら全サマリー含む1ファイル。今回の出力はJARL、Cabrilloは未対応。主催照合の時刻差10分境界は未確認。',guest='mo_only')
    e=r['event'];e['required_flags']=[f for f in e['required_flags'] if not f.startswith('国内の')];e['exchange']['region_map']={v:str(int(v)) for v in zone};e['regional']['checklog_code']='EX';e['regional']['checklog_prefixes']=['8J','8K','8M','8N'];e['regional']['missing_exchange']=['?','--'];e['submission']['formats']=['JARL R1.0','JARL R2.1']
    for code,cap,low in [('CP',5,None),('CL',50,5),('CM',100,50),('CH',None,100)]:
        c=cat(r,code,'国内 SO '+code,bands,['CW'],KCJ,op='SO',cap=cap);reg(c,points_by_code={z:2 for z in zone})
        if low is not None:c['min_power_exclusive']=low
    if not top:
        for b,suffix in zip(bands,['18','35','7','14','21','28','50']):
            c=cat(r,'C'+suffix,'国内 SO '+b+'MHz',[b],['CW'],KCJ,op='SO');reg(c,points_by_code={z:2 for z in zone})
    c=cat(r,'CMM','国内 MO',bands,['CW'],KCJ,op='MO');reg(c,points_by_code={z:2 for z in zone})
    c=cat(r,'DX','国外',bands,['CW'],zone,mo_operators_in_comments=True);reg(c,points_by_code={v:2 for v in KCJ},multiplier_codes=KCJ)
    flag(r,'相手が実送した番号を使用し、双方ログ照合前の申告と理解した。8J/8K/8M/8N始まりの自局は全体チェックログEXにする。固定移動併用をせず同一マルチ内で運用した')
    flag(r,'160mの実周波数を確認した。1820～1825kHzはCQを出す国外局を呼ぶ場合のみ（BANDだけでは確認できない）')
    e['submission']['required_fields']=['opplace','email']
    return write(r)

def ja0(band,year):
    ident='all_ja0_160m' if band=='1.9' else 'all_ja0_35' if band=='3.5' else 'all_ja0_7';code={'1.9':'18','3.5':'35','7':'7'}[band];a,z=('2025-12-20 21:00','2025-12-20 23:00') if band=='1.9' else ('2026-03-07 21:00','2026-03-08 00:00') if band=='3.5' else ('2026-03-08 08:00','2026-03-08 12:00');numbers=[f'{i:03}' for i in range(1,1000)]
    r=make2(ident,'ALL JA0 '+('1.8' if band=='1.9' else band)+'MHzコンテスト', 'JARL長野県支部',[band],[(a,z)],numbers,[],'all_ja0_18_2025.html' if band=='1.9' else 'all_ja0_35_7_2026.html','JARL JST・専用列順。実交換連番を振り直さない。本文又はWeb、宛先ja0-'+code+'@jarl-nn.asama-net.comのみ、件名コール。締切'+('2025年12月31日' if year==2025 else '2026年3月31日')+'、電子23:59。紙50交信まで。自然0点とチェック希望は別。'+('2025参考版、2026規約待ち。' if year==2025 else '3.5と7は別大会・別提出。'),guest='forbidden')
    r['year']=year;e=r['event'];e['submission']['instructions']=e['submission']['instructions'].replace('2026参考版',str(year)+'参考版');e['exchange']['same_sent_region']=False;e['regional']['profile']='ja0_serial';e['submission']['required_fields']=['email']
    for m,ms in [('C',['CW']),('F',MIX)]:
        c=cat(r,m+code,'SO '+('電信' if m=='C' else '電信電話'),[band],ms,numbers,op='SO');extra(r,c,'license_location','免許県・常置場所・実運用県（0コールの管外運用も区別）')
    flag(r,'国内交信・ゲストなし・同局同帯1交信、相手ログ照合前の申告である。送受信連番は実交換の3桁であり再採番していない')
    return write(r)

def scalg():
    codes=[f'{i:02}' for i in range(100)];valid=[c for c in codes if int(c)<=26 or int(c)>=51]
    r=make2('scalg-6m-cw','第39回エスカルゴ6m CWコンテスト','エスカルゴ SCALG',['50'],[('2026-07-20 10:00','2026-07-20 12:00')],codes,[],'scalg_6m_cw_2026.html','SOのみ、50MHz A1A。1～6のうち1種目、チェックは8。JARL本文のみ、ログ添付不可。ただし自作/不明/代用品の電鍵写真1枚必須。scalgcw@gmail.com、件名運用コール、8月4日23:59:59。電鍵の主催認定をソフトで代行しない。')
    e=r['event'];e['regional'].update(profile='scalg',checklog_code='8');e['submission']['formats']=['JARL R1.0','JARL R2.1']
    for code,label in [('1','固定'),('2','固定QRP'),('3','移動'),('4','移動QRP'),('5','ビギナー'),('6','シニア')]:
        c=cat(r,code,label,['50'],['CW'],codes,op='SO',cap=5 if code in ('2','4') else None);reg(c,multiplier_codes=valid)
        for k,label in [('cw_license','1 CW従免初取得年（ビギナーは年月日）'),('key_model','2 電鍵メーカー・型式／認定コードと操作方法'),('key_photo','2 自作・不明・代用品は電鍵写真1枚の準備状況（それ以外は非該当と理由）')]:extra(r,c,k,label)
        extra(r,c,'sc_location','6 固定/移動の申告、移動なら日本語所在地とJCC/JCG。既設設備・電源の有無')
        if code in ('3','4'):c['required_flags'].append('コンテスト目的で移動し、既設無線設備も使用可能な既設電源もない場所で運用した')
        if code in ('1','2'):c['required_flags'].append('規約の固定定義に該当する（コールの移動表記だけでは判定しない）')
        if code=='5':extra(r,c,'beginner_birthdate','7 ビギナー生年月日 YYYY-MM-DD');c['required_flags'].append('CW従免の初取得日は2025-07-21以降であり、初開局日や上級資格取得日ではない')
        if code=='6':c['qualification']=dict(min_age=70,age_output='comments');extra(r,c,'senior_birthyear','8 シニアの西暦生年')
    flag(r,'搬送波出力時間と手動接点操作時間が一対一の電鍵を使用し、必要な電鍵写真は1枚を別途用意した。交信内容を外部情報で事後補正していない')
    return write(r)

def mie():
    ages=[f'{n:02}' for n in range(100)]+[str(n) for n in range(100,151)];me=[a+'ME' for a in ages];mej=[a+'MEJ' for a in ages];bands=HF+VU[:3]+UP
    r=make2('all_mie_33','第49回オール三重33コンテスト','JARL三重県支部',bands,[('2026-05-05 08:00','2026-05-05 12:00')],me+mej,ages,'mie33_49_2026.pdf','1部門、国内外可。年齢00非公表可、送った値を修正しない。県人は出生/居住歴又は前回2025入賞。R1.0本文、添付不可、log-contest@jarl-mie.com、件名コール、5月31日。')
    e=r['event'];e['required_flags']=[f for f in e['required_flags'] if not f.startswith('国内の')];e['regional']['profile']='mie';e['exchange']['region_map']={x:re.sub('MEJ?$','',x) for x in me+mej};e['exchange']['same_sent_region']=True
    for group,sent in [('A',me),('C',mej),('D',ages),('B',me)]:
        for m,ms in [('X',MIX),('C',['CW'])]:
            specs=[('1',bands,'SO')]
            if group!='B':specs += [('2-'+b,[b],'SO') for b in ['1.9','3.5','7','21','50','144']]+([('3',['28']+VU[:3]+UP,'SO')] if m=='X' else [])+[('4',bands,'MO')]
            for suffix,bs,op in specs:
                c=cat(r,m+group+suffix,group+' '+op+' '+m+' '+suffix,bs,['FM'] if suffix=='3' else ms,sent,op=op);reg(c,points_by_code={x:3 for x in me})
                if group=='D':c['eligible']=dict(field='exchange',op='in',value=','.join(me+mej))
                if group=='B':extra(r,c,'jl_basis','JL本人が女性又は中学生以下である根拠・学年')
                if group=='C':extra(r,c,'kenjin_basis','三重出生/居住歴、又は2025第48回入賞の根拠（MOは代表者）')
                if op=='MO':extra(r,c,'operator_ages','全実運用者と送信年齢・交信担当の対応（交信ごとに実OPの年齢を送ったこと）')
    flag(r,'A/Bは三重県内、Cは県外運用の県人資格、Dはその他として確認した。年齢とME/MEJは実送受信値であり、同局同帯のOP交代で重複を解除しない')
    return write(r)

def yamaguchi():
    local='3301 3302 3303 3304 3306 3307 3308 3310 3311 3312 3313 3315 3316 33002D 33005E 33006A 33006B 33006E 33003E'.split();area4=municipal(['31','32','34','35']);out=outside(['31','32','33','34','35']);vu=VU[:3];bands=HF+vu+UP
    # One shared runtime rule for the two tracked dates, including OM/MO once.
    r=make2('oidemase_yamaguchi','第25回おいでませオール山口コンテスト','JARL山口県支部',bands,[('2026-05-09 18:00','2026-05-10 00:00'),('2026-05-10 06:00','2026-05-10 15:00'),('2026-05-16 18:00','2026-05-17 00:00'),('2026-05-17 06:00','2026-05-17 15:00')],local+area4,out,'all_yamaguchi_2026.pdf','No68/71は一大会の別日程。OM/MOを二重作成しない。通常HF電話/電信/VU/SHFは別交信の複数提出可、OM/MOは排他。R1.0本文、添付不可、ja4jcc.4@gmail.com、件名コール＋部門、6月1日。',duplicate_family=True)
    e=r['event'];e['exchange']['same_sent_region']=False;e['regional'].update(base_call_duplicates=True,entry_set=dict(max=4,kind='modes_disjoint'))
    for i,w in enumerate(e['windows']):w['bands']=HF if i<2 else vu+UP
    r['conditions']=[dict(when=pred(local),points=2)];e['submission']['row_scope']='category'
    for p,sent,eligible in [('Y',local,None),('4',area4,None),('G',out,local+area4)]:
        for suffix,bs,ms,op in [('HF',HF,PHONE,'SO'),('HC',HF,['CW'],'SO'),('VU',vu,MIX,'SO'),('S',UP,MIX,'SO'),('O',bands,MIX,'SO'),('M',bands,MIX,'MO')]:
            c=cat(r,p+suffix,p+' '+op+' '+suffix,bs,ms,sent,eligible,op=op);reg(c,entry_group='exclusive' if suffix in ('O','M') else suffix)
            extra(r,c,'operation_prefecture','初回から両週を通じた実運用県（移動も同県内）')
            extra(r,c,'yamaguchi_awards','任意の新人/ジュニア表彰申告（希望しなければ希望なし。新人初開局日、ジュニアは5月31日の年齢と生年月日）')
            if suffix=='O':c['qualification']=dict(min_age=70,age_output='comments');extra(r,c,'om_birthdate','OM生年月日（2026-05-31時点で70歳以上、男女共通）')
    flag(r,'複数提出は同じQSOを重ねず、OM/MOと他部門を併願しない。初回から同一県の範囲で運用した')
    return write(r)

def gifu():
    local=municipal(['19'],False);out=outside(['19'])
    r=make2('all_gifu','第29回オール岐阜コンテスト','JARL岐阜県支部',ALL,[('2026-06-13 19:00','2026-06-13 22:00'),('2026-06-14 07:00','2026-06-14 10:00')],local,out,'all_gifu_2026_web_extract.txt','国内陸上・1局1種目。R1.0本文、添付不可、je2qbl@jarl.com、件名コール＋コード、6月30日。2026-09-15利用者添付PDF全4ページを画像照合済み。ハーフは運用自体片側のみ。ジュニア割合の無得点/重複分母の細部は原典未確定。',duplicate_family=True)
    for p,sent,eligible in [('G-',local,None),('X-',out,local)]:
        specs=[('SM',ALL,MIX,'SO'),('SMQ',ALL,MIX,'SO'),('SHH',HF,MIX,'SO'),('SVH',VU,MIX,'SO'),('SHF',HF,MIX,'SO'),('SVU',VU,MIX,'SO')]+[('S'+b,[b],MIX,'SO') for b in ALL]+[('SCM',ALL,['CW'],'SO'),('SPM',[b for b in ALL if b!='14'],PHONE,'SO'),('SPD',['144','430'],['FM'],'SO'),('MM',ALL,MIX,'MO'),('MJ',ALL,MIX,'MO')]
        for suffix,bs,ms,op in specs:
            c=cat(r,p+suffix,p+' '+suffix,bs,ms,sent,eligible,op=op,cap=5 if suffix=='SMQ' else None)
            extra(r,c,'operators_qualification','全実運用者のコール/氏名・資格（MO1人なら理由）')
            if suffix in ('SHH','SVH'):reg(c,half_only=True);extra(r,c,'half_date','ハーフの運用日 YYYY-MM-DD（2026-06-13又は2026-06-14）');c['required_flags'].append('抽出外・チェック扱いを含め、他方の日には大会運用していない。全運用記録を含めた')
            if suffix in ('SPM','SPD'):c['power_by_band']={b:20 if b in ['50','144','430'] else 10 for b in bs};c['max_power']=20
            if suffix=='MJ':c['participation']=dict(max_age=18,min_percent=80,family_pair=False,manual_claim=True);extra(r,c,'youth_denominator','担当割合の集計方法・補足（任意、参加資格は本人判断）');c['regional']['required_declarations'].remove('youth_denominator')
    flag(r,'陸上運用・同一番号内、ゲスト等のOP資格と担当を申告し、SO/MO掛け持ちはない。JARL開設記念局はチェックログ（接頭辞だけでは開設主体を決めない）')
    club(r,'19-');return write(r)

def tokai():
    local=municipal(['18','19','20','21']);out=outside(['18','19','20','21']);bands=HF+VU[:3]+UP;dv=['DV','DSTAR','DMR','FREEDV','C4FM'];mix=MIX+dv;phone=PHONE+dv
    r=make2('tokai_qso','第66回東海QSOコンテスト','JARL東海地方本部',bands,[('2026-03-20 09:00','2026-03-20 15:00')],local,out,'tokai_qso_66_2026.html','国内陸上・1局1種目。Web提出R1.0、メール不可、4月3日。バンド・時刻順、担当交信を意見欄に記載。SPAのみ4アマ、SPDVはD-STAR直接通信。',duplicate_family=True)
    phones(r,dv);r['event']['submission']['order']='band_time';points_bands(r,{'1.9':3,'28':2,**dict(zip(UP,[3,5,10,20,20,20,20,20,20]))})
    for p,sent,eligible in [('I-',local,None),('X-',out,local)]:
        specs=[('SA',bands,mix),('SAJ',bands,mix),('SAQ',bands,mix),('SHF',HF,mix),('SHL',HF[:3],mix),('SHH',HF[3:],mix),('SVU',VU[:3]+UP,mix)]+[('S'+b.replace('.',''),[b],mix) for b in HF+VU[:3]]+[('SG',UP,mix)]+[(code,bs,['CW']) for code,bs in [('SCA',bands),('SCHF',HF),('SCHL',HF[:3]),('SCHH',HF[3:]),('SCVU',VU[:3]+UP)]]+[('SPA',[b for b in bands if b!='14'],phone),('SPDV',['28']+VU[:3]+UP,['DV','DSTAR']),('SPD',['144','430'],['FM']),('MA',bands,mix),('MAJ',bands,mix),('MCA',bands,['CW'])]
        for suffix,bs,ms in specs:
            c=cat(r,p+suffix,p+suffix,bs,ms,sent,eligible,op='MO' if suffix in ('MA','MAJ','MCA') else 'SO',cap=5 if suffix=='SAQ' else 20 if suffix in ('SPDV','SPD') else None)
            if suffix=='SPA':extra(r,c,'license_fourth','所持資格が第四級アマチュア無線技士のみであること（上級資格所持者不可）');c['required_flags'].append('SPAの資格は4アマのみ。3アマ以上を所持していない')
            if suffix=='SPDV':c['required_flags'].append('DV各交信はD-STARの直接通信であり、他方式・レピータ・ゲートウェイではない')
            if suffix=='SAJ':c['qualification']=dict(max_age=20,age_output='comments');reg(c,operator_assignments=True)
            if suffix=='MAJ':c['participation']=dict(max_age=20,min_percent=80,family_pair=False);reg(c,operator_assignments=True)
            extra(r,c,'operators_qualification','運用者・補助者のコール/氏名と資格')
    flag(r,'国内陸上・同一番号内で運用し、未受信番号を補っていない。デジタル音声は中継を使わない直接交信と確認した')
    club(r);return write(r)

def tsugaru():
    a=[f'02{i:02}' for i in range(1,11)]+[f'020{i:02}' for i in range(1,9)];b='0104 0136 01021 01024 01025 01067 01071 01079 01016 01028 01040 01053 01059'.split();local=a+b;out=outside(['02'],['113','114'])
    r=make2('tsugaru_kaikyo','第24回津軽海峡コンテスト','JARL青森県支部・JARL渡島檜山支部',VU,[('2026-05-09 18:00','2026-05-10 15:00')],local,out,'tsugarukaikyou_2026.html','2026はSO/MO区分。1提出単位。R2.1推奨、本文のみ添付不可、log-tk2026@jarl-aomori.sakura.ne.jp、件名コール、5月31日。任意採用は他の重複候補を作業上のチェック行に指定、原本は保存。支部対抗点は個人点に足さない。')
    e=r['event'];e['exchange']['same_sent_region']=True;e['regional'].update(profile='tsugaru',local_a=a,local_b=b,base_call_duplicates=True);e['submission']['formats']=['JARL R2.1','JARL R1.0']
    for p,sent,eligible in [('A',local,None),('K',out,local)]:
        for suffix,bs,op in [('MM',VU,'MO'),('SM',VU,'SO')]+[('S'+b,[b],'SO') for b in VU]:cat(r,p+suffix,p+' '+op+' '+suffix,bs,MIX,sent,eligible,op=op,mo_operators_in_comments=True)
    flag(r,'管内移動は自身の支部側（青森／渡島檜山）を維持し、管外は管外内。同じ局の移動で重複を解除しない。MO全OP氏名/コールと資格を記載した')
    return write(r)

def akita():
    local='AK NS OD YT OG YZ KZ YH KM DS NA NH SB UG HN KG KA MS IK HR GJ OO FS MT HP'.split();out=outside(['04']);bands=HF+VU[:3]+UP
    r=make2('all_akita','第40回オール秋田コンテスト','JARL秋田県支部',bands,[('2026-09-12 21:00','2026-09-12 23:00'),('2026-09-13 06:00','2026-09-13 12:00')],local,out,'all_akita_2026.pdf','最大2種目、禁止3条件を確認。2提出は別送。R1.0/R2.1、ji7oed@jarl.com、9月30日。ジュニア/QRPは通常全帯HF+VU条件なし。マルチ2種目の判定集合が異なり合否が変わる境界は主催確認の根拠が必要。',duplicate_family=True)
    e=r['event'];e['regional']['entry_set']=dict(max=2,kind='akita');e['regional']['declarations'].update(entry_band_sets='併願の実提出バンド集合（種目ID=7,14;種目ID=50,144）',entry_basis='併願の判定集合を確認した根拠（境界例の場合）');e['submission']['formats']=['JARL R1.0','JARL R2.1'];e['entrant'].update(station_types=['individual','club','special'],checklog_only_types=['special'])
    for p,sent,eligible in [('A',local,None),('G',out,local)]:
        for m,ms in [('C',MIX),('P',PHONE)]:
            specs=[('SM',bands,'SO','all'),('SH',HF,'SO','hf'),('SJ',bands,'SO','junior')]+([( 'SV',VU[:3]+UP,'SO','vu'),('SQ',bands,'SO','qrp'),('MM',bands,'MO','mo')] if m=='C' else [])+ [('S'+b,[b],'SO',b) for b in (HF+VU[:3] if m=='C' else HF[1:])]+([('S1200',UP,'SO','up')] if m=='C' else [])
            for suffix,bs,op,g in specs:
                c=cat(r,p+suffix+m,p+' '+op+' '+suffix+' '+m,bs,ms,sent,eligible,op=op,cap=5 if g=='qrp' else None,minbands=2 if g=='hf' else 1);reg(c,entry_group=g)
                if g=='all':reg(c,required_band_groups=[HF,VU[:3]+UP])
                if g=='junior':c['qualification']=dict(max_age=18,age_output='comments');extra(r,c,'junior_birth','ジュニアの生年月日（2026-09-12時点で18歳以下）')
                if op=='MO':extra(r,c,'mo_assistants','2名以上の全運用者・アシスト者のコール/氏名と資格');c['required_flags'].append('MOとして2人以上が運用し、アシスト者も名簿へ記載した')
    flag(r,'移動は種目ごとに送信マルチ不変、同じ交信を都合よく削除して禁止併願を回避していない。県内クラブSOは高得点1種目のみ申告する')
    e['rule_view']={'participants': '国内のアマチュア局・SWL。県内局は秋田県内で運用する局、県外局はそれ以外。8J7等の記念局での運用はチェックログ扱いです。', 'power': 'QRP種目は5W以下。その他の種目について、2026年規約に大会独自の一律出力上限は記載されていません。', 'movement': '移動は種目ごとのマルチプライヤーが変わらない範囲内で認められます。移動地はサマリーに記載します。上空・海上移動は不可。', 'call_method': '電信：県内局 CQ AT TEST／県外局 CQ ATG TEST\n電話：CQ オール秋田コンテスト（県内局は自局コール送出時に「秋田県内局」と付ける）', 'counterparts': '県内局は県内を含む全国の局、県外局は秋田県内の局が交信相手です。', 'frequency': '各バンドのJARLコンテスト使用周波数帯と総務省告示の使用区別に従います。種目別の対象バンドは公式規約の表を参照してください。', 'restrictions': '上空・海上移動とレピーター使用は不可。マルチオペは2人以上の運用（アシストも含む）。2種目提出には組合せ制限があります。', 'exchange': '県内局：RS(T)＋秋田県内の市町村略号。県外局：RS(T)＋都府県・北海道地域等の番号。', 'repeat': '同一局・同一バンドでも電信と電話はそれぞれ得点可。同一バンド・同一モードの重複交信は得点不可。'};
    club(r,'04-');return write(r)

def shiga():
    local=municipal(['23'],False);out=outside(['23']);bands=ALL[2:]
    r=make2('shiga','第30回ALL滋賀コンテスト','JARL滋賀県支部',bands,[('2026-07-20 10:00','2026-07-20 12:00'),('2026-07-20 13:00','2026-07-20 15:00')],local,out,'shiga_2026.html','全国同士が有効。滋賀5点、JL3ZKV6点、その他1点。管外は滋賀と交信した実バンド数を追加乗算、0も有効。スプリント/QRPは選択3バンド全て実交信必要。R1.0/R2.1本文、si-test@jarl.com、件名滋賀コンテスト（CALL）、8月3日23:59。')
    e=r['event'];e['regional'].update(profile='shiga',local_codes=local);e['submission']['formats']=['JARL R1.0','JARL R2.1'];e['entrant'].update(station_types=['individual','club','special'],checklog_only_types=['special'])
    for p,sent in [('',local),('O',out)]:
        for m,ms in [('C',['CW']),('F',MIX)]:
            for suffix,bs,op in [('M',bands,'SO'),('MM',bands,'MO')]+[(b,[b],'SO') for b in bands]:
                c=cat(r,p+m+suffix,('管外' if p else '管内')+' '+op+' '+m+suffix,bs,ms,sent,op=op)
                if op=='MO':extra(r,c,'mo_members','2名以上の全運用者と従事者資格');c['required_flags'].append('MOの運用者が2名以上であることを確認した')
    for suffix,w in [('A',0),('B',1)]:
        for m,ms in [('C',['CW']),('F',MIX)]:
            c=cat(r,m+'MS'+suffix,'県内スプリント '+m+' '+suffix,bands,ms,local,op='SO',minbands=3,scoring_windows=[{k:v for k,v in e['windows'][w].items() if k in ('start','end')}]);c['max_bands']=3;reg(c,selected_bands=True);extra(r,c,'scoring_bands','採点する異なる3バンド（MHz、カンマ区切り）')
    c=cat(r,'QRP','県内QRP（3バンド）',bands,MIX,local,op='SO',cap=5,minbands=3);c['max_bands']=3;reg(c,selected_bands=True);extra(r,c,'scoring_bands','採点する異なる3バンド（MHz、カンマ区切り）')
    flag(r,'移動は同一番号内、固定移動切替なし、1種目のみ。3バンド種目は採点外の運用も隠さず残した。提出後の種目変更不可を確認した')
    return write(r)

def gunma():
    local=[f'16{i:02}' for i in range(1,13)]+[p+c for p,cs in [('16001','BCFGHI'),('16003','ABCDE'),('16004','ABC'),('16005','DE'),('16007','D'),('16009','FG'),('16010','ABCI')] for c in cs];assert len(local)==35;out=outside(['16'])
    r=make2('all_gunma','第54回オール群馬コンテスト','JARL群馬県支部',ALL,[('2026-05-16 20:00','2026-05-17 00:00'),('2026-05-17 06:00','2026-05-17 12:00')],local,out,'all_gunma_2026.pdf','104種目。実績に応じた部門を表示し本人が変更、CW優先へ自動変更しない。R1.0/R2.1をメール添付、agclog@akagi76.com、件名コール＋コード、6月1日24:00。紙100局以上は重複表、紙禁止ではない。',guest='forbidden')
    e=r['event'];e['regional']['profile']='gunma';e['submission']['formats']=['JARL R1.0','JARL R2.1'];r['points']['cw']=2
    for p,sent,eligible in [('1',local,None),('2',out,local)]:
        for m,ms in [('A',['CW']),('B',PHONE),('C',MIX)]:
            for b in ALL:cat(r,p+m+b,p+' 個人 '+m+' '+b,[b],ms,sent,eligible,station='individual')
        for letters,ms in [('DEF',['CW']),('GHI',PHONE),('JKL',MIX)]:
            for letter,bs in zip(letters,[ALL,HF,VU]):cat(r,p+letter,p+' 個人 '+letter,bs,ms,sent,eligible,station='individual')
        for suffix,bs in [('Q',HF),('Q1',VU[:3])]:
            for m,ms in [('A',['CW']),('B',PHONE),('C',MIX)]:
                c=cat(r,p+suffix+m,p+' QRP '+suffix+m,bs,ms,sent,eligible,station='individual',cap=5);extra(r,c,'qrp_rig','QRPリグ名・実出力')
        for suffix,bs,st in [('M',ALL,'club'),('JN',HF,'individual'),('JN1',VU,'individual'),('JNC',ALL,'club'),('YL',ALL,'individual'),('SE',HF,'individual'),('SE1',VU,'individual')]:
            c=cat(r,p+suffix,p+' '+suffix,bs,MIX,sent,eligible,station=st,operators_in_comments=st=='club')
            if suffix.startswith('JN'):extra(r,c,'grade','ジュニア本人/社団運用者の学年（高校生以下）');c['required_flags'].append('ジュニアの全対象者は高校生以下であると学年で確認した')
            if suffix.startswith('SE'):c['qualification']=dict(min_age=70,age_output='comments')
            if suffix=='YL':extra(r,c,'yl','YL本人申告')
    flag(r,'ゲスト・クロスモード・セルフスポット・所在地外受信機を使わず、SO移動例外以外の場所変更はない。クラブ局は社団種目。連絡先の郵便番号・電話・メールを記載する')
    e['submission']['required_fields']=['email'];club(r,'16-');return write(r)

def kanagawa_em():
    import zipfile
    with zipfile.ZipFile(SOURCES/'kanagawa_emergency_inside_20260130.zip') as z:
        data=z.read(next(n for n in z.namelist() if n.endswith('.md'))).decode('cp932');postal=sorted(set(re.findall(r'(?<!\d)\d{7}(?!\d)',data)))
    assert len(postal)>1000,len(postal)
    outside_codes=[x['code'] for x in MUNICIPAL['rows'] if x['contest_usable'] and x['code'][:2]!='11'];bands=['3.5','7','50','144','430','1200']
    r=make2('kanagawa_emergency','第44回非常通信訓練コンテスト','JARL神奈川県支部',bands,[('2026-04-04 18:00','2026-04-04 20:00'),('2026-04-04 20:00','2026-04-04 22:00'),('2026-04-04 22:00','2026-04-05 00:00')],postal,outside_codes,'kanagawa_emergency_44_2026.pdf','SOのみ（社団/ゲスト可）。R1.0本文、添付不可、hijou-test@jarlkn.sakura.ne.jp、件名運用コール、電子4月18日、紙4月16日。紙は全手書き100交信以下のみ、PC印刷は正式提出不可。郵便番号未収録は県内地名と確認根拠を入力。')
    e=r['event'];e['exchange'].update(kind='postal_region',codes=outside_codes+['LOCAL','OUT']);e['exchange'].pop('region_map');e['regional'].update(profile='kanagawa_postal',postal_codes=postal);e['regional']['declarations']['postal_confirmation']='未収録郵便番号の県内地名と確認根拠（該当時）';e['band_modes']={b:['SSB','AM']+(['FM'] if b in bands[2:] else []) for b in bands}
    for i,w in enumerate(e['windows']):w['bands']=bands[i*2:i*2+2]
    for p,sent in [('K',['LOCAL']),('X',['OUT'])]:
        for suffix,bs in [('A',bands),('HL',bands[:2]),('V',bands[2:4]),('U',bands[4:])]+[(b.replace('.',''),[b]) for b in bands]:
            c=cat(r,p+suffix,p+' SO '+suffix,bs,PHONE,sent,op='SO',minbands=2 if len(bs)>1 else 1)
            if suffix=='A':c['excluded_band_subsets']=[bands[:2],bands[2:4],bands[4:]]
    flag(r,'開催中は同一郵便番号内でも場所を変更していない。SO全作業1人、HFのFM・CW・デジタル音声は使わず指定周波数を確認した。採点外バンドも記載した')
    e['submission']['required_fields']=[];return write(r)

BUILDERS=[ishikari,yamagata,yamanashi,ja8,okhotsk,miyagi,kansai,kcj,lambda:kcj(True),lambda:ja0('1.9',2025),lambda:ja0('3.5',2026),lambda:ja0('7',2026),scalg,mie,yamaguchi,gifu,tokai,tsugaru,akita,shiga,gunma,kanagawa_em]
if __name__=='__main__':
    for f in BUILDERS:f()
    pack(ROOT/'distribution/rules/remaining28_r1.zip',BUILT,'remaining28_r1')
