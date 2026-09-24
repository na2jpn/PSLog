"""Remaining-contest definitions. No invented years or unresolved identity aliases."""
from build_remaining28 import *

def free_rule(ident,name,org,bands,windows,source,notes,profile,local=(),out=(),guest='allowed'):
    r=make2(ident,name,org,bands,windows,list(local),list(out),source,notes,guest=guest);r['event'].pop('exchange');r['event']['regional'].update(profile=profile,local_a=list(local),local_b=list(out));return r

def naked(r,code,name,bands,modes,**kw):
    c=cat(r,code,name,bands,modes,[],**kw);c.pop('sent_codes');return c

def kcwa():
    codes='SY RM KK OH SC IS NM SB TC KR HD IR HY OM AM IT AT YM MG FS NI NN TK KN CB ST IB TG GM YN SO GF AC ME KT SI NR OS WK HG TY FI IK OY SN YG TT HS KA TS EH KC FO SG NS KM OT MZ KG ON OG MT'.split();assert len(codes)==62
    r=free_rule('kcwa_cw','第42回KCWA CWコンテスト','JARL京都府支部・京都CW愛好会',['3.5','7'],[('2025-12-07 10:00','2025-12-07 20:00')],'kcwa_2025.html','2025参考版。JARL R1.0、実交換RST+略称+帯域別連番（001開始）。単帯でも他帯チェックログを付ける。本文にコードなし、部門名をそのまま出力。kcwa2025@kcwa.sakura.ne.jp と jq3dgt@jarl.com の両方、件名コール、12月31日。2026へ自動更新しない。','kcwa',codes,guest='forbidden');r['year']=2025;e=r['event'];e['regional']['outside_category_checklog']=True;e['entrant']['station_types']=['individual'];e['submission']['order']='band_time'
    for ident,bs,title in [('B35',['3.5'],'3.5MHz部門'),('B7',['7'],'7MHz部門'),('MULTI',['3.5','7'],'マルチバンド部門')]:
        c=naked(r,ident,title,bs,['CW'],station='individual',op='SO',submission_code=title,minbands=2 if ident=='MULTI' else 1);extra(r,c,'own_region','自局のKCJ略称（62地域）');extra(r,c,'location','運用場所（変更なし）');c['required_flags'].append('国内個人局のみ、相手も個人局。実周波数3.510～3.530/7.010～7.040MHz・A1A、同時1波・ゲストなし・場所変更なし。原送信連番と全帯履歴を確認した')
    return write(r)

def hyogo():
    local=municipal(['27']);out=outside(['27']);r=free_rule('all_hyogo','オール兵庫コンテスト','JARL兵庫県支部',ALL,[('2026-01-04 09:00','2026-01-04 21:00')],'all_hyogo_2026.pdf','2026。最大2部門、対象帯域が重ならない組合せのみ。JARL R1.0/R2.1、hyogo_hgtest@yahoo.co.jp、1月18日23:59。2部門目はサマリーCALLSIGNと件名を基本コール直後に-2（例JP3ELG-2/3）。原コール不変。県内国外1点・マルチなし、2701は点ありマルチなし。','hyogo',local,out,guest='mo_only');e=r['event'];e['submission'].update(formats=['JARL R1.0','JARL R2.1'],required_fields=['opplace'],row_scope='category');e['regional']['entry_set']={'kind':'disjoint','max':2};e['entrant'].update(station_types=['individual','club','special'],checklog_only_types=['special'])
    for p in ('I','O'):
        for kind,ms in [('CS',['CW']),('MS',MIX)]:
            for suffix,bs in [('ALL' if p=='I' else 'HF',ALL if p=='I' else HF),('VU',VU)]+[(b,[b]) for b in ALL]+([('QRP',ALL)] if kind=='MS' else []):
                c=naked(r,p+'-'+kind+'-'+suffix,p+' '+kind+' '+suffix,bs,ms,op='SO',cap=5 if suffix=='QRP' else None)
                if kind=='MS':c['required_mode_families']=['phone']
            c=naked(r,p+'-'+('CM' if kind=='CS' else 'MM')+'-ALL',p+' MO '+kind,ALL,ms,op='MO',operators_in_comments=True);reg(c,min_operators=2)
            if kind=='MS':c['required_mode_families']=['phone']
    for c in e['categories']:
        extra(r,c,'own_region','自局送信地域。国外運用の場合はDX');extra(r,c,'submission_number','今回の提出番号 1 又は 2（提出セットの選択順と一致）');c['required_flags'].append('実周波数表を確認。SOはゲストなし・同時1波、MOは実運用者2人以上・同帯1波。部門内場所不変、クロスバンド・レピータなし。ゲストOPとして運用した本人の個人提出なし')
    e['band_modes']={b:['CW','SSB','AM']+(['FM'] if b in ['28']+VU else []) for b in ALL};club(r,'27-');return write(r)

def hiroshima():
    bands=HF+VU[:3]+UP;r=free_rule('hiroshima_was','広島WASコンテスト','JARL広島県支部',bands,[('2026-02-28 21:00','2026-03-01 17:00')],'hiroshima_was_2026.html','2026。JARL R1.0 JST、3月31日、log-2026@HS-contest.org。単帯2種目はサマリー/ログを1本文にまとめて提出、添付不可。自局コールだけの件名。各部門を生成後「提出セット」で1ファイルへ結合。県外GL4・県内市郡区、県内相手5/他1点。','hiroshima',municipal(['35']));e=r['event'];e['windows']=[]
    for bs,a,z in [(HF[:2],'2026-02-28 21:00','2026-03-01 00:00'),(['7'],'2026-03-01 13:00','2026-03-01 17:00'),(['14','50','144'],'2026-03-01 09:00','2026-03-01 12:00'),(['21'],'2026-03-01 09:00','2026-03-01 11:00'),(['28'],'2026-03-01 08:00','2026-03-01 10:00'),(['430']+UP,'2026-03-01 10:00','2026-03-01 12:00')]:e['windows'].append(dict(start=a,end=z,bands=bs))
    e['submission'].update(order='band_time',row_scope='category',required_fields=[],band_labels={'1.9':'1.8'});e['duplicate_fields']=['call','band','mode_family'];e['regional']['entry_set']={'kind':'modes_disjoint','max':2};e['normalization']['modes'].update({'D-STAR':'DSTAR'});modes=MIX+['RTTY','FT8','FT4','JT65','JT9','SSTV','FAX','PSK31','DSTAR','FREEDV','C4FM','DMR'];e['normalization']['mode_families'].update({m:'digital' for m in modes if m not in MIX})
    for p in ('N','G'):
        for suffix,bs in [('M',bands)]+([('MVU',bands[6:])] if p=='N' else [])+[('1.8' if b=='1.9' else b,[b]) for b in HF+VU[:3]]+[('1200',UP),('MM',bands)]:
            c=naked(r,p+'-'+suffix,p+' '+suffix,bs,modes,op='MO' if suffix=='MM' else 'SO',operators_in_comments=suffix=='MM');reg(c,entry_group='exclusive' if suffix in ('M','MVU','MM') else 'single');extra(r,c,'own_region','自局の実送信番号（N市郡区、GはGL4）');extra(r,c,'locations','実バンドごとの運用地と時刻（同帯移動なし、マルチは全帯同一地）')
            c['required_flags'].append('同帯内場所変更なし。マルチは全帯同一地、単帯間のみ場所変更可。MO全員の氏名又はコールと資格を記載。データ/音声区分・実レポートを確認した')
    return write(r)

def shizuoka():
    local='AO SG SI TN CO HN NU AT MI FM IT SM IW YZ FJ KK FE GB FR SD SU KS IZ OE KI IK MH HI KZ MN MZ NI MR SZ NM OY KN YD KH'.split();assert len(local)==39
    bands=HF+VU+UP[1:5];r=free_rule('shizuoka','第35回静岡コンテスト','JARL静岡県支部',bands,[('2026-05-04 12:00','2026-05-04 20:00')],'shizuoka_35_2026.pdf','2026 JARL R1.0。送受RS(T)+番号を結合、対象外帯域も0/-で出力、国外は提出から除外。/QRP略記保持、10.1/10.4は同一10GHz。shizuokatest@jarl.com、件名運用コール、5月18日、再提出は15分超間隔。QRPは430以下対象全交信1W以下、外付け減衰器不可、1.2G以上倍化なし。','shizuoka',local,outside(['18']));e=r['event'];e['windows']=[dict(start='2026-05-04 '+a,end='2026-05-04 '+z,bands=bs) for bs,a,z in [(HF[3:],'12:00','15:00'),(bands[6:],'14:00','17:00'),(['7'],'14:00','20:00'),(HF[:2],'17:00','20:00')]];e['duplicate_fields']=['call','band','mode_family'];e['submission'].update(order='band_time',required_fields=['email']);e['normalization']['bands'].update({'10.1G':'10G','10.4G':'10G','10.1GHZ':'10G','10.4GHZ':'10G'});e['regional']['entry_set']={'kind':'disjoint','max':1}
    for p in ('S','X'):
        for m,ms in [('C',['CW']),('F',MIX)]:
            for suffix,bs,op in [('M',bands,'SO'),('HP',HF,'SO')]+[(b.replace('.',''),[b],'SO') for b in HF+VU[:3]]+[('1200',bands[9:],'SO'),('C',bands,'MO')]:
                c=naked(r,m+suffix+p,m+suffix+p,bs,ms,op=op,cap=1 if suffix=='HP' else None,operators_in_comments=op=='MO')
        naked(r,'HF'+p,'FMハンディ '+p,['50','144','430','1200'],['FM'],op='SO')
    for c in e['categories']:
        extra(r,c,'own_region','自局の送信略符号又は県地域番号');extra(r,c,'qrp','430以下の対象全交信が1W以下でQRP表示を実送信: YES / NO');extra(r,c,'equipment','機種・規定出力/実測・測定方法・アンテナ形式/高さ（QRPの外付けアッテネータ不可）');extra(r,c,'locations','各場所の時刻・所在地（同一マルチ内）');c['required_flags'].append('対象帯域内の高出力交信をチェックログ指定で隠してQRP申告していない。430以下全交信の実出力と/QRP送出を確認し、高帯域へ倍化しない。MO/SO掛持ち例外・相互交信禁止を確認した')
        if c['id'].startswith('HF'):c['required_flags'].append('FMハンディ本体・付属相当アンテナ、同軸延長なし、内蔵可能電源だけ。独自5W上限は設けない')
    club(r,'18-');return write(r)

if __name__=='__main__':kcwa();hyogo();hiroshima();shizuoka()

def party():
    bands=['0.135','0.475']+HF+['10','18','24']+VU+UP[1:]
    r=free_rule('qso_party','第79回QSOパーティ','JARL',bands,[('2026-01-02 09:00','2026-01-07 21:01')],'qso_party_rule_2026.html','2026。20局以上、得点競争なし、部門30。実交換RS(T)と名前（愛称・略称可）。全許可バンド・モード、レピータ不可。国内局は国内外、国外局は国内局との交信。JARL電子ログWeb又はnyp@jarl.org、1月31日。ステッカー希望はメールアドレス必須。紙の場合は返信封筒等を別途確認。','qso_party')
    e=r['event'];e['required_flags']=['実際の完全なレポートと名前交換を確認。レピータ・SWLを含まない。全使用帯域・型式が自他局の免許と法令に適合する'];e['submission']['required_fields']=['email'];e['normalization']['bands'].update({'135KHZ':'0.135','475KHZ':'0.475'});r['points']={k:0 for k in r['points']};r['conditions']=[]
    c=naked(r,'30','アマチュア局',bands,['*'],submission_code='30');extra(r,c,'own_country','自局の運用国・地域（国内はJA）')
    e['rule_view']={'participants': 'アマチュア局およびSWL。PSLogの登録部門はアマチュア局（コード30）です。', 'call_method': '電話：CQ NEW YEAR PARTY\n電信：CQ NYP', 'counterparts': '国内局は国内・国外のアマチュア局、国外局は日本国内のアマチュア局との交信が対象です。', 'frequency': '総務省告示のアマチュア業務に使用する電波型式・周波数の使用区別に従います。', 'restrictions': '総務省告示の使用区別からの逸脱、レピーターの使用は禁止です。', 'exchange': '相手局のシグナルレポートとオペレーターの名前。通称・ニックネーム・イニシャル・ハンドルネームも可。'};r['url']='https://www.jarl.org/Japanese/1_Tanoshimo/1-1_Contest/qso_party_rule.html';
    return write(r)

def shimane():
    bands=['7','21','28','50','144','430'];local=municipal(['32']);out=outside(['32']);r=free_rule('shimane','第46回島根対全日本コンテスト','JARL島根県支部',bands,[('2026-06-21 09:00','2026-06-21 15:00')],'shimane_2026.pdf','2026。通常3部門とAJD別提出。HF県内移動資格時は各HF提出の最後に1000加算。AJD数値点0、完成時刻を得点欄へ、時刻順10局。JARL R1.0、shimane3201@jarl.com、7月13日。移動先市町村を記載。','shimane',local,out)
    e=r['event'];e['duplicate_fields']=['call','band','mode_group'];e['mode_groups']={m:m for m in ('CW','SSB','FM')};e['regional']['entry_set']={'kind':'sections','max':4};e['submission'].update(row_scope='category',required_fields=[])
    for side in ('1','2'):
        for station,letters in [('individual','ABCD'),('club','EFGH')]:
            for letter,section,bs in zip(letters,['VU','HFH','HFL','AJD'],[bands[3:],bands[1:3],bands[:1],bands[:3]]):
                if side=='2' and section=='AJD':continue
                c=naked(r,side+letter,side+' '+station+' '+section,bs,['CW','SSB','FM'],station=station,operators_in_comments=station=='club');reg(c,section=section);extra(r,c,'own_region','実際の送信地域');extra(r,c,'bonus','HF県内移動1000点の申告 YES / NO');extra(r,c,'licensed_region','自局設置場所の市郡番号');extra(r,c,'portable_equipment','YES申告時:既設無線設備・既設電源を使わない事実と移動場所');c['required_flags'].append('開催中同一地点・同帯1波・クロスバンドなし。AJDは移動先エリアで国内10局、QSL取得を要件にしない')
    e['rule_view']={'participants': '日本国内で運用するアマチュア局。島根県内へ移動して運用する県外局は県内局として参加します。', 'movement': 'コンテスト中の運用地点変更と複数地点からの運用は禁止。県内での移動運用地は市町村まで提出書類に記載します。', 'call_method': '県内局：電話 CQオールジャパン／電信 CQ AJ TEST\n県外局：電話 CQ島根／電信 CQ SN TEST', 'counterparts': '県内局は日本国内の局との交信、県外局は島根県内局との交信が得点対象です。', 'frequency': '7・21・28・50・144・430MHz帯。部門別の対象帯域とJARLコンテスト使用周波数帯を確認してください。使用モードはCW・SSB・FM。', 'restrictions': 'クロスバンド交信、コンテスト中の運用地点変更、複数地点からの運用、同一バンドでの2波以上の同時発射は禁止。10分間ルールは適用しません。', 'exchange': '県内局：RS(T)＋市郡ナンバー。県外局：RS(T)＋都府県・支庁ナンバー。', 'repeat': '同一局との同一バンドの交信は最初の1交信が得点対象。ただし電波型式が異なる場合は、それぞれ得点対象です。'};r['url']='https://jarl-shimane.jimdofree.com/事業計画/';
    return write(r)

def iburi():
    codes='0105 0113 0130 0133 01007 01011 01013 01030 01031 01037 01052 01064 01073 01080'.split();assert all(x in municipal(['01']) for x in codes)
    r=free_rule('iburi_hidaka','胆振日高コンテスト','JARL胆振日高支部',ALL,[('2026-07-24 21:00','2026-07-24 23:00'),('2026-07-25 07:00','2026-07-25 23:00'),('2026-07-26 07:00','2026-07-26 21:00')],'iburi_hidaka_2026.pdf','2026。管内は常置場所と1つの/8移動先を統合可。送受原番号を保持し48の小笠原/南鳥島だけ別作業欄で識別。日本語コード・名称をJARL R1.0へ。ja8pmn@jarl.com、8月16日23:59。','iburi',codes,outside(exclude=['111','112']),guest='forbidden')
    e=r['event'];e['duplicate_fields']=['call','band','own'];e['entrant'].update(station_types=['individual','club','special'],checklog_only_types=['special']);e['submission'].update(order='band_time',row_scope='category');e['regional']['entry_set']={'kind':'disjoint','max':1}
    for side,label in [('I','管内'),('O','管外')]:
        for suffix,title,bs,ms,st in [('HC','個人局HF電信マルチバンド部門',HF,['CW'],'individual'),('HX','個人局HF電信電話マルチバンド部門',HF,MIX,'individual'),('VX','個人局V/U電信電話マルチバンド部門',VU,MIX,'individual'),('MX','社団局電信電話マルチバンド部門',ALL,MIX,'club')]:
            c=naked(r,side+suffix,title,bs,ms,station=st,submission_code=label,operators_in_comments=st=='club')
            for k,t in [('fixed_region','常置場所の実送信市郡/県地域番号（使用しない場合NONE）'),('fixed_address','常置場所の住所（使用しない場合NONE）'),('portable_region','移動先1か所の実送信番号（使用しない場合NONE）'),('portable_address','移動先1か所の住所（使用しない場合NONE）')]:extra(r,c,k,t)
            c['required_flags'].append('常置と移動各1地点だけで移動先変更なし。管内移動/8・同時1波・ゲストなし・ネット中継なし。社団全員の氏名と資格を運用者一覧へ記載した')
    return write(r)

def toyama():
    local='富山市 高岡市 魚津市 氷見市 滑川市 黒部市 砺波市 小矢部市 南砺市 射水市 舟橋村 上市町 立山町 入善町 朝日町'.split()
    out='北海道 青森県 岩手県 宮城県 秋田県 山形県 福島県 茨城県 栃木県 群馬県 埼玉県 千葉県 東京都 神奈川県 新潟県 石川県 福井県 山梨県 長野県 岐阜県 静岡県 愛知県 三重県 滋賀県 京都府 大阪府 兵庫県 奈良県 和歌山県 鳥取県 島根県 岡山県 広島県 山口県 徳島県 香川県 愛媛県 高知県 福岡県 佐賀県 長崎県 熊本県 大分県 宮崎県 鹿児島県 沖縄県'.split();assert len(out)==46
    bands=['21','28','50','144','430','1200','2400'];r=free_rule('toyama_emergency','第49回富山県非常無線通信訓練コンテスト','JARL富山県支部',bands,[('2026-01-10 19:00','2026-01-10 23:00')],'toyama_2026_detail.html','2026。指定支部様式の記入済PDF、単帯参加帯赤枠・他帯サマリーとログ・50局超の重複チェック表を含む。実所在地+苗字は自由文字列、集計用所在地は別欄。jh9feh@jarl.com、1月26日到着。','toyama',local,out)
    e=r['event'];e['submission'].update(formats=['所定様式PDF'],row_scope='category');e['regional']['entry_set']={'kind':'sections','max':2};r['points']={k:1 for k in r['points']};r['conditions']=[]
    for ident,title,bs,op in [('I-M','県内シングルオペマルチバンド',bands,'SO')]+[('I-'+b,'県内シングルオペ'+b+'MHz',[b],'SO') for b in bands]+[('I-MM','県内マルチオペマルチバンド',bands,'MO'),('O-M','県外マルチバンド',bands,None),('HANDY','ハンディー',bands,None)]:
        c=naked(r,ident,title,bs,['*'],op=op,submission_code=title,cap=5 if ident=='HANDY' else None,mo_operators_in_comments=True);reg(c,section='HANDY' if ident=='HANDY' else 'NORMAL');extra(r,c,'own_region','自局集計所在地（県内15市町村名、県外都道府県名）');extra(r,c,'equipment','無線機の機種・電源（ハンディーは携行可能電源）');extra(r,c,'antenna','アンテナ（ハンディーは身に付け携行可能）');c['required_flags'].append('国内在住局。実際に交換した所在地と苗字を省略せず入力し、免許範囲内の型式・必要最小出力。ハンディー申告時は全交信FM・5W以下で無線機/電源/アンテナを携行した')
    return write(r)

if __name__=='__main__':party();shimane();iburi();toyama()
