"""Explicit archived-year definitions for PSLOG101's remaining-nine goal.

Only definitions with acceptance coverage may be committed to the progress ledger.
"""
from build_remaining28 import make2,write,flag,extra
from build_regional_2026 import *
import re

def saitama():
    source=ROOT/'docs/contest-research/sources/all_saitama_44.txt'
    table=source.read_text().split('１５．市区町村ナンバー一覧表',1)[1].split('【参考】',1)[0]
    local=sorted(set(re.findall(r'(?<![0-9])13[0-9]{2}(?:[0-9]{2})?(?![0-9])',table)))
    assert len(local)==72, len(local)
    out=outside(['13'])
    r=make2('all_saitama','オール埼玉コンテスト','JARL埼玉県支部',ALL,[('2026-01-12 09:00','2026-01-12 15:00')],local,out,'all_saitama_44.pdf','2026第44回。1人1コール1種目。JARL R1.0/R2.1、jarl.saitama@gmail.com、締切2026-01-23。電話を含むクロスモードは電話として採点・重複判定。相手通信方式は実記録を確認し、終了後のDB・録音等による番号補完は禁止。',duplicate_family=True)
    e=r['event'];e['regional'].update(profile='saitama',local_a=local,entry_set={'kind':'disjoint','max':1})
    e['submission']['formats']=['JARL R1.0','JARL R2.1']
    e['normalization']['modes'].update(A2A='CW',F2A='CW')
    for p,sent in [('S',local),('X',out)]:
        for suffix,bs in [('A',ALL)]+[(b.replace('.',''),[b]) for b in ALL]+[('HF',HF),('VU',VU)]:
            cat(r,p+'-S'+suffix,('県内' if p=='S' else '県外')+' SO '+suffix,bs,MIX,sent,op='SO')
        cat(r,p+'-MA',('県内' if p=='S' else '県外')+' MO オールバンド',ALL,MIX,sent,op='MO',operators_in_comments=True)
    flag(r,'JARL開設局はチェックログとし、それ以外の記念局と区別した。コール接頭辞だけでは局種を判定していない')
    flag(r,'原典第3項の実周波数と型式を確認した。A2A/F2Aは電話側帯域、51.000MHzはFM。場所変更・クロスバンド・レピータなし、SO全帯1波・MO同帯1波')
    flag(r,'リモート設備は単一所在地で場外受信機なし、セルフスポットと依頼なし、1人複数コール提出なし')
    club(r,'13-');return write(r)

if __name__=='__main__':saitama()

def cqvhf(digital=False):
    from cabrillo_templates import default_template,dumps as template_dumps
    ident='cq-vhf-'+('digi' if digital else 'ssbcw');start='2026-07-18 14:00' if digital else '2026-07-04 14:00';end='2026-07-19 14:00' if digital else '2026-07-05 14:00';bands=['50','144'];modes=['FT4','FT8','MSK144','Q65'] if digital else ['CW','SSB','FM']
    r=base(ident,'CQ World Wide VHF '+('Digital' if digital else 'SSB/CW/FM'),'CQ VHF','WWROF','https://cqww-vhf.com/rules.htm',bands,[(start,end)])
    e=r['event'];e['timezone']='UTC';e['regional']={'profile':'cq_vhf','declarations':{}};e['duplicate_fields']=['call','band','my_grid','his_grid']
    e['required_flags']=['原典の許可周波数・実出力・免許範囲を確認した。各バンド1波、レピータ・衛星・航空移動の交信なし',
      '実交換のGLを保持した。6桁記録の先頭4桁を採点・提出へ使用し、レポートは出力しない',
      '援助を使って番号の受領・再送を要求していない。1人1コール、クラブ申告条件、公開と審査への同意を確認した']
    e['normalization']['mode_families'].update({m:'digital' for m in modes} if digital else {})
    e['submission']=dict(formats=['Cabrillo'],zone='UTC',contest=ident.upper(),instructions='2026保存版。Cabrillo3をhttps://cqww-vhf.com/logcheck/へWeb提出。締切'+('7月24日' if digital else '7月10日')+'、時分の規定なし。レポートなしGL4。主催審査前の申告得点。デジタル初期対応はFT4/FT8/MSK144/Q65。任意モード入力も許容し、適否は主催者判断。原モード表記は保持、提出はDG。')
    for power,cap in [('HIGH',1500),('LOW',100),('QRP',10)]:
        for label,bs in [('ALL',bands),('6M',['50']),('2M',['144'])]:
            c=cat(r,'SO_'+power+'_'+label,'SO '+power+' '+label,bs,modes,[],op='SO',cap=cap);c.pop('sent_codes');c['required_flags'].append('全設備500m径内・アンテナ有線接続・単一運用地、全運用と記録は1人')
    for code,op,cap in [('HILLTOPPER','SO',100),('ROVER',None,None),('MO','MO',None)]:
        c=cat(r,code,code,bands,modes,[],op=op,cap=cap);c.pop('sent_codes')
        if code=='HILLTOPPER':
            c['timing']={'operating':{'max_minutes':360,'min_off_minutes':0}};c['required_flags'].append('単一移動運用地・全設備500m径内・SO、連続6時間以内のHilltopper運用')
        elif code=='ROVER':
            extra(r,c,'operator_count','Roverの実運用者数（1又は2）');extra(r,c,'rover_locations','各GLの運用地と設備全体を100m以上移動した記録')
            c['required_flags'].append('Rover運用は2人以下・1コールで/Rを明示。GL境界では1つだけ選び、新GLへ設備全体100m以上移動した')
        else:c['required_flags'].append('2人以上の実運用・全設備500m径内・アンテナ有線接続・単一運用地')
    r['_build']={'source':'cqvhf_rules_2026.txt','inside':[],'outside':[]}
    t=default_template();t.update(id=ident+'_2026',name=r['name']+' 2026',rule_id=ident,contest=ident.upper(),url='https://cqww-vhf.com/cabrillo.htm')
    t['columns']=[dict(source=s,width=w,align='left',part=0,literal='') for s,w in [('frequency',5),('mode',2),('date',10),('time',4),('own',13),('my_grid',4),('call',13),('his_grid',4)]]
    t['modes']={m:('DG' if digital else 'PH' if m=='SSB' else m) for m in modes}
    keep={'CATEGORY-OPERATOR','CATEGORY-BAND','CATEGORY-POWER','CATEGORY-MODE','CATEGORY-TRANSMITTER','LOCATION','EMAIL','NAME','ADDRESS','ADDRESS-CITY','ADDRESS-STATE-PROVINCE','ADDRESS-POSTALCODE','ADDRESS-COUNTRY','OPERATORS','CLUB','SOAPBOX'}
    t['headers']=[h for h in t['headers'] if h['tag'] in keep]
    for h in t['headers']:
        h['required']=h['required'] or h['tag'] in ('EMAIL','LOCATION')
        h['default']={'CATEGORY-OPERATOR':'SINGLE-OP','CATEGORY-BAND':'ALL','CATEGORY-POWER':'LOW','CATEGORY-MODE':'DG' if digital else 'MIXED','CATEGORY-TRANSMITTER':'ONE'}.get(h['tag'],'')
        if h['tag']=='CATEGORY-MODE':h['choices']=['DG'] if digital else ['SSB','CW','FM','MIXED']
    (ROOT/'config/templates/cabrillo').mkdir(parents=True,exist_ok=True)
    if digital:
        r['points']=dict(cw=1,phone=1,digital=1)
        for c in e['categories']:c['modes']=['*']
        t['modes']['DG']='DG'
    (ROOT/f'config/templates/cabrillo/{ident}_2026.txt').write_text(template_dumps(t))
    return write(r)

if __name__=='__main__':
    cqvhf(False);cqvhf(True)

def cq160(cw=True):
    from cabrillo_templates import default_template,dumps as template_dumps
    ident='cq-160-'+('cw' if cw else 'ssb');modes=['CW'] if cw else ['SSB'];start='2026-01-23 22:00' if cw else '2026-02-27 22:00';end='2026-01-25 22:00' if cw else '2026-03-01 22:00'
    r=base(ident,'CQ World Wide 160 Meter '+('CW' if cw else 'SSB'),'CQ 160','CQ WW 160 Contest Committee','https://cq160.com/rules.htm',['1.9'],[(start,end)]);e=r['event'];e['timezone']='UTC';e['duplicate_fields']=['call','band'];e['regional']={'profile':'cq160','declarations':{}};e['normalization']['bands']['1.8']='1.9'
    e['required_flags']=['CQ用カントリーはDXCC・WAE・IG9/IH9・大陸区分を実運用地で確認した。通常DXCC欄とは別の識別子を使用し、本土米K・カナダVE・AK/KH6を区別した',
      '開催中の完全な番号交換を確認した。自局・相手の実運用大陸を使用し、未受信番号をDBで補っていない',
      '同時1波・CQ周波数1つ、セルフスポットなし、ネット等で交信を手配・確認していない。ITU地域の周波数、国内免許制限、主催の公開・審査条件を確認した',
      '同一連続敷地、又は全設備1500m半径内、全アンテナ有線接続。クラブ申告の資格と配分を確認した']
    e['submission']=dict(formats=['Cabrillo'],zone='UTC',contest=ident.upper(),instructions='2026保存版。Cabrillo3・実周波数kHzを入力しhttps://cq160.com/logcheck/へWeb提出。締切'+('1月30日22:00UTC' if cw else '3月6日22:00UTC')+'。SO30h/MO40h、休止30分以上。CQゾーンは所在地情報でマルチに数えない。実周波数出力を初期対応とする。主催審査前の申告得点。')
    for code,cap in [('SO_HIGH',1500),('SO_LOW',100),('SO_QRP',5),('SA_HIGH',1500),('SA_LOW',100),('MO_HIGH',1500)]:
        c=cat(r,code,code,['1.9'],modes,[],op='MO' if code=='MO_HIGH' else 'SO',cap=cap);c.pop('sent_codes');c['timing']={'operating':{'max_minutes':2400 if code=='MO_HIGH' else 1800,'min_off_minutes':30}}
        extra(r,c,'own_cq_entity','自局CQカントリー識別子（JA、DL、本土米K、加VEなど）');extra(r,c,'own_continent','自局の実運用大陸 AF/AN/AS/EU/NA/OC/SA')
        if code.startswith('SA'):c['required_flags'].append('SO Assisted：追加リモート受信機は1つだけ、主送信地点から100km以内')
        else:c['required_flags'].append('送信地点外の受信機は使用していない（QRPの援助許可とリモート受信機特例は区別）')
        if code.startswith('SO') and code!='SO_QRP':c['required_flags'].append('QSO発見援助なし、全運用・記録・スポット作業は1人')
        elif code=='MO_HIGH':c['required_flags'].append('複数人の実運用、援助可、同時1波、場外受信機なし')
        else:c['required_flags'].append('全運用・記録作業は1人。援助はこの区分の範囲内')
    r['_build']={'source':'cq160_rules_2026.txt','inside':[],'outside':[]}
    t=default_template();t.update(id=ident+'_2026',name=r['name']+' 2026',rule_id=ident,contest=ident.upper(),url='https://cq160.com/cabrillo.htm',frequency='actual');t['modes']={'CW':'CW'} if cw else {'SSB':'PH'}
    t['headers']=[h for h in t['headers'] if h['tag'] not in ('CATEGORY-STATION','CATEGORY-TIME','CATEGORY-OVERLAY','GRID-LOCATOR')]
    for h in t['headers']:
        h['default']={'CATEGORY-OPERATOR':'SINGLE-OP','CATEGORY-BAND':'160M','CATEGORY-POWER':'LOW','CATEGORY-MODE':'CW' if cw else 'SSB','CATEGORY-TRANSMITTER':'ONE','CATEGORY-ASSISTED':'NON-ASSISTED'}.get(h['tag'],'')
        if h['tag'] in ('EMAIL','LOCATION'):h['required']=True
    (ROOT/'config/templates/cabrillo').mkdir(parents=True,exist_ok=True);(ROOT/f'config/templates/cabrillo/{ident}_2026.txt').write_text(template_dumps(t))
    return write(r)

if __name__=='__main__':cq160(True);cq160(False)

def nara():
    bands=['28','50','144','430','1200'];years=[f'{i:02}' for i in list(range(52,100))+list(range(27))];local=[y+'N' for y in years]
    r=make2('nara_vuhf','第52回JARL奈良県支部V・UHFコンテスト','JARL奈良県支部',bands,[('2026-08-08 19:00','2026-08-09 13:00')],local,years,'nara_vuhf_2026_rules.pdf','県内N/県外G。単帯最大5、同帯CW/混合排他、マルチと単帯不可。JARL R1.0準拠専用列。1バンド1メール本文、マルチは帯域順に1メール、naratest@jarl.com、8月31日必着。2026公式PDFでNX28を照合。',guest='forbidden')
    e=r['event'];e['windows']=[]
    for i,b in enumerate(bands):
        start=f'2026-08-08 {19+i:02}:00';end=f'2026-08-08 {20+i:02}:00' if i<4 else '2026-08-09 00:00';e['windows'].append(dict(start=start,end=end,bands=[b]))
        e['windows'].append(dict(start=f'2026-08-09 {12-i:02}:00',end=f'2026-08-09 {13-i:02}:00',bands=[b]))
    e['regional'].update(profile='nara',entry_set={'kind':'disjoint','max':5});e['exchange']['region_map']={x:x[:2] for x in local+years};e['submission'].update(order='band_time',row_scope='category',required_fields=[])
    r['scoring']['multipliers']=[dict(id=k,source=source,kind='whole',start=0,length=2,per_band=True,when={'all':[]}) for k,source in [('tail','prefix'),('year','area')]]
    for p,sent in [('N',local),('G',years)]:
        for m,ms in [('C',['CW']),('X',MIX)]:
            for suffix,bs in [(b,[b]) for b in bands]+[('M',bands)]:
                c=cat(r,p+m+suffix,('県内' if p=='N' else '県外')+' '+m+' '+suffix,bs,ms,sent,minbands=2 if suffix=='M' else 1,mo_operators_in_comments=True)
                if p=='G':c['eligible']={'field':'exchange','op':'in','value':','.join(local)}
                reg(c,min_operators=1);extra(r,c,'call_license_year','当該コールの最初の局免許年（西暦4桁・再開局も初年）');extra(r,c,'operator_kind','実運用者区分 SO / MO');extra(r,c,'all_locations','同一府県内の全運用地一覧')
    flag(r,'同一府県内の移動のみ、全運用地を記載した。同帯2波・レピータ・ゲスト・体験運用なし。社団運用者は有資格登録メンバー')
    return write(r)

if __name__=='__main__':nara()

def kyoto():
    import unicodedata
    text=unicodedata.normalize('NFKC',(ROOT/'docs/contest-research/sources/kyoto_70.txt').read_text());local=sorted(set(re.findall('[CW][0-9]{2}|G[0-9]{2}[A-Z]',text.split('表1 京都府内の市区郡符号')[1].split('表2')[0])))
    out='SY RM KK OH SC IS NM SB TC KR HD IR HY OM AM IT AT YM MG FS NI NN TK KN CB ST IB TG GM YN SO GF AC ME SI NR OS WK HG TY FI IK OY SN YG TT HS KA TS EH KC FO SG NS KM OT MZ KG ON OG'.split();assert len(local)==36,len(local);assert len(out)==60,len(out)
    bands=HF+VU+['2400','5600'];r=make2('kyoto','第70回京都コンテスト','JARL京都府支部・JARL京都クラブ',bands,[('2026-02-07 20:00','2026-02-08 16:00')],local,out,'kyoto_70.pdf','1電子メール1種目、単帯最大2、マルチ1のみ。R1.0本文、件名CALLSIGN:部門、kt-test@ja3yaq.ampr.org、2月28日。地域と3桁番号は独立加算、ニューカマー係数を掛けて最後だけ切上げ。ゲストは実OP名。')
    e=r['event'];e.pop('exchange');e['regional'].update(profile='kyoto',local_a=local,local_b=out,entry_set={'kind':'modes_disjoint','max':2},checklog_code='CL');e['duplicate_fields']=['call','band','mode_family'];e['submission'].update(row_scope='category')
    periods=[('2026-02-07 20:00','2026-02-07 22:00',['3.5']),('2026-02-07 22:00','2026-02-08 00:00',['1.9']),('2026-02-08 08:00','2026-02-08 09:00',['14','144']),('2026-02-08 09:00','2026-02-08 10:00',['21','144']),('2026-02-08 10:00','2026-02-08 11:00',['28','50']),('2026-02-08 11:00','2026-02-08 12:00',['50','1200','2400','5600']),('2026-02-08 13:00','2026-02-08 14:00',['7','430']),('2026-02-08 14:00','2026-02-08 16:00',['7'])];e['windows']=[dict(start=a,end=z,bands=bs) for a,z,bs in periods]
    r['scoring']['multipliers']=[dict(id='region',source='area',kind='whole',start=0,length=2,per_band=True,when={'all':[]}),dict(id='volunteer_club',source='prefix',kind='whole',start=0,length=3,per_band=True,when={'field':'prefix','op':'in','value':','.join(f'{i:03}' for i in range(1000))})]
    for p in ['I','O']:
        for suffix,bs,minbands,op in [('A',bands,4,'SO'),('B',bands,1,'SO'),('C',VU+['2400','5600'],1,'SO')]+[(b.replace('.',''),[b],1,'SO') for b in bands]+[('M',bands,1,'MO')]:
            c=cat(r,p+suffix,('府内' if p=='I' else '府外')+' '+op+' '+suffix,bs,MIX,[],op=op,minbands=minbands,operators_in_comments=op=='MO');c.pop('sent_codes');reg(c,same_sent_region=True,entry_group='exclusive' if suffix in ('A','B','C','M') else 'single')
            if suffix=='B':c['max_bands']=3
            if op=='SO':
                extra(r,c,'participation_age','参加時の年齢（整数）');extra(r,c,'young_birthdate','18歳以下は生年月日YYYY-MM-DD、それ以外は -');extra(r,c,'first_license_date','成人は初開局日YYYY-MM-DD、係数対象外は 対象外、18歳以下は -')
    flag(r,'同一部門内場所変更なし、SO全帯1波・MO同帯1波・単一地点、クロスバンド・レピータ・1人複数コールなし。MO担当者は他部門へ提出しない')
    flag(r,'ニューカマーは再開局ではなく初開局で判定し、JARL京都府支部・JARL京都クラブの規約と宣誓を確認した')
    return write(r)

if __name__=='__main__':kyoto()

def cqww(mode):
    from cabrillo_templates import default_template,dumps as template_dumps
    rtty=mode=='rtty';ident='cq-ww-'+mode;bands=HF[1:] if rtty else HF;year=2026 if rtty else 2025
    start={'cw':'2025-11-29 00:00','ssb':'2025-10-25 00:00','rtty':'2026-09-26 00:00'}[mode];end={'cw':'2025-12-01 00:00','ssb':'2025-10-27 00:00','rtty':'2026-09-28 00:00'}[mode];url='https://cqwwrtty.com/' if rtty else 'https://cqww.com/'
    r=base(ident,'CQ World Wide '+mode.upper(),'CQ WW','CQ WW '+('RTTY DX' if rtty else 'DX')+' Contest Committee',url+'rules.htm',bands,[(start,end)]);r['year']=year;e=r['event'];e['timezone']='UTC';e['duplicate_fields']=['call','band'];e['regional']={'profile':'cq_ww_rtty' if rtty else 'cq_ww','declarations':{}};e['normalization']['bands']['1.8']='1.9'
    e['required_flags']=['CQカントリー（DXCC/WAE/IG9/IH9）、大陸、ゾーンを実運用地で確認し、未受信番号を事後に補っていない。CQ専用欄は通常DXCC欄と分離した',
      '同帯1波、必要なインターロック、交互CQなし、セルフスポット・依頼なし、原典の周波数・免許・実出力・外部手段による交信確認禁止を守った',
      '参加部門・クラブ資格と配分・公開と審査への同意を確認した。必要な録音・設備資料は実際に保存し、ソフトの確認欄を資料の代用にしない',
      'Overlayを申告する場合、CLASSICは1台・無援助・送信中受信なし、ROOKIE/YOUTHは本人資格、TB-WIRESは対象大会のアンテナ条件を確認した']
    if rtty:e['required_flags'].append('45.45baud・170Hz shift ITA2のみ、周波数変更・相手呼出・記録は人が開始した。単一RTTYデコーダと多ch援助を区別した')
    e['submission']=dict(formats=['Cabrillo'],zone='UTC',contest=ident.upper(),instructions=str(year)+'保存版。Cabrillo3実周波数、Web '+url+'logcheck/ 。単帯でも他帯の交信を提出に残す。CLASSIC等は別集計し、本体得点を置換しない。締切'+({'cw':'2025-12-05','ssb':'2025-10-31','rtty':'2026-09-29'}[mode])+'23:59UTC。主催審査前。')
    r['scoring']['multipliers']=[dict(id=k,source=f,kind='whole',start=0,length=2,per_band=True,when={'all':[]}) for k,f in [('zone','area'),('country','country')]]+([dict(id='wve',source='prefix',kind='whole',start=0,length=3,per_band=True,when={'all':[]})] if rtty else [])
    band_names=dict(zip(HF,['160M','80M','40M','20M','15M','10M']))
    for op in ['SO','SA']:
        for power,cap in [('HIGH',1500),('LOW',100),('QRP',5)]:
            for label,bs in [('ALL',bands)]+[(band_names[b],[b]) for b in bands]:
                c=cat(r,op+'_'+power+'_'+label,op+' '+power+' '+label,bs,[mode.upper()],[],op='SO',cap=cap);c.pop('sent_codes')
                c['required_flags'].append('SO全作業1人・同時1波。'+('QSO発見援助なし' if op=='SO' else 'QSO発見援助ありの区分を選択した'))
                extra(r,c,'overlay','Overlay NONE / CLASSIC / ROOKIE / YOUTH');extra(r,c,'overlay_evidence','Overlay根拠：ROOKIE初免許日・YOUTH生年月日YYYY-MM-DD、CLASSIC全運用区間 start / end を ; 区切り、NONEは -')
    for code,cap in [('MS_HIGH',1500),('MS_LOW',100),('M2_HIGH',1500),('MM_HIGH',1500),('MD_HIGH',1500)]:
        c=cat(r,code,code,bands,[mode.upper()],[],op='MO',cap=cap);c.pop('sent_codes')
        if code.startswith(('MS','M2')):
            spec=dict(kind='hourly',max_changes=8,tx_ids=['0','1'],on_violation='block') if rtty or code.startswith('M2') else dict(kind='stay',min_minutes=10,tx_ids=['0','1'],on_violation='block');c['timing']={'band_change':spec}
            c['required_flags'].append('RUN/MULT又は2系列を全行に0/1で記録し、同時は別帯。MSのMULTは新マルチだけ・CQを出さない')
    for c in e['categories']:
        extra(r,c,'own_cq_entity','自局CQカントリー識別子（JA、DL、本土米K、加VEなど）');extra(r,c,'own_continent','自局の実運用大陸 AF/AN/AS/EU/NA/OC/SA');extra(r,c,'own_cq_zone','自局の実運用CQゾーン1～40')
        c['required_flags'].append('全設備は同一DXCC・CQゾーン内の分散構成' if c['id'].startswith('MD_') else '全送受信設備は500m径の単一所在地、アンテナ有線接続、場外受信機なし')
    r['_build']={'source':'cqww_rtty_rules_2026.txt' if rtty else 'cqww_rules_2025.txt','inside':[],'outside':[]}
    t=default_template();t.update(id=ident+'_'+str(year),year=year,name=r['name']+' '+str(year),rule_id=ident,contest=ident.upper(),url=url+'cabrillo.htm',frequency='actual');t['modes']={mode.upper():'RY' if rtty else 'PH' if mode=='ssb' else 'CW'}
    if rtty:
        cols=[('frequency',5,0),('mode',2,0),('date',10,0),('time',4,0),('own',13,0),('rst_sent',3,0),('sent',2,1),('sent',4,2),('call',13,0),('rst_received',3,0),('received',2,1),('received',4,2)]
        t['columns']=[dict(source=f,width=w,part=p,align='left',literal='') for f,w,p in cols]
    t['columns'].append(dict(source='tx',width=1,part=0,align='left',literal=''))
    for h in t['headers']:
        h['default']={'CATEGORY-OPERATOR':'SINGLE-OP','CATEGORY-BAND':'ALL','CATEGORY-POWER':'LOW','CATEGORY-MODE':mode.upper(),'CATEGORY-TRANSMITTER':'ONE','CATEGORY-ASSISTED':'NON-ASSISTED','CATEGORY-STATION':'FIXED'}.get(h['tag'],'')
        if h['tag'] in ('EMAIL','LOCATION'):h['required']=True
    (ROOT/f'config/templates/cabrillo/{ident}_{year}.txt').write_text(template_dumps(t));return write(r)

if __name__=='__main__':
    for mode in ['cw','ssb','rtty']:cqww(mode)

def wpx(mode):
    from cabrillo_templates import default_template,dumps as template_dumps
    rtty=mode=='rtty';year=2026;oldyear=2026 if rtty else 2025;r=loads((ROOT/f'config/rules/cq-ww-{mode}_{oldyear}.txt').read_text());ident='cq-wpx-'+mode
    start={'cw':'2026-05-30 00:00','ssb':'2026-03-28 00:00','rtty':'2026-02-14 00:00'}[mode];end={'cw':'2026-06-01 00:00','ssb':'2026-03-30 00:00','rtty':'2026-02-16 00:00'}[mode];url='https://cqwpxrtty.com/' if rtty else 'https://cqwpx.com/';r.update(id=ident,name='CQ World Wide WPX '+mode.upper(),sort_name='CQ WPX',year=2026,url=url+'rules.htm',organizer='CQ WPX '+('RTTY ' if rtty else '')+'Contest Committee');e=r['event'];bands=e['windows'][0]['bands'];e['windows']=[dict(start=start,end=end,bands=bands)];e['regional']['profile']='cq_wpx_rtty' if rtty else 'cq_wpx';e['regional']['declarations'].pop('own_cq_zone')
    e['regional']['declarations']['overlay']='Overlay NONE / CLASSIC / ROOKIE / YOUTH / TB-WIRES'
    e['regional']['declarations']['overlay_evidence']='Overlay根拠：ROOKIE初免許日・YOUTH生年月日、CLASSIC全運用区間 start / end を ; 区切り、TB-WIRESアンテナ構成（半角英数）、NONEは -'
    e['required_flags'][0]='実運用地のカントリーと大陸、許可された移動プリフィックスを確認した。実際の交換連番を保持し、受信番号を事後補完せず再採番しない'
    e['required_flags'].append('全QSO・実際の送信連番系列を対象に含めた。SO/MSは共通系列、M2/MM/MDはバンド別系列')
    e['required_flags'].append('TB-WIRES申告時は10/15/20mを1本給電の1台トライバンダー、低帯域は単一エレメント'+('。受信専用アンテナ禁止の独自条項はこのRTTY保存版にない' if rtty else '、別受信アンテナなし'))
    e['submission'].update(contest=ident.upper(),instructions='2026保存版。Cabrillo3実周波数、Web '+url+'logcheck/ 。単帯でも他帯QSOを保持、連番は再採番しない。SO'+('30' if rtty else '36')+'h/休止60分、MO48h。CLASSICは最初24hを別採点。締切'+{'cw':'6月2日','ssb':'3月31日','rtty':'2月17日'}[mode]+'23:59UTC。SSB規約見出しの2025表記は公式2026日本語PDF冒頭（wpx_rules_2026_jp_datecheck.pdf）と照合。')
    r['scoring']['multipliers']=[dict(id='prefix',source='prefix',kind='whole',start=0,length=2,per_band=False,when={'all':[]})]
    e['categories']=[c for c in e['categories'] if not c['id'].startswith('SA_')]
    for c in e['categories']:
        c['regional']['required_declarations'].remove('own_cq_zone')
        c['required_flags']=[f.replace('QSO発見援助なし','QSO発見援助可（CLASSICを除く）') for f in c['required_flags'] if not f.startswith('RUN/MULT')]
        if c['operator']=='SO':c['timing']={'operating':{'max_minutes':1800 if rtty else 2160,'min_off_minutes':60}}
        elif c['id'].startswith('MS_'):
            c['timing']={'band_change':dict(kind='hourly',max_changes=10,tx_ids=[],on_violation='block')};c['required_flags'].append('MSは同時1波、毎時計10変更まで、共通送信連番')
        elif c['id'].startswith('M2_'):c['required_flags'].append('M2は異なる帯域で同時2波まで、各TX毎時計8変更、全行TX0/1、バンド別連番')
    r['_build']={'source':'wpx_rtty_rules_2026.txt' if rtty else 'wpx_rules_2026.txt','inside':[],'outside':[]}
    t=default_template();t.update(id=ident+'_2026',year=2026,name=r['name']+' 2026',rule_id=ident,contest=ident.upper(),url=url+'cabrillo.htm',frequency='actual');t['modes']={mode.upper():'RY' if rtty else 'PH' if mode=='ssb' else 'CW'};t['columns'].append(dict(source='tx',width=1,part=0,align='left',literal=''))
    for h in t['headers']:
        h['default']={'CATEGORY-OPERATOR':'SINGLE-OP','CATEGORY-BAND':'ALL','CATEGORY-POWER':'LOW','CATEGORY-MODE':mode.upper(),'CATEGORY-TRANSMITTER':'ONE','CATEGORY-ASSISTED':'ASSISTED','CATEGORY-STATION':'FIXED'}.get(h['tag'],'')
        if h['tag'] in ('EMAIL','LOCATION'):h['required']=True
    (ROOT/f'config/templates/cabrillo/{ident}_2026.txt').write_text(template_dumps(t));return write(r)

if __name__=='__main__':
    for mode in ['cw','ssb','rtty']:wpx(mode)
