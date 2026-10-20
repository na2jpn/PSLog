"""Reviewed dated names and entity validity. No automatic historical log rewrite."""
import json,re,sys
from pathlib import Path
from datetime import datetime,timezone,timedelta


def load_history(root=None):
    relative=Path('config/db/country_history.json')
    p=Path(root)/relative if root else Path(__file__).parent/relative
    if not p.exists():p=Path(getattr(sys,'_MEIPASS',Path(__file__).parent))/relative
    data=json.loads(p.read_text('utf-8'))
    if data.get('schema')!=1:raise ValueError('国名履歴DBの形式が違います。')
    return data


def key(text):
    return re.sub(r'[^a-z0-9]','',str(text).casefold().replace('ü','u').replace('ı','i'))


def historic_name(name,when,history):
    day=str(when or datetime.now(timezone(timedelta(hours=9))).date())[:10]
    for row in history.get('names',[]):
        if key(name) in {key(x) for x in [row['canonical']]+row['aliases']}:
            values=[v for v in row['periods'] if v['from']<=day and (not v.get('until') or day<v['until'])]
            if len(values)==1:return values[0]['name']
    return name


def utc_stamp(qso):
    return datetime.strptime(qso.date+' '+qso.time,'%Y-%m-%d %H:%M').replace(tzinfo=timezone(timedelta(hours=9))).astimezone(timezone.utc)


def valid_entity(row,qso):
    t=utc_stamp(qso)
    day=t.date().isoformat()
    if row.get("from_date") and day<row["from_date"]:return False
    if row.get("through_date") and day>row["through_date"]:return False
    for field,lower in (('from_utc',True),('until_utc',False)):
        if row.get(field):
            boundary=datetime.fromisoformat(row[field].replace('Z','+00:00'))
            if (lower and t<boundary) or (not lower and t>=boundary):return False
    return True
