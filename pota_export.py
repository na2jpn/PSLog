"""POTA activator ADI: one file per park and UTC date; original logs unchanged."""
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re,unicodedata
from model import validate_station
from exporting import select_rows,adif_fields
from adif_modes import ADIF_VERSION
from storage import Snapshot,StorageError,ExternalChange,replace_bytes

REFERENCE='https://docs.pota.app/docs/activator_reference/logging_made_easy.html'
REFERENCE_CHECKED='2026-09-11'

@dataclass
class PotaPlan:
    sessions: list
    files: dict
    counts: dict
    warnings: list
    qsos: int

class PotaSaveFailure(StorageError):
    def __init__(self,message,saved):super().__init__(message);self.saved=saved

def normalize(value):return unicodedata.normalize('NFKC',value).strip().upper()

def park_numbers(value):
    parks=[normalize(v) for v in re.split(r'[,;\s]+',unicodedata.normalize('NFKC',value).strip()) if v]
    if not parks or any(not re.fullmatch(r'[A-Z]{1,4}-[0-9]{4,}',p) for p in parks):raise ValueError('公園番号は JA-1222 のように入力してください。複数は空白・カンマ区切りです。')
    if len(parks)!=len(set(parks)):raise ValueError('公園番号が重複しています。')
    return parks

def tag(key,value):
    if not all(32<=ord(c)<=126 for c in value):raise ValueError(f'{key}に半角以外の文字・制御文字があります。')
    return f'<{key}:{len(value)}>{value}'

def prepare_selected(sessions,rows,source_own,station,operator,parks,my_state=''):
    """Prepare POTA output from an exact, already-filtered set of rows."""
    source_own=validate_station(normalize(source_own),'');station=validate_station(normalize(station),'');operator=validate_station(normalize(operator),'')
    parks=park_numbers(parks);state=normalize(my_state)
    if state and not re.fullmatch(r'[A-Z0-9-]+',state):raise ValueError('MY_STATEは半角英数字・ハイフンで指定してください。')
    rows=list(rows)
    if any(own!=source_own for own,_,_,_ in rows):raise ValueError('検索結果に複数の自局コールが含まれています。POTA用は1つの運用コールに絞ってください。')
    if not rows:raise ValueError('条件に一致する交信がありません。')
    warnings=set();groups={}
    for own,q,path,line in rows:
        try:
            validate_station(q.call,'')
            f=adif_fields(station,q,warnings)
            # Submission fields only: arbitrary Japanese notes do not affect ADI encoding.
            f={k:v for k,v in f.items() if k in ('QSO_DATE','TIME_ON','CALL','STATION_CALLSIGN','BAND','MODE','SUBMODE','RST_SENT','RST_RCVD')}
            f['CALL']=q.call.upper();f['OPERATOR']=operator;f['MY_SIG']='POTA'
            if state:f['MY_STATE']=state
            for park in parks:
                record=dict(f,MY_SIG_INFO=park)
                text=''.join(tag(k,v) for k,v in record.items())+'<EOR>\r\n'
                groups.setdefault((park,f['QSO_DATE']),[]).append(text)
        except (ValueError,OverflowError) as e:raise ValueError(f'{path.name}:{line} {e}') from e
    header='PSLog POTA export\r\n<ADIF_VER:5>'+ADIF_VERSION+'<PROGRAMID:5>PSLOG<PROGRAMVERSION:4>1.00<EOH>\r\n'
    files={};counts={}
    for (park,date),records in sorted(groups.items()):
        name=f'{station.replace("/","-")}@{park}-{date}.adi'
        files[name]=(header+''.join(records)).encode('ascii');counts[name]=len(records)
    # Generic export warning refers to APP fields, which this purpose-specific export omits.
    notes=[]
    if warnings:notes.append('モードの補足表記はPOTA用の基本MODE・SUBMODEへ変換しました。')
    return PotaPlan(list(sessions),files,counts,notes,len(rows))

def prepare(repo,paths,source_own,station,operator,parks,start='',end='',remarks='',my_state=''):
    # Keep the direct-export validation order used before the search-result handoff was added.
    # This gives the user the actionable submission-field error (for example, missing park
    # number) even when no source log is selected, instead of the generic no-QSO message.
    source_own=validate_station(normalize(source_own),'')
    station=validate_station(normalize(station),'')
    operator=validate_station(normalize(operator),'')
    parks=park_numbers(parks)
    state=normalize(my_state)
    if state and not re.fullmatch(r'[A-Z0-9-]+',state):raise ValueError('MY_STATEは半角英数字・ハイフンで指定してください。')
    sessions,rows=select_rows(repo,paths,start,end)
    if remarks:rows=[r for r in rows if remarks.casefold() in r[1].remarks.casefold()]
    return prepare_selected(sessions,rows,source_own,station,operator,' '.join(parks),state)

def save(plan,directory):
    if not str(directory).strip():raise ValueError('保存先フォルダーを指定してください。')
    directory=Path(directory).resolve()
    if not directory.is_dir():raise ValueError('存在する保存先フォルダーを指定してください。')
    for session in plan.sessions:session.snapshot.check(session.path)
    saved=[]
    try:
        for name,data in plan.files.items():
            # A subsequent input edit stops the remaining files, with completed paths reported.
            for session in plan.sessions:session.snapshot.check(session.path)
            for i in range(10000):
                original=Path(name);path=directory/(original.stem+('' if i==0 else f'_{i:03d}')+original.suffix)
                if path.exists():continue
                try:replace_bytes(path,data,Snapshot(None,None))
                except ExternalChange:continue
                saved.append(path);break
            else:raise StorageError('出力名の連番上限に達しました。')
    except (StorageError,OSError) as e:
        raise PotaSaveFailure('出力を停止しました。作成済み '+str(len(saved))+'ファイル。\n'+str(e),saved) from e
    return saved
