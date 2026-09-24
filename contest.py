"""Contest working data never modifies canonical QSO records."""
import re,unicodedata
from sota_export import select as single_select
from qsl_marks import TOKEN
from remarks_sections import primary

FORMATS=('JARL R1.0','JARL R2.1','Cabrillo','zLog令和版CSV','所定様式PDF')
def candidates(remarks,filter_text=''):
    text=unicodedata.normalize('NFKC',primary(remarks))
    if filter_text:text=re.sub(re.escape(unicodedata.normalize('NFKC',filter_text)),' ',text,flags=re.I)
    text=TOKEN.sub(' ',text)
    # Only isolated alphanumerics containing digits; never split a call/date/frequency.
    return list(dict.fromkeys(m.group().upper() for m in re.finditer(r'(?<![\w./:+-])[A-Za-z]*[0-9]+[A-Za-z]*(?![\w./:+-])',text)))

def entries(selection,draft):
    result=[]
    for own,q,path,line in selection.rows:
        values=draft.get((str(path),line),{})
        result.append(dict(own_location=values.get('own_location',''),island=values.get('island',''),other_station=values.get('other_station',''),communication=values.get('communication',''),qso_power=values.get('qso_power',''),cq_entity=values.get('cq_entity',''),remote_mode=values.get('remote_mode',''),own=own,rst_sent=values.get('rst_sent',q.sent),rst_received=values.get('rst_received',q.received),operator_name=values.get('operator_name',''),operator_birthdate=values.get('operator_birthdate',''),operator_yl=values.get('operator_yl',False),contest_band=values.get('contest_band',''),checklog=values.get('checklog',False),date=q.date,time=q.time,sent=values.get('sent',''),my_grid=values.get('my_grid'),his_grid=values.get('his_grid'),tx=values.get('tx'),call=q.call,band=q.band,mode=q.mode,exchange=values.get('received',''),area=values.get('area') or None,prefix=values.get('prefix') or None,country=values.get('country') or None,continent=values.get('continent') or None))
    return result


def select_logs(repo,paths,own,start='',end='',remarks='',joint=False):
    if not joint:return single_select(repo,paths,own,start,end,remarks)
    from sota_export import minute_boundary,Selection,norm
    from exporting import select_rows
    from model import validate_station
    from contest_regional import base_call
    own=validate_station(norm(own),'');base=base_call(own)
    if own not in (base,base+'/8'):raise ValueError('胆振日高の統合元は基本コール又は/8です。')
    sessions,rows=select_rows(repo,paths,minute_boundary(start,False) if start else '',minute_boundary(end,True) if end else '')
    if any(r[0] not in (base,base+'/8') for r in rows):raise ValueError('異なる基本コール又は/8以外のログを統合できません。')
    if remarks:rows=[r for r in rows if remarks.casefold() in r[1].remarks.casefold()]
    if not rows:raise ValueError('条件に一致する交信がありません。')
    return Selection(sessions,rows)
