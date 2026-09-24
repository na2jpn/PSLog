"""PSLog 1.00 input model. Historical reads use storage.parse separately."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import re
from input_normalization import callsign as normalize_callsign, date_text, machine_text, time_text, jccjcg_code

class InputError(ValueError):
    def __init__(self,field,message):
        super().__init__(message);self.field=field

JST = timezone(timedelta(hours=9))
QSL_FLAGS = {'LoTW.R','BURO.R','Direct.R','CARD.R','1way.R','eQSL.R','hQSL.R','QRZ.R','Other.R'}

def now_jst():
    return datetime.now(JST)

def validate_station(call, suffix):
    call = normalize_callsign(call)
    if not re.fullmatch(r'[A-Z0-9]+(?:/[A-Z0-9]+)*', call):
        raise ValueError('自局コールサインを英数字と / で入力してください。')
    if re.search(r'[<>:"/\\|?*\x00-\x1f]', suffix) or suffix.endswith((' ', '.')):
        raise ValueError('ログ付与文字にファイル名として使えない文字があります。')
    return call

def mode_family(mode):
    mode = mode.upper()
    for family in ('FREEDV','FT8','FT4','FT2','RTTY','SSTV','SSB','CW','FM','AM'):
        if family in mode: return family
    return None

def default_rst(mode):
    return {'SSB':'59','FM':'59','AM':'59','CW':'599','RTTY':'599','SSTV':'595',
            'FT8':'-01','FT4':'-01','FT2':'-01','FREEDV':'+00'}.get(mode_family(mode))

@dataclass
class QSO:
    date: str
    time: str
    band: str
    mode: str
    call: str
    sent: str
    received: str
    his_qth: str
    my_qth: str
    remarks: str
    code: str = ''

    @property
    def confirmed(self):
        from qsl_marks import tokens
        return bool(tokens(self.remarks) & {x.casefold() for x in QSL_FLAGS})

    def validate(self):
        try:self.date = date_text(self.date)
        except ValueError as e:raise InputError('date',str(e)) from e
        try:self.time = time_text(self.time)
        except ValueError as e:raise InputError('time',str(e)) from e
        self.call = normalize_callsign(self.call)
        self.band = machine_text(self.band)
        self.mode = machine_text(self.mode,upper=True)
        self.sent = machine_text(self.sent)
        self.received = machine_text(self.received)
        self.code = jccjcg_code(self.code)
        if not re.fullmatch(r'[A-Z0-9]+(?:/[A-Z0-9]+)*', self.call):
            raise InputError('call','相手コールサインを入力してください。')
        for field in ('band','mode'):
            if not getattr(self,field).strip():raise InputError(field,field.upper()+'を入力してください。')
        for field,value in vars(self).items():
            if any(c in value for c in '|\r\n\t\x00'):
                raise InputError(field,field.upper()+'内に |、改行、タブは使用できません。')
        # Both blank means no report was exchanged (e.g. grid-only contests).
        # Never invent a signal report to satisfy the normal mode defaults.
        if self.sent == '' and self.received == '':return
        mode = mode_family(self.mode)
        pattern = (r'[1-5][1-9]' if mode in ('SSB','FM','AM') else
                   r'[1-5][1-9][1-9]' if mode in ('CW','RTTY') else
                   r'[1-5][1-9][1-5]' if mode == 'SSTV' else None)
        if pattern:
            for field,label in (('sent','送信RST'),('received','受信RST')):
                if not re.fullmatch(pattern,getattr(self,field)):raise InputError(field,label+': Modeに合うレポートを入力してください。')
        if mode in ('FT8','FT4','FT2','FREEDV'):
            self.sent = '+00' if self.sent in ('00','0','-00') else self.sent
            self.received = '+00' if self.received in ('00','0','-00') else self.received
            for field,label in (('sent','送信RST'),('received','受信RST')):
                if not re.fullmatch(r'[+-][0-9]{2}',getattr(self,field)):raise InputError(field,label+': デジタルレポートは +00 や -12 の形式で入力してください。')

    def to_ps(self):
        self.validate()
        values = list(vars(self).values())
        values[1] += ' JST'
        return ' | '.join(values) + ' ' + chr(92)*2

LOCATIONS = []  # Verified JCC/JCG master is a subsequent implementation step.

def preserve_grid(old, new):
    match = re.match(r'^([A-Ra-r]{2}\d{2}(?:[A-Xa-x]{2}(?:\d{2})?)?)(?:\s|$)', old)
    return (match.group(1) + ' ' if match else '') + new
