"""Free-radio (フリラ) log identity, validation, and discovery for PSLog 1.14."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re
import unicodedata

from input_normalization import date_text,time_text,machine_text,jccjcg_code
from model import QSO,InputError
from storage import Snapshot,StorageError,operation_lock,replace_bytes

FREE_TYPES=('CB','LCR','DCR','UHFCB','特小','BLU','ETC')
TYPE_RADIO={
    'CB':('27','AM'),
    'LCR':('142/146','DIGITAL'),
    'DCR':('351','DIGITAL'),
    'UHFCB':('422','FM'),
    '特小':('422','FM'),
    'BLU':('2400','DIGITAL'),
    'ETC':('N/A','N/A'),
}
_FREE_NAME=re.compile(r'^(\d{4})_([^_]+)_(CB|LCR|DCR|UHFCB|特小|BLU|ETC)(?:_(.*))?\.txt$')
_FORBIDDEN_FILENAME=re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def katakana_to_hiragana(text):
    text=unicodedata.normalize('NFKC',str(text or ''))
    out=[]
    for ch in text:
        code=ord(ch)
        if 0x30A1 <= code <= 0x30F6:
            out.append(chr(code-0x60))
        elif ch=='ヴ':out.append('ゔ')
        else:out.append(ch)
    return ''.join(out)


def normalize_free_call(value):
    value=katakana_to_hiragana(value).strip()
    return ''.join(ch.upper() if 'a'<=ch.lower()<='z' else ch for ch in value)


def validate_free_call(value,label='自局コールサイン'):
    value=normalize_free_call(value)
    if not value:
        raise ValueError(label+'を入力してください。')
    # Hiragana (including iteration marks) plus ASCII letters/digits only.
    if not all(('ぁ'<=c<='ゖ') or c in 'ゝゞ' or ('A'<=c<='Z') or c.isdigit() and c.isascii() for c in value):
        raise ValueError(label+'は平仮名と英数字で入力してください。漢字・カナは使用しません。')
    return value


def validate_model(value):
    """Validate the optional free-radio model name.

    Model is descriptive metadata, not an identity requirement.  Blank is
    therefore valid; when present it must still be safe for use in a filename.
    """
    value=unicodedata.normalize('NFKC',str(value or '')).strip()
    if not value:return ''
    if _FORBIDDEN_FILENAME.search(value) or value.endswith((' ','.')):
        raise ValueError('機種名にファイル名として使えない文字があります。')
    return value


def radio_values(kind):
    if kind not in TYPE_RADIO:raise ValueError('フリラの種類を選択してください。')
    return TYPE_RADIO[kind]


def free_filename(year,call,kind,model):
    call=validate_free_call(call);model=validate_model(model)
    if kind not in FREE_TYPES:raise ValueError('フリラの種類を選択してください。')
    stem=f'{int(year):04d}_{call}_{kind}'
    if model:stem+='_'+model
    return stem+'.txt'


def free_path(repo,call,kind,model,date):
    year=datetime.strptime(date,'%Y-%m-%d').year
    return repo.free_book/free_filename(year,call,kind,model)


def free_file_identity(path):
    m=_FREE_NAME.fullmatch(Path(path).name)
    if not m:return None
    return m.group(1),m.group(2),m.group(3),m.group(4) or ''


def free_files(repo,call='',kind='',model=None):
    call=normalize_free_call(call) if call else ''
    result=[]
    for path in repo.free_book.glob('*.txt'):
        ident=free_file_identity(path)
        if not ident:continue
        _year,actual_call,actual_kind,actual_model=ident
        if call and actual_call!=call:continue
        if kind and actual_kind!=kind:continue
        if model is not None and actual_model!=model:continue
        result.append(path)
    return sorted(result,key=lambda p:p.name.casefold())


def free_station_calls(repo):
    return sorted({i[1] for p in free_files(repo) if (i:=free_file_identity(p))},key=str.casefold)


def free_models(repo,kind=''):
    values={}
    for p in free_files(repo):
        ident=free_file_identity(p)
        if not ident:continue
        _year,_call,k,model=ident
        if kind and k!=kind:continue
        if model:values.setdefault(k,set()).add(model)
    if kind:return sorted(values.get(kind,set()),key=str.casefold)
    return {k:sorted(v,key=str.casefold) for k,v in values.items()}


def free_profiles(repo):
    """Unique (call, kind, model) profiles, newest year first in presentation metadata."""
    profiles={}
    for p in free_files(repo):
        ident=free_file_identity(p)
        if not ident:continue
        year,call,kind,model=ident
        key=(call,kind,model)
        profiles.setdefault(key,set()).add(year)
    return [
        {'call':call,'kind':kind,'model':model,'years':sorted(years,reverse=True)}
        for (call,kind,model),years in sorted(profiles.items(),key=lambda item:(item[0][0].casefold(),item[0][1],item[0][2].casefold()))
    ]


def ensure_free_logbook(repo,call,kind,model,date):
    path=free_path(repo,call,kind,model,date)
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():return path
    with operation_lock(repo.free_book):
        snap=Snapshot.read(path)
        if snap.data is None:
            replace_bytes(path,b'\xef\xbb\xbf',snap)
    return path


class FreeQSO(QSO):
    """QSO record with free-radio callsign rules while retaining 11 PSLog fields."""
    def validate(self):
        try:self.date=date_text(self.date)
        except ValueError as e:raise InputError('date',str(e)) from e
        try:self.time=time_text(self.time)
        except ValueError as e:raise InputError('time',str(e)) from e
        try:self.call=validate_free_call(self.call,'相手コールサイン')
        except ValueError as e:raise InputError('call',str(e)) from e
        self.band=machine_text(self.band)
        self.mode=machine_text(self.mode,upper=True)
        self.sent=machine_text(self.sent);self.received=machine_text(self.received)
        self.code=jccjcg_code(self.code)
        if not self.band:raise InputError('band','BANDを入力してください。')
        if not self.mode:raise InputError('mode','MODEを入力してください。')
        for field,value in vars(self).items():
            if any(c in value for c in '|\r\n\t\x00'):
                raise InputError(field,field.upper()+'内に |、改行、タブは使用できません。')

    def to_ps(self):
        self.validate();values=list(vars(self).values());values[1]+=' JST'
        return ' | '.join(values)+' '+chr(92)*2
