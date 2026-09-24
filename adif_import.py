"""ADIF 3.1.4 subset import. Strict record boundaries; explicit conversions."""
import re,json
from datetime import datetime,timedelta
from decimal import Decimal,InvalidOperation
import xml.etree.ElementTree as ET
from storage import Log,ParsedLine,Issue,InvalidLog
from model import QSO
from remarks_sections import primary,append_primary
from adif_modes import check_pair,MODES

BANDS={'160m':'1.8','80m':'3.5','60m':'5','40m':'7','30m':'10','20m':'14','17m':'18','15m':'21','12m':'24','10m':'28','6m':'50','4m':'70','2m':'144','1.25m':'222','70cm':'430','33cm':'902','23cm':'1200','13cm':'2400','9cm':'3300','6cm':'5600','3cm':'10000','1.25cm':'24000'}
# ADIF international band ranges in MHz, not an assertion of local authorization.
RANGES=[('1.8','2','1.8'),('3.5','4','3.5'),('5.06','5.45','5'),('7','7.3','7'),('10.1','10.15','10'),('14','14.35','14'),('18.068','18.168','18'),('21','21.45','21'),('24.89','24.99','24'),('28','29.7','28'),('50','54','50'),('70','71','70'),('144','148','144'),('222','225','222'),('420','450','430'),('902','928','902'),('1240','1300','1200'),('2300','2450','2400'),('3300','3500','3300'),('5650','5925','5600'),('10000','10500','10000'),('24000','24250','24000')]

def read_adi(data):
    try:text=data.decode('utf-8-sig')
    except UnicodeDecodeError as e:raise InvalidLog('ADIをUTF-8/ASCIIとして読めません。') from e
    if not text.isascii():raise InvalidLog('この版のADI入力はASCIIのみです。日本語はADXを使用してください。')
    records=[];fields={};pos=0;header=True;seen=False
    tag=re.compile(r'<([A-Za-z][A-Za-z0-9_]*)(?::([0-9]+)(?::([A-Za-z]))?)?>')
    while pos<len(text):
        begin=text.find('<',pos)
        if begin<0:
            if text[pos:].strip() and not header:raise InvalidLog('ADIFの末尾に不明な文字があります。')
            break
        if text[pos:begin].strip() and not header:raise InvalidLog('ADIFの項目間に不明な文字があります。')
        m=tag.match(text,begin)
        if not m:raise InvalidLog('ADIFタグが壊れています。')
        name=m[1].upper();pos=m.end()
        if name in ('EOH','EOR'):
            if m[2] is not None:raise InvalidLog('ADIF区切りタグに長さが指定されています。')
            if name=='EOH':
                if seen or not header:raise InvalidLog('EOHの位置が不正です。')
                fields={};header=False
            else:
                records.append(fields);fields={};seen=True;header=False
        else:
            if m[2] is None:raise InvalidLog('ADIFフィールドの長さがありません。')
            end=pos+int(m[2])
            if end>len(text):raise InvalidLog('ADIFフィールドが途中で切れています。')
            if name in fields:raise InvalidLog('同じADIF項目が重複しています: '+name)
            fields[name]=text[pos:end];pos=end
    if fields:raise InvalidLog('最後の交信にEORがありません。')
    if not records:raise InvalidLog('ADIFに交信レコードがありません。')
    return records

def read_adx(data):
    try:text=data.decode('utf-8-sig')
    except UnicodeDecodeError as e:raise InvalidLog('ADXはUTF-8で読み込んでください。') from e
    if re.search(r'<!\s*(?:DOCTYPE|ENTITY)',text,re.I):raise InvalidLog('ADXのDTD・独自エンティティは使用できません。')
    try:root=ET.fromstring(text)
    except ET.ParseError as e:raise InvalidLog('ADXのXMLが壊れています: '+str(e)) from e
    def name(e):return e.tag.rsplit('}',1)[-1]
    if name(root)!='ADX':raise InvalidLog('ADXルートがありません。')
    containers=[e for e in root if name(e)=='RECORDS']
    if len(containers)!=1:raise InvalidLog('ADXのRECORDSは1つ必要です。')
    records=[]
    for record in containers[0]:
        if name(record)!='RECORD':raise InvalidLog('RECORDS内に不明な要素があります。')
        fields={}
        for e in record:
            if len(e):raise InvalidLog('ADX項目内の入れ子要素は扱えません。')
            k=name(e)
            if k=='APP':k='APP_'+e.get('PROGRAMID','').upper()+'_'+e.get('FIELDNAME','').upper()
            elif k=='USERDEF':k='USERDEF_'+e.get('FIELDNAME','').upper()
            if k in fields:raise InvalidLog('同じADX項目が重複しています: '+k)
            fields[k]=e.text or ''
        records.append(fields)
    if not records:raise InvalidLog('ADXに交信レコードがありません。')
    return records

def convert(data,kind,own,override=False,country_data=None,location_data=None):
    records=read_adx(data) if kind=='adx' else read_adi(data)
    lines=[];issues=[];notices=[]
    for number,f in enumerate(records,1):
        raw=json.dumps(f,ensure_ascii=False)
        try:
            used=set()
            def get(k,default=''):
                if k in f:used.add(k)
                return f.get(k,default).strip()
            date=get('QSO_DATE');time=get('TIME_ON')
            if not re.fullmatch(r'[0-9]{8}',date) or not re.fullmatch(r'[0-9]{4}(?:[0-9]{2})?',time):raise ValueError('QSO_DATE/TIME_ONが不正です。')
            dt=datetime.strptime(date+time,'%Y%m%d%H%M%S' if len(time)==6 else '%Y%m%d%H%M')
            dt+=timedelta(hours=9)
            station=get('STATION_CALLSIGN').upper()
            station_source='STATION_CALLSIGN'
            if 'STATION_CALLSIGN' not in f:
                station=f.get('OPERATOR','').strip().upper()
                station_source='OPERATOR'
            if station and station!=own:
                if not override:raise ValueError(f'自局が異なります: ADIF={station} / 指定={own}')
                notices.append(Issue(number,'自局を画面指定へ変更します。元項目: '+station_source,station));used.discard('STATION_CALLSIGN')
            call=get('CALL').upper()
            if not re.fullmatch(r'[A-Z0-9]+(?:/[A-Z0-9]+)*',call):raise ValueError('CALLがないか形式が不正です。')
            band=get('BAND').lower();freq=get('FREQ')
            frequency_band=''
            if freq:
                try:val=Decimal(freq)
                except InvalidOperation:raise ValueError('FREQが数値ではありません。')
                if not val.is_finite():raise ValueError('FREQが有限値ではありません。')
                frequency_band=next((b for low,high,b in RANGES if Decimal(low)<=val<=Decimal(high)),'')
                if not frequency_band:raise ValueError('FREQからバンドを判定できません。')
            if band:
                if band not in BANDS:raise ValueError('未対応のADIF BANDです: '+band)
                band=BANDS[band]
                if freq and band!=frequency_band:
                    raise ValueError('BANDとFREQが一致しません: '+f['BAND']+' / '+freq+' MHz。入力ファイルを確認してください。')
            elif freq:
                band=frequency_band
                notices.append(Issue(number,'FREQからBANDへ変換します。',freq))
            else:raise ValueError('BANDまたはFREQが必要です。')
            if freq:used.discard('FREQ') # actual frequency survives in extra notes
            mode=get('MODE');sub=get('SUBMODE');original=get('APP_PSLOG_MODE')
            check_pair(mode,sub)
            if mode and sub and (mode.upper() not in MODES or sub.upper() not in MODES):
                notices.append(Issue(number,'未対応のMODE/SUBMODEは原表記を保持して取り込みます。組み合わせを確認してください。',mode+' / '+sub))
            # One PSLog mode cannot encode every independent ADIF field.
            if sub or original:
                used.discard('MODE');used.discard('SUBMODE')
            # Preserve unknown modes without input restrictions.
            mode=original or sub or mode
            if not mode:raise ValueError('MODE/SUBMODEがありません。')
            his=get('QTH_INTL') or get('QTH');grid=get('GRIDSQUARE')
            code=get('APP_PSLOG_JCCJCG')
            remarks=get('COMMENT_INTL') or get('COMMENT')
            # NAME is the contacted operator's name; OPERATOR is our callsign.
            # Keep the original name fields in ADIF_EXTRA even after conversion.
            operator_name=(f.get('NAME_INTL','').strip() or f.get('NAME','').strip())
            if operator_name:
                if re.search(r'(?<!\w)OP\s*:',primary(remarks),re.I):
                    notices.append(Issue(number,'RMKSにOP:があるため保持します。入力の相手名はADIF_EXTRAで確認してください。',operator_name))
                else:
                    remarks=append_primary(remarks,'OP:'+operator_name)
                    notices.append(Issue(number,'相手の名前をRMKSのOP:へ反映します。',operator_name))
            from adif_qsl import import_marks
            remarks,qsl_notices=import_marks(f,remarks)
            notices.extend(Issue(number,message,'') for message in qsl_notices)
            from adif_paper_qsl import import_marks as import_paper_marks
            remarks,paper_notices=import_paper_marks(f,remarks)
            notices.extend(Issue(number,message,'') for message in paper_notices)
            if his and not his.isascii() and location_data is not None:
                from locations import confirmed
                original_his=his
                supplied_country=(f.get('COUNTRY_INTL') or f.get('COUNTRY') or '').strip()
                hint=country_data.lookup(call) if country_data is not None else None
                domestic=supplied_country.casefold() in ('japan','日本') if supplied_country else bool(hint and hint['country']=='Japan')
                roman=confirmed(location_data,his,code) if domestic else None
                remarks=append_primary(remarks,'QTH:'+original_his)
                his=roman or ''
                notices.append(Issue(number,'元の所在地をRMKSへ保持。'+('確認済みのローマ字表記を使用します。' if roman else '所在地DBで確定できないため国名・GLの補助へ進みます。'),original_his))
            if not his and country_data is not None:
                supplied=(f.get('COUNTRY_INTL') or f.get('COUNTRY') or '').strip()
                # Supplied country information takes precedence over a callsign hint.
                if supplied:
                    his=supplied
                    notices.append(Issue(number,'QTHが空欄のため入力ファイルの国名を使用します。',supplied))
                else:
                    hint=country_data.lookup(call)
                    if hint:
                        his=hint['country']
                        notices.append(Issue(number,'QTHが空欄のため参照DBの国名候補を補完します。交信当時の運用地を確認してください。',his))
            if grid and grid.casefold() not in his.casefold().split():his=(his+' '+grid).strip()
            my=get('APP_PSLOG_MY_QTH') or get('MY_CITY_INTL') or get('MY_CITY')
            if not my:my=get('MY_GRIDSQUARE')
            sent=get('RST_SENT');received=get('RST_RCVD')
            if any(m in mode.upper() for m in ('FT8','FT4','FT2','FREEDV')):
                sent='+00' if sent in ('0','00','-00','+0') else sent
                received='+00' if received in ('0','00','-00','+0') else received
            if len(time)==6 and time[-2:]!='00':
                remarks=append_primary(remarks,'ADIF_TIME_ON:'+time+'UTC')
                notices.append(Issue(number,'秒をRMKSへ保持し、DATE/TIMEはJSTの分精度にします。',time))
            extras={k:v for k,v in f.items() if k not in used and v}
            if extras:
                remarks=append_primary(remarks,'ADIF_EXTRA:'+json.dumps(extras,ensure_ascii=False,separators=(',',':')))
                notices.append(Issue(number,'追加項目をRMKSのADIF_EXTRAに保持します。',', '.join(extras)))
            values=[dt.strftime('%Y-%m-%d'),dt.strftime('%H:%M'),band,mode,call,sent,received,his,my,remarks,code]
            clean=[]
            for v in values:
                c=v.replace('|','｜').replace('\r','\\r').replace('\n','\\n').replace('\t','\\t')
                if any(ord(ch)<32 for ch in c):raise ValueError('制御文字が含まれています。')
                if c!=v:notices.append(Issue(number,'区切り文字・改行等をログ用の表記へ置換します。',''))
                clean.append(c)
            lines.append(ParsedLine(raw,QSO(*clean)))
        except (ValueError,OverflowError) as e:
            lines.append(ParsedLine(raw));issues.append(Issue(number,str(e),raw))
    notices.insert(0,Issue(0,'ADIFはUTCからJSTへ変換します。未使用項目はRMKSへ保持します。',''))
    return Log(lines,issues,notices,True,'\r\n'),records
