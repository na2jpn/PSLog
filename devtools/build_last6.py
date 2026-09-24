"""Six final verified definitions to reach remaining nine; explicit 2026 sources."""
from build_remaining9 import *
from cabrillo_templates import default_template,dumps as template_dumps

def world(ident,name,bands,modes,windows,profile,source,url):
    r=base(ident,name,name,'JARL' if profile in ('aadx','jarl_rtty') else name,url,bands,windows);e=r['event'];e.update(timezone='UTC',duplicate_fields=['call','band'],regional={'profile':profile,'declarations':{}},submission=dict(formats=['Cabrillo'],zone='UTC',contest=name,instructions='2026保存規約。原ログJST不変、提出UTC。申告得点（審査前）。主催受付・Windows実機未検証。'))
    e['normalization']['bands']['1.8']='1.9';e['required_flags']=['実運用地・免許・出力・原典の周波数を確認し、設備は単一所在地の直径500m内、場外受信機・セルフスポットなし。原番号を事後DBから補っていない','原典の同時送信・交信成立・参加数・クラブ資格と公開条件を確認した。各部門のSO/MOは実運用者で選んだ']
    e['normalization']['mode_families'].update({m:'digital' for m in modes if m in ('FT4','FT8','RTTY')});r['_build']={'source':source,'inside':[],'outside':[]};return r

def template(r,contest,modes,grid=False,tx=False):
    t=default_template();t.update(id=r['id']+'_2026',name=r['name']+' 2026',rule_id=r['id'],contest=contest,url=r['url'],frequency='band');t['modes']=modes
    columns=[('frequency',5),('mode',2),('date',10),('time',4),('own',13)]+([('my_grid',4),('call',13),('his_grid',4)] if grid else [('rst_sent',3),('sent',6),('call',13),('rst_received',3),('received',6)])+([('tx',1)] if tx else [])
    t['columns']=[dict(source=s,width=w,align='left',part=0,literal='') for s,w in columns]
    for h in t['headers']:
        h['default']={'CATEGORY-OPERATOR':'SINGLE-OP','CATEGORY-BAND':'ALL','CATEGORY-POWER':'LOW','CATEGORY-MODE':'DIGI' if grid else 'CW' if 'CW' in modes else 'SSB','CATEGORY-TRANSMITTER':'ONE','CATEGORY-ASSISTED':'ASSISTED'}.get(h['tag'],'')
        if h['tag'] in ('LOCATION','EMAIL'):h['required']=True
    if r['event']['regional']['profile']=='aadx':
        for h in t['headers']:
            if h['tag']=='CATEGORY-OVERLAY':h['choices']=['SOJR','SOSV']
    if r['id']=='jarl_world_wide_rtty':
        t['name']+='（CONTEST暫定）'
        for h in t['headers']:
            if h['tag']=='CATEGORY-MODE':h['default']='RTTY'
            if h['tag']=='CATEGORY-OVERLAY':h['choices']=['YOUTH']
            if h['tag']=='LOCATION':h['required']=False
    (ROOT/f'config/templates/cabrillo/{r["id"]}_2026.txt').write_text(template_dumps(t))

def aadx(cw=True):
    ident='all_asian_dx_'+('cw' if cw else 'phone');modes=['CW'] if cw else ['SSB'];start='2026-06-20 00:00' if cw else '2026-09-05 00:00';end='2026-06-22 00:00' if cw else '2026-09-07 00:00'
    r=world(ident,'ALL ASIAN DX '+('CW' if cw else 'Phone'),HF,modes,[(start,end)],'aadx','aadx_2026.html','https://www.jarl.org/Japanese/1_Tanoshimo/1-1_Contest/aadx_rules.html');e=r['event'];e['submission'].update(contest='AADX-CW' if cw else 'AADX-SSB',instructions='Cabrillo3 UTC、対象外バンドも同じ提出物へ保持。CONTEST AADX-CW / AADX-SSB。Web contest.jarl.org/upload-aa 又は'+('aacw@jarl.org、7月1日' if cw else 'aaph@jarl.org、9月16日')+' UTC必着。SO年齢/MO平均年齢又は01を実交換どおり記録。MSのTX0=RUN、1=MULT。24hは実運用区間を申告し最初24時間だけ採点。相手/MMは自局ASのみ有効、マルチなし。主催受付・Windows実機未検証。')
    for power,cap in [('HP',None),('LP',100)]:
        for suffix,bs in [(x, [b]) for x,b in zip(['160','80','40','20','15','10'],HF)]+[('AB',HF),('AB24',HF)]:
            code='SO'+('AB'+power+'24' if suffix=='AB24' else suffix+power);c=cat(r,code,code,bs,modes,[],op='SO',cap=cap);c.pop('sent_codes')
            if suffix=='AB24':
                c['timing']={'operating':{'max_minutes':2880,'min_off_minutes':60}};extra(r,c,'first24','最初24運用時間のみ採点することを確認（休憩60分以上、以後も提出）')
        for op in ('MS','MM'):
            c=cat(r,op+power,op+power,HF,modes,[],op='MO',cap=cap);c.pop('sent_codes')
            if op=='MS':c['timing']={'band_change':dict(kind='stay',min_minutes=10,tx_ids=['0','1'],on_violation='block')};c['required_flags'].append('MSはRUN1波、異バンド新マルチのみMULT1波。実送信区間・役割を確認した')
    for code,age in [('SOJR',{'max_age':19}),('SOSV',{'min_age':70})]:
        c=cat(r,code,code,HF,modes,[],op='SO');c.pop('sent_codes');c['qualification']=age
    for c in e['categories']:
        for k,label in [('own_entity','自局DXCC識別子（本土JA/K/VE/VK、JD1は別々のID）'),('own_continent','自局実運用大陸 AF/AN/AS/EU/NA/OC/SA'),('exchange_age','実際の送信年齢・MO平均年齢又は01')]:extra(r,c,k,label)
        c['required_flags'].append('アジア表の版と実運用地を確認した。駐日米極東軍補助軍用無線局を有効相手へ含めない。全交信を記録している')
    template(r,e['submission']['contest'],{'CW':'CW'} if cw else {'SSB':'PH'},tx=True);return write(r)

def jarl_rtty():
    r=world('jarl_world_wide_rtty','JARL World Wide RTTY',HF[1:],['RTTY'],[('2026-10-17 00:00','2026-10-19 00:00')],'jarl_rtty','jarl_ww_rtty_2026.html','https://www.jarl.org/Japanese/1_Tanoshimo/1-1_Contest/rtty_rules.html');e=r['event'];e['submission'].update(formats=['Cabrillo','JARL R1.0','JARL R2.1'],instructions='2026第1回保存版。JARL電子ログUTC。Web contest.jarl.org/upload-aa 推奨、rtty@jarl.orgも可、10月29日00:00UTC締切。Cabrillo3対応。CONTEST等未指定ヘッダーは暫定・編集可能で提出フォームで確認。周波数はMHz帯域表示。年齢は実交換（01/00/99可）、MOは平均。YOUTHはSO開始時25歳以下でAGE/意見欄へ記載。公海MM自己局は得点掲載・表彰対象外。主催受付・Windows実機未検証。')
    for code,op,cap in [('SOHP','SO',None),('SOLP','SO',100),('SOQRP','SO',5),('MMHP','MO',None),('MMLP','MO',100)]:
        c=cat(r,code,code,HF[1:],['RTTY'],[],op=op,cap=cap);c.pop('sent_codes')
        for k,label in [('own_entity','自局DXCC識別子（本土JA/K/VE/VK、島嶼は別ID）'),('own_continent','自局の実運用大陸'),('exchange_age','実際に送った年齢・平均又は01/00/99'),('youth','YOUTH 又は NONE'),('youth_birth','YOUTHの生年月日 YYYY-MM-DD（NONEは -）')]:extra(r,c,k,label)
        c['required_flags'].append('Baudot RTTYのみ。SO全帯1波、MOは各帯1波最大5帯。JA/K/VE/VK本土と島嶼、JD1の2エンティティを実運用地で区別した。未受信番号の事後修正なし')
    template(r,'JARL-WW-RTTY',{'RTTY':'RY'})
    club(r);return write(r)

def grid_events(okayama=False):
    ident='all_okayama_ft' if okayama else 'ww-digi';bands=HF+['50','144','430','1200','2400'] if okayama else HF
    r=world(ident,'オール岡山FT8/FT4' if okayama else 'World Wide Digi DX',bands,['FT4','FT8'],[('2026-09-06 00:00','2026-09-06 12:00')] if okayama else [('2026-08-29 12:00','2026-08-30 12:00')],'okayama_ft' if okayama else 'ww_digi','okayama_ft8_2026.html' if okayama else 'wwdigi_rules_web_2026.txt','https://www.jarl.com/okayama/oy-ft8-test-rule-2026.html' if okayama else 'https://ww-digi.com/rules/')
    e=r['event']
    if okayama:
        e['regional']['entry_set']={'kind':'disjoint','max':3};e['submission'].update(row_scope='category',instructions='12種目L/H/V別に提出。Cabrillo3は公式案内のWSJT-X WW-DIGI形式・UTC、フォームで同じUTCと正式部門コードを選択。CONTEST WW-DIGIは交換形式の識別、提出先は岡山専用。9月16日締切、時分規定なし。CQ OYT設定でGLのみ交換。フォームで内容・部門を確認して提出。主催受付は未検証。')
        e['entrant'].update(station_types=['individual','club','special'],checklog_only_types=['special'])
        e['required_flags']=['国内全局を対象とした実運用で、完全なGL交換を確認した。FT8/FT4以外は含めず、QSO後のDBで番号を補っていない','公式WWデジタル設定・CQ OYTでGLのみ交換。RS/RST/SNRは不要。提出時の部門・UTC/JST・再提出置換と締切を確認した']
        for group,bs in [('L',HF[:3]),('H',HF[3:]),('V',bands[6:])]:
            for suffix,op,cap in [('SD','SO',None),('SDP','SO',5),('MD','MO',None),('MDP','MO',5)]:
                c=cat(r,group+'-'+suffix,group+'-'+suffix,bs,['FT4','FT8'],[],op=op,cap=cap);c.pop('sent_codes');c['required_flags'].append('記念局等特別局はチェックログ。通常個人/社団のSO/MOは実運用人数で選んだ')
    else:
        e['submission']['instructions']='2026 WW-DIGI Cabrillo3 UTC、FT4/FT8=DG、レポートなし。GL4中心の球面距離で1+floor(km/3000)、マルチGL2。距離境界の主催照合は未検証。受信GL不明ZZ00は捏造せず、申告得点を省略して提出できる。全帯ログ保持。Webのみ。本文締切48時間と9月1日23:59UTCの不一致を原案に保持し早い側までの提出を案内。'
        for power,cap in [('HIGH',1500),('LOW',100),('QRP',5)]:
            for suffix,bs in [('ALL',bands)]+[(x,[b]) for x,b in zip(['160M','80M','40M','20M','15M','10M'],bands)]:
                c=cat(r,'SO_ONE_'+power+'_'+suffix,'SO ONE '+power+' '+suffix,bs,['FT4','FT8'],[],op='SO',cap=cap);c.pop('sent_codes')
            c=cat(r,'SO_UNLIMITED_'+power,'SO UNLIMITED '+power,bands,['FT4','FT8'],[],op='SO',cap=cap);c.pop('sent_codes')
        for tx,power,cap in [('ONE','HIGH',1500),('ONE','LOW',100),('TWO','HIGH',1500),('UNLIMITED','HIGH',1500)]:
            c=cat(r,'MO_'+tx+'_'+power,'MO '+tx+' '+power,bands,['FT4','FT8'],[],op='MO',cap=cap);c.pop('sent_codes')
            if tx in ('ONE','TWO'):c['timing']={'band_change':dict(kind='hourly',max_changes=8,tx_ids=['0','1'] if tx=='TWO' else [],on_violation='block')}
        for c in e['categories']:
            extra(r,c,'unknown_grid','受信GLがZZ00なら総得点未確定・CLAIMED-SCORE省略で提出することの確認')
            c['required_flags'].append('各帯1波、部門の送信機数・実出力、SOの全作業1人を確認。各QSO開始は人が操作、無人ロボットなし。賞対象の場合は実周波数を入力した')
    template(r,'WW-DIGI',{'FT4':'DG','FT8':'DG'},grid=True,tx=True);return write(r)

def miyazaki():
    local=[f'45{i:02}' for i in range(1,10)]+[f'450{i:02}' for i in range(1,7)];out=outside(['45']);kj=[x+'KJ' for x in local];bands=HF+VU[:3]
    r=make2('miyazaki','第50回宮崎コンテスト','JARL宮崎県支部',bands,[('2026-06-06 18:00','2026-06-07 18:00')],local,out,'miyazaki_2026.html','1種目。JARL R1.0/R2.1を1MB以下のメール本文、添付不可、件名コール、mzlog26@jarl.comへ6月22日まで。県人国外は1点マルチなし、県内国外は6大陸。旧FAQの一括MOチェックログ条件は適用しない。MKJのモード構成は原典未明示で独自最低条件を追加しない。')
    e=r['event'];e.pop('exchange');e['regional'].update(profile='miyazaki',local_a=local,local_b=out,entry_set={'kind':'disjoint','max':1});e['submission']['formats']=['JARL R1.0','JARL R2.1']
    for p,sent in [('M',local),('',out)]:
        for suffix,ms in [('CA',['CW']),('PA',PHONE),('XA',MIX)]:
            c=cat(r,p+suffix,p+suffix,bands,ms,sent,op='SO',minbands=2)
            if suffix=='XA':c['required_mode_families']=['cw','phone']
        for b in bands:cat(r,('M' if p else 'X')+b,('M' if p else 'X')+b,[b],MIX,sent,op='SO')
        c=cat(r,'MN' if p else 'XN','ニューカマー',bands,MIX,sent,op='SO');c['qualification']=dict(license_since='2023-06-06',license_until='2026-06-06',license_output='comments')
        cat(r,p+'MP',p+'MP',bands,MIX,sent,op='MO',operators_in_comments=True)
    c=cat(r,'MKJ','県人',bands,MIX,kj);extra(r,c,'kenjin','宮崎に居住した時期・市郡・理由、現在は県外（国外含む）');extra(r,c,'operator_kind','実際のSO又はMO')
    for c in e['categories']:
        c.pop('sent_codes',None)
        extra(r,c,'sent_region','自局送信地域（国外相手にRSTのみの場合も実運用地番号を申告）');extra(r,c,'locations','運用場所（同一マルチ内移動だけ）')
        c['required_flags'].append('同一マルチ内運用、クロスバンド・レピータなし、SO同時1波。複数番号から運用した場合は一方のみ採用。重複は有利な実交信を残し他を明示チェックログにした')
    club(r);return write(r)

if __name__=='__main__':aadx();aadx(False);jarl_rtty();grid_events();grid_events(True);miyazaki()
