"""Explicit conventional HAMLOG CSV mapping; no record-number overwrite."""
import csv,io,re,json,unicodedata
from datetime import datetime,timedelta
from decimal import Decimal,InvalidOperation
from storage import Log,ParsedLine,Issue,InvalidLog
from model import QSO
from remarks_sections import append_primary
from adif_import import RANGES

COLUMNS=['Call','Date','Time','His','My','Freq','Mode','Code','GL','QSL','Name','QTH','Remarks1','Remarks2','Flags']
JAPAN=re.compile(r'(?:J[A-S][0-9]|7[J-N][0-9]|8[J-N][0-9])[A-Z]{1,4}(?:/(?:[0-9]|P|M|QRP|JD1))?',re.I)
GRID=re.compile(r'[A-R]{2}[0-9]{2}(?:[A-X]{2})?(?:[0-9]{2})?',re.I)

def convert(data,encoding='cp932',timezone='',century=2000,location_data=None,country_data=None):
    if encoding not in ('cp932','utf-8-sig'):raise ValueError('CSVの文字コード指定が不正です。')
    if timezone not in ('','JST','UTC'):raise ValueError('CSVの時刻指定が不正です。')
    if century not in (1900,2000):raise ValueError('2桁年の世紀指定が不正です。')
    if data.startswith(b'\xef\xbb\xbf'):encoding='utf-8-sig'
    try:text=data.decode(encoding)
    except UnicodeDecodeError as e:raise InvalidLog('指定した文字コードでCSVを読めません。文字コードを確認してください。') from e
    reader=csv.reader(io.StringIO(text,newline=''),strict=True,skipinitialspace=True)
    records=[];lines=[];issues=[];notices=[];width=None
    try:
        for row in reader:
            if not row or all(not c.strip() for c in row):continue
            physical=reader.line_num
            # Column layout never changes mid-file.
            if width is None:
                if len(row) not in (15,16):raise InvalidLog('CSVは15列、またはレコード番号付き16列が必要です。')
                width=len(row)
            if len(row)!=width:raise InvalidLog(f'CSV {physical}行付近で列数が変わっています。')
            records.append({'line_end':physical,'fields':row[:]})
            raw=json.dumps(row,ensure_ascii=False);number=len(records)
            try:
                if width==16:
                    if not re.fullmatch('[0-9]+',row[0].strip()):raise ValueError('レコード番号が数値ではありません。')
                    record_number=row[0].strip();row=row[1:]
                else:record_number=''
                f=dict(zip(COLUMNS,(c.strip() for c in row)))
                f['QSL']=row[9] # Position, including leading spaces, is meaningful.
                call=unicodedata.normalize('NFKC',f['Call']).upper()
                if not re.fullmatch(r'[A-Z0-9]+(?:/[A-Z0-9]+)*',call):raise ValueError('Callが不正です。')
                d=unicodedata.normalize('NFKC',f['Date']);m=re.fullmatch(r'([0-9]{2}|[0-9]{4})[/-]([0-9]{1,2})[/-]([0-9]{1,2})',d)
                if not m:raise ValueError('DateはYY/MM/DDまたはYYYY/MM/DDが必要です。')
                year=int(m[1])+(century if len(m[1])==2 else 0)
                if len(m[1])==2:notices.append(Issue(number,f'2桁年を{year}年として読み込みます。',f['Date']))
                t=unicodedata.normalize('NFKC',f['Time']).upper();mt=re.fullmatch(r'([0-9]{1,2}):([0-9]{2})(?::([0-9]{2}))?\s*([JU])?',t)
                if not mt:raise ValueError('Timeはhh:mmJ / hh:mmU形式が必要です。')
                zone={'J':'JST','U':'UTC'}.get(mt[4],timezone)
                if not zone:raise ValueError('時刻にJ/Uがありません。画面でJST/UTCを指定してください。')
                dt=datetime(year,int(m[2]),int(m[3]),int(mt[1]),int(mt[2]),int(mt[3] or 0))
                if zone=='UTC':dt+=timedelta(hours=9)
                if not mt[4]:notices.append(Issue(number,'時刻末尾なし：画面指定の'+zone+'として読み込みます。',''))
                freq=unicodedata.normalize('NFKC',f['Freq'])
                try:value=Decimal(freq)
                except InvalidOperation:raise ValueError('Freqが数値ではありません。衛星等の複合表記は未対応です。')
                if not value.is_finite():raise ValueError('Freqが有限値ではありません。')
                # Representative PSLog values as well as actual MHz frequencies.
                representatives={'5':'5','10':'10','18':'18','24':'24','1.9':'1.8','3.8':'3.5','1200':'1200','2400':'2400','5600':'5600','10000':'10000','24000':'24000'}
                band=next((b for k,b in representatives.items() if Decimal(k)==value),'') or next((b for lo,hi,b in RANGES if Decimal(lo)<=value<=Decimal(hi)),'')
                if not band:raise ValueError('Freqからバンドを判定できません。')
                mode=unicodedata.normalize('NFKC',f['Mode'])
                if not mode:raise ValueError('Modeが空欄です。')
                sent,received=f['His'],f['My']
                if any(k in mode.upper() for k in ('FT8','FT4','FT2','FREEDV')):
                    sent='+00' if sent in ('0','00','-00','+0') else sent
                    received='+00' if received in ('0','00','-00','+0') else received
                from hamlog_export_fields import name_from_remarks
                same_name=f['Name'] and name_from_remarks(f['Remarks1'],set())==f['Name']
                remarks=f['Remarks1']
                if f['Name'] and not same_name:remarks=append_primary(remarks,'OP:'+f['Name'])
                if f['Remarks2']:remarks=append_primary(remarks,f['Remarks2'])
                qth=f['QTH'];domestic=bool(JAPAN.fullmatch(call))
                if qth and not qth.isascii():
                    from locations import confirmed
                    roman=confirmed(location_data,qth,f['Code']) if location_data else None
                    remarks=append_primary(remarks,'QTH:'+qth);qth=roman or ('Japan' if domestic else '')
                    notices.append(Issue(number,'日本語所在地はRMKSへ保持。'+('確認済み所在地DBのローマ字を使用します。' if roman else '確認済み表記がないため国名またはGLのみとします。'),'') )
                if not qth and country_data:
                    hint=country_data.lookup(call)
                    if hint:
                        qth=hint['country'];notices.append(Issue(number,'国名参照DBの候補を補完します。運用地を確認してください。',qth))
                grid=f['GL']
                if grid:
                    if not GRID.fullmatch(grid):raise ValueError('GLの形式が不正です。')
                    if grid.casefold() not in qth.casefold().split():qth=(grid+' '+qth).strip()
                code=f['Code'] if domestic and re.fullmatch('[0-9]{4,6}',f['Code']) else ''
                extra={k:f[k] for k in ('Freq','QSL','Flags') if f[k]}
                if f['Code'] and not code:extra['Code']=f['Code']
                if record_number:extra['RecordNumber']=record_number
                if mt[3] and mt[3]!='00':extra['Time']=f['Time'];extra['Timezone']=zone
                if extra:remarks=append_primary(remarks,'HAMLOG_EXTRA:'+json.dumps(extra,ensure_ascii=False,separators=(',',':')))
                values=[dt.strftime('%Y-%m-%d'),dt.strftime('%H:%M'),band,mode,call,sent,received,qth,'',remarks,code]
                clean=[]
                for v in values:
                    c=v.replace('|','｜').replace('\r','\\r').replace('\n','\\n').replace('\t','\\t')
                    if any(ord(ch)<32 for ch in c):raise ValueError('制御文字があります。')
                    if c!=v:notices.append(Issue(number,'区切り文字・改行をログ用表記へ置換します。',''))
                    clean.append(c)
                lines.append(ParsedLine(raw,QSO(*clean)))
            except (ValueError,OverflowError) as e:lines.append(ParsedLine(raw));issues.append(Issue(number,str(e),raw))
    except csv.Error as e:raise InvalidLog(f'CSVの引用符・レコード構造が壊れています（{reader.line_num}行付近）。') from e
    if not records:raise InvalidLog('CSVに交信がありません。')
    notices.insert(0,Issue(0,f'CSV {width}列 / {encoding}。列対応と内容を確認してください。',' → '.join(COLUMNS)))
    notices.insert(1,Issue(0,'CSVにはMY QTHの専用列がないため空欄にします。QSL・フラグ・元周波数はRMKSへ保持します。',''))
    return Log(lines,issues,notices,True,'\r\n'),{'format':'HAMLOG CSV','encoding':encoding,'century':century,'timezone_if_missing':timezone,'records':records,'notices':[{'record':n.line,'reason':n.reason,'detail':n.raw} for n in notices]}
