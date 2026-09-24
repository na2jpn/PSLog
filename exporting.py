"""Read-only selection and non-overwriting ADIF/CSV output."""
from dataclasses import dataclass
from datetime import datetime,timedelta
from pathlib import Path
import csv,io,re,unicodedata
import xml.etree.ElementTree as ET
from storage import Snapshot,StorageError,InvalidLog,ExternalChange,replace_bytes
from search import file_identity
from time_range import boundary_datetime
from qsl_marks import tokens
from adif_modes import MODES,ADIF_VERSION,mapping
from adif_paper_qsl import fields as paper_qsl_fields
from hamlog_export_fields import name_from_remarks,qsl_from_remarks
from remarks_sections import split_for_ui

@dataclass
class ExportPlan:
    sessions: list
    rows: list
    data: bytes
    extension: str
    warnings: list

def stamp(q):return datetime.strptime(q.date+' '+q.time,'%Y-%m-%d %H:%M')
def boundary(value,upper=False):
    return boundary_datetime(value,upper,14)

BANDS={'1.8':'160m','1.9':'160m','3.5':'80m','3.8':'80m','7':'40m','10':'30m','14':'20m','18':'17m','21':'15m','24':'12m','28':'10m','29':'10m','50':'6m','144':'2m','430':'70cm','433':'70cm','1200':'23cm','2400':'13cm','5600':'6cm','10000':'3cm','24000':'1.25cm'}
def _append_field(fields,key,value):
    value=str(value or '').strip()
    if not value or not key or key=='出力しない':return
    if key in fields and fields[key]:fields[key]=fields[key]+' / '+value
    else:fields[key]=value

def adif_fields(own,q,warnings,remark_mapping=None):
    dt=stamp(q)-timedelta(hours=9)
    if dt.year<1930:raise ValueError('ADIFで扱えない年です。')
    band=BANDS.get(q.band)
    if not band:raise ValueError(f'ADIFのバンド対応が未定義です: {q.band}')
    mode=q.mode.upper();mapped=mapping(q.mode)
    if not mapped:raise ValueError(f'ADIFのMODE対応が未定義です: {q.mode}（原本は変更しません）')
    if mode not in MODES:warnings.add('モードの補足表記はAPP_PSLOG_MODEに保持し、標準MODEには対応する基本モードを出力します。')
    f={'QSO_DATE':dt.strftime('%Y%m%d'),'TIME_ON':dt.strftime('%H%M%S'),'CALL':q.call,'STATION_CALLSIGN':own,'BAND':band,'MODE':mapped[0],'RST_SENT':q.sent,'RST_RCVD':q.received,'QTH':q.his_qth,
       'APP_PSLOG_MY_QTH':q.my_qth,'APP_PSLOG_JCCJCG':q.code,'APP_PSLOG_MODE':q.mode,'APP_PSLOG_BAND':q.band}
    if remark_mapping is None:
        _append_field(f,'COMMENT',q.remarks)
    else:
        rmks1,rmks2,_extras=split_for_ui(q.remarks)
        _append_field(f,remark_mapping.get('rmks1','COMMENT'),rmks1)
        _append_field(f,remark_mapping.get('rmks2','APP_PSLOG_RMKS2'),rmks2)
    if mapped[1]:f['SUBMODE']=mapped[1]
    marks=tokens(q.remarks)
    # Only service-specific, affirmative states supported by PSLog semantics.
    # Bare LoTW is a promise, not evidence of an upload.
    if 'lotw.r' in marks:
        f.update(LOTW_QSL_SENT='Y',LOTW_QSL_RCVD='Y')
    if marks & {'eqsl','eqsl.r'}:f['EQSL_QSL_SENT']='Y'
    if 'eqsl.r' in marks:f['EQSL_QSL_RCVD']='Y'
    f.update(paper_qsl_fields(q.remarks,warnings))
    if re.fullmatch(r'[A-Ra-r]{2}[0-9]{2}(?:[A-Xa-x]{2})?(?:[0-9]{2})?',q.his_qth):f['GRIDSQUARE']=q.his_qth.upper()
    return {k:v for k,v in f.items() if v}

def adif(rows,adx=False,remark_mapping=None):
    warnings=set();records=[]
    for own,q,_,_ in rows:records.append(adif_fields(own,q,warnings,remark_mapping))
    if adx:
        root=ET.Element('ADX');header=ET.SubElement(root,'HEADER')
        for k,v in [('ADIF_VER',ADIF_VERSION),('PROGRAMID','PSLOG'),('PROGRAMVERSION','1.00')]:ET.SubElement(header,k).text=v
        container=ET.SubElement(root,'RECORDS')
        for fields in records:
            record=ET.SubElement(container,'RECORD')
            for k,v in fields.items():
                if any(ord(c)<32 or ord(c) in (0xfffe,0xffff) for c in v):raise ValueError('出力できない制御文字があります。')
                if k.startswith('APP_PSLOG_'):e=ET.SubElement(record,'APP',PROGRAMID='PSLOG',FIELDNAME=k[10:],TYPE='I')
                else:
                    if k in ('QTH','COMMENT') and not v.isascii():k+='_INTL'
                    elif not v.isascii():raise ValueError(f'{k}はASCII文字が必要です。')
                    e=ET.SubElement(record,k)
                e.text=v
        ET.indent(root);return ET.tostring(root,encoding='utf-8',xml_declaration=True),sorted(warnings)
    def tag(k,v):
        if not all(32<=ord(c)<=126 for c in v):raise ValueError('ADIに日本語・制御文字は出力できません。日本語を保持する場合はADXを選んでください。')
        return f'<{k}:{len(v)}>{v}'
    text='PSLog export\r\n<ADIF_VER:5>'+ADIF_VERSION+'<PROGRAMID:5>PSLOG<PROGRAMVERSION:4>1.00<EOH>\r\n'
    text+=''.join(''.join(tag(k,v) for k,v in f.items())+'<EOR>\r\n' for f in records)
    return text.encode('ascii'),sorted(warnings)

def hamlog(rows,remark_mapping=None):
    # Conventional 15-column CSV, without a record number or header.
    output=io.StringIO(newline='');writer=csv.writer(output,quoting=csv.QUOTE_ALL,lineterminator='\r\n');warnings=set()
    limits={3:(3,12),4:(3,12),5:(7,16),6:(4,16),10:(12,64),11:(28,128),12:(54,254),13:(54,254)}
    for own,q,path,line in rows:
        rmks1,rmks2,_extras=split_for_ui(q.remarks)
        remark1=q.remarks if remark_mapping is None else ''
        include_identity=True if remark_mapping is None else bool(remark_mapping.get('hamlog_identity',True))
        remark2=f'MYCALL:{own} MYQTH:{q.my_qth}'.strip() if include_identity else ''
        if remark_mapping is not None:
            for key,value in (('rmks1',rmks1),('rmks2',rmks2)):
                target=remark_mapping.get(key,'Remarks1' if key=='rmks1' else 'Remarks2')
                if not value or target=='出力しない':continue
                if target=='Remarks1':remark1=(remark1+' '+value).strip()
                elif target=='Remarks2':remark2=(remark2+' '+value).strip()
        f=[q.call,q.date.replace('-','/'),q.time+'J',q.sent,q.received,q.band,q.mode,q.code,'','','',q.his_qth,remark1,remark2,'']
        f[9]=qsl_from_remarks(q.remarks,warnings);f[10]=name_from_remarks(q.remarks,warnings)
        if re.fullmatch(r'[A-Ra-r]{2}[0-9]{2}(?:[A-Xa-x]{2})?',q.his_qth):f[8]=q.his_qth.upper()
        for i,v in enumerate(f):
            if any(ord(c)<32 for c in v):raise ValueError(f'{path.name}:{line} 制御文字があります。')
            try:length=len(v.encode('cp932'))
            except UnicodeEncodeError as e:raise ValueError(f'{path.name}:{line} CP932で表現できない文字があります。') from e
            if i in limits:
                default,maximum=limits[i]
                if length>maximum:raise ValueError(f'{path.name}:{line} CSVの第{i+1}列がHAMLOG最大幅を超えます。切り捨てず停止しました。')
                if length>default:warnings.add('HAMLOGの初期項目幅を超えるデータがあります。読み込み前に「データ項目の幅変更」で拡張が必要です。')
        writer.writerow(f)
    warnings.add('HAMLOGの周波数欄には原本のBAND値を出力します。実際の交信周波数ではありません。')
    if remark_mapping is None or remark_mapping.get('hamlog_identity',True):
        warnings.add('QSL欄は判別できる紙カード情報、Name欄は明確なOP:を反映します。電子QSLとRMKS原文はRemarks1、自局とMY QTHはRemarks2に保持します。DX等のフラグは空欄です。')
    else:
        warnings.add('QSL欄は判別できる紙カード情報、Name欄は明確なOP:を反映します。MYCALL/MYQTHのRemarks2出力は無効です。DX等のフラグは空欄です。')
    warnings.add('CSVは互換性確認用の暫定実装です。15列のマッピングと文字コードはHAMLOG実機での再読込検証が未完了です。')
    return output.getvalue().encode('cp932'),sorted(warnings)

def select_rows(repo,paths,start='',end='',latest=None):
    lo=boundary(start,False) if start else None;hi=boundary(end,True) if end else None
    if lo and hi and lo>hi:raise ValueError('開始日時は終了日時以前にしてください。')
    if latest is not None and latest<1:raise ValueError('最新件数は1以上です。')
    sessions=[];rows=[]
    for path in sorted(set(Path(p).resolve() for p in paths)):
        identity=file_identity(path)
        if not identity:raise ValueError('自局を特定できないログ名です。')
        s=repo.open(path)
        if s.snapshot.data is None:raise StorageError('選択したログが見つかりません。')
        if s.log.issues:raise InvalidLog(f'{path.name}に要確認行があります。出力を停止しました。')
        sessions.append(s)
        for line,q in s.log.records:
            dt=stamp(q)
            if lo and dt<lo or hi and dt>hi:continue
            rows.append((identity[1],q,path,line))
    rows.sort(key=lambda r:(stamp(r[1]),str(r[2]),r[3]))
    if latest is not None:rows=rows[-latest:]
    if not rows:raise ValueError('出力する交信がありません。')
    return sessions,rows

def prepare_rows(sessions,rows,format='adi',remark_mapping=None):
    """Prepare an export from an exact, already-selected set of QSO rows.

    Used by the log-search handoff so CALL/BAND/MODE/QTH/RMKS filters are
    preserved exactly instead of widening the selection back to whole files.
    """
    if format not in ('adi','adx','csv'):raise ValueError('未対応の出力形式です。')
    rows=list(rows)
    if not rows:raise ValueError('出力する交信がありません。')
    data,warnings=hamlog(rows,remark_mapping) if format=='csv' else adif(rows,format=='adx',remark_mapping)
    return ExportPlan(list(sessions),rows,data,format,warnings)

def prepare(repo,paths,format='adi',start='',end='',latest=None,remark_mapping=None):
    sessions,rows=select_rows(repo,paths,start,end,latest)
    return prepare_rows(sessions,rows,format,remark_mapping)

def save(plan,directory):
    directory=Path(directory).resolve()
    if not directory.is_dir():raise ValueError('存在する出力先フォルダーを指定してください。')
    for s in plan.sessions:s.snapshot.check(s.path)
    own=plan.rows[0][0] if len({r[0] for r in plan.rows})==1 else 'multi'
    stem='PSLog_'+own.replace('/','-')+'_'+datetime.now().strftime('%Y%m%d%H%M%S')
    for n in range(10000):
        path=directory/(stem+('' if n==0 else f'_{n:03d}')+'.'+plan.extension)
        if path.exists():continue
        try:replace_bytes(path,plan.data,Snapshot(None,None))
        except ExternalChange:continue
        return path
    raise StorageError('出力ファイル名を確保できません。')
