"""SOTA CSV V2 based on SOTA Japan/HOTACA documentation; no original writes."""
from dataclasses import dataclass
from datetime import timedelta
import csv,io,re,unicodedata
from model import validate_station
from exporting import select_rows,stamp
from pota_export import save, PotaSaveFailure as SaveFailure
from time_range import prefix_boundary

@dataclass
class Selection:
    sessions: list
    rows: list

@dataclass
class SotaPlan:
    sessions: list
    files: dict
    qsos: int
    warnings: list

def norm(value):return unicodedata.normalize('NFKC',value).strip().upper()
def summit(value,optional=False):
    value=norm(value)
    if optional and not value:return ''
    if not re.fullmatch(r'[A-Z0-9]+/[A-Z]{2}-[0-9]{3}',value):raise ValueError('山頂番号は JA/ST-001 のように入力してください。')
    return value

def key(row):return (str(row[2]),row[3])

def minute_boundary(value,upper=False):
    return prefix_boundary(value,upper,12)

def select(repo,paths,own,start='',end='',remarks=''):
    own=validate_station(norm(own),'')
    sessions,rows=select_rows(repo,paths,minute_boundary(start,False) if start else '',minute_boundary(end,True) if end else '')
    if any(r[0]!=own for r in rows):raise ValueError('出力元の自局と異なるログが含まれています。')
    if remarks:rows=[r for r in rows if remarks.casefold() in r[1].remarks.casefold()]
    if not rows:raise ValueError('条件に一致する交信がありません。')
    return Selection(sessions,rows)

BANDS={a:b for a,b in [('1.8','1.8MHz'),('1.9','1.8MHz'),('3.5','3.5MHz'),('3.8','3.5MHz'),('7','7MHz'),('10','10MHz'),('14','14MHz'),('18','18MHz'),('21','21MHz'),('24','24MHz'),('28','28MHz'),('29','28MHz'),('50','50MHz'),('144','144MHz'),('430','433MHz'),('433','433MHz'),('1200','1240MHz'),('2400','2.3GHz'),('5600','5.6GHz'),('10000','10GHz')]}
DATA={'RTTY','RTY','PSK','PSK31','PSK-31','DIG','DATA','PSK63','JT9','JT65','FT8','FT4','FT2','FSQ','MFSK','MSK144','OLIVIA','WSPR'}
DV={'DV','FUSION','DSTAR','D-STAR','DMR','C4FM','FREEDV','DIGITALVOICE'}
def mode(value):
    value=norm(value)
    if value in ('AM','SSB','CW','FM'):return value
    if value in ('USB','LSB'):return 'SSB'
    if value in DATA or any(base in value for base in ('FT8','FT4','FT2')):return 'Data'
    if value in DV or 'FREEDV' in value:return 'DV'
    if value in ('SSTV','OTHER'):return 'Other'
    raise ValueError('SOTAモードの対応が未定義です: '+value)

def prepare(selection,kind,own_ref='',refs=None,comment=''):
    if kind not in ('activator','chaser','s2s'):raise ValueError('運用種別を選択してください。')
    own_ref=summit(own_ref) if kind!='chaser' else ''
    refs=refs or {};notes=[]
    if any(ord(c)<32 or ord(c)>126 for c in comment):raise ValueError('提出用メモは半角英数字・記号で入力してください。')
    clean=comment.replace(',','_').replace('"',"'")
    if clean!=comment:notes.append('提出用メモのカンマを _、二重引用符を単一引用符へ置換しました。')
    groups={}
    for row in selection.rows:
        own,q,path,line=row
        try:
            other=summit(refs.get(key(row),''),optional=kind=='activator')
            if own_ref and other==own_ref:raise ValueError('自局と相手が同じ山頂番号です。')
            dt=stamp(q)-timedelta(hours=9)
            if not 2000<=dt.year<=2099:raise ValueError('このCSVの2桁年出力は2000～2099年に対応します。')
            band=BANDS.get(q.band)
            if not band:raise ValueError('SOTAバンドの対応が未定義です: '+q.band)
            fields=['V2',validate_station(own,''),own_ref,dt.strftime('%d/%m/%y'),dt.strftime('%H%M'),band,mode(q.mode),validate_station(q.call,''),other,clean]
            groups.setdefault(dt.strftime('%Y%m%d'),[]).append(fields)
        except (ValueError,OverflowError) as e:raise ValueError(f'{path.name}:{line} {e}') from e
    if not groups:raise ValueError('出力する交信がありません。')
    files={}
    own=selection.rows[0][0].replace('/','-');ref=own_ref.replace('/','-') or 'chaser'
    for date,rows in sorted(groups.items()):
        out=io.StringIO(newline='');csv.writer(out,lineterminator='\r\n').writerows(rows)
        files[f'SOTA_{own}_{kind}_{ref}_{date}.csv']=out.getvalue().encode('ascii')
    return SotaPlan(selection.sessions,files,len(selection.rows),notes)
