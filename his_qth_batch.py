"""Bounded, cancellable MIC lookup with guarded, reviewed log maintenance."""
from dataclasses import dataclass,replace
from pathlib import Path
import hashlib,json,re,time,unicodedata,queue,threading
from urllib.request import Request,urlopen
from urllib.parse import urlencode
from urllib.error import HTTPError,URLError
from storage import StorageError,Snapshot,replace_bytes,operation_lock
from logbook_sources import amateur_log_files,file_identity,base_station_call
from locations import load as load_locations,qth_for_row
from jccjcg_batch import unique_row_for_code,prefecture_qth_from_rmks

API='https://www.tele.soumu.go.jp/musen/list'
from internet_common import USER_AGENT,request_bytes,InternetError,excerpt
DOMESTIC=re.compile(r'(?:(?:J[A-S])\d|[78][J-N]\d)\w+',re.ASCII)

class StopLookup(StorageError):pass

LOOKUP_DEADLINE=15
_LOOKUP_SLOT=threading.BoundedSemaphore(1)
MIC_HEADERS={'Referer':'https://2jp.org','Content-Type':'application/x-www-form-urlencoded'}

def location_url(call):
    return API+'?'+urlencode({'ST':1,'OF':2,'DA':0,'OW':'AT','SK':2,'DC':1,'SC':1,'MC':1,'MA':call.upper()})

def request_location(call,opener=None):
    if '/' in call or not DOMESTIC.fullmatch(call.upper()):raise ValueError('日本の移動表記なしの局だけを照会できます。')
    url=location_url(call);started=time.monotonic()
    if not _LOOKUP_SLOT.acquire(blocking=False):raise StopLookup('前の総務省API通信が終了していません。連続照会は行いません。\nURL: '+url)
    result=queue.Queue(maxsize=1)
    def fetch():
        try:result.put((True,request_bytes(url,'application/json',opener or urlopen,headers=MIC_HEADERS)))
        except Exception as e:result.put((False,e))
        finally:_LOOKUP_SLOT.release()
    worker=threading.Thread(target=fetch,name='PSLog-MIC-HTTP',daemon=True)
    try:worker.start()
    except Exception:
        _LOOKUP_SLOT.release();raise
    try:ok,data=result.get(timeout=LOOKUP_DEADLINE)
    except queue.Empty:
        raise StopLookup(f'総務省API 照会全体の制限時間超過（{LOOKUP_DEADLINE}秒）\n経過: {time.monotonic()-started:.1f}秒\nURL: {url}\nDNS・接続・応答のどの段階で停滞したかは未確定です。取得結果は破棄します。') from None
    if not ok:
        cls=StopLookup if not isinstance(data,InternetError) or data.status in (None,403,429,503) else StorageError
        raise cls(f'総務省API 経過: {time.monotonic()-started:.1f}秒\nURL: {url}\n{type(data).__name__}: {data}') from data
    try:return json.loads(data.decode('utf-8-sig'))
    except (ValueError,UnicodeError) as e:
        raise StopLookup('総務省API応答解析エラー\nURL: '+url+'\n'+type(e).__name__+': '+str(e)+'\n応答冒頭: '+excerpt(data)) from e


def license_day(value,last=False):
    """Normalize Gregorian/Japanese era dates only when a real date is present."""
    from datetime import date
    text=unicodedata.normalize('NFKC',str(value or ''))
    found=[]
    for match in re.finditer(r'(令和|平成|昭和|[RHS])?\s*(元|[0-9]{1,4})[年/.-]\s*([0-9]{1,2})[月/.-]\s*([0-9]{1,2})日?',text):
        era,year,month,day=match.groups();year=1 if year=='元' else int(year)
        if era:year+={'令和':2018,'R':2018,'平成':1988,'H':1988,'昭和':1925,'S':1925}[era]
        elif year<1000:continue
        try:found.append(date(year,int(month),int(day)).isoformat())
        except ValueError:continue
    return (found[-1] if last else found[0]) if found else ''

def location_options(data,call,locations):
    if not isinstance(data,dict) or data.get('err') or data.get('errs'):raise StorageError('総務省APIがエラーを返しました。')
    records=data.get('musen')
    if not isinstance(records,list):raise StorageError('総務省APIの応答形式を確認できません。')
    total=data.get('musenInformation',{}).get('totalCount')
    if total is not None and int(total)>len(records):raise StorageError('検索結果が省略されているため所在地を確定できません。')
    grouped={}
    for record in records:
        detail=record.get('detailInfo',{});info=record.get('listInfo',{})
        identity=detail.get('identificationSignals') or info.get('identificationSignals') or info.get('name') or ''
        if not re.search(r'(?<![A-Z0-9/])'+re.escape(call.upper())+r'(?![A-Z0-9/])',str(identity).strip().upper()):continue
        address=unicodedata.normalize('NFKC',str(detail.get('radioEuipmentLocation') or detail.get('radioEquipmentLocation') or info.get('tdfkCd') or '')).strip()
        begin=str(detail.get('licenseDate') or info.get('licenseDate') or '').strip()
        end=str(detail.get('validTerms') or info.get('validTerms') or '').strip()
        option={'address':address,'license_start':begin,'license_end':end,'start_day':license_day(begin),'end_day':license_day(end,last=True),'row':None,'error':''}
        matches=[r for r in locations['rows'] if address and address.startswith(r['name'])]
        if matches:
            longest=max(len(r['name']) for r in matches);matches=[r for r in matches if len(r['name'])==longest]
            if len(matches)==1 and qth_for_row(matches[0]):option['row']=matches[0]
            else:option['error']='所在地を一意に対応できません。'
        else:option['error']='所在地DBに対応する市区町村がありません: '+(address or '所在地未取得')
        # Deduplicate equal source locality strings, not different license addresses.
        previous=grouped.get(address)
        if previous is None or (option['start_day'],option['end_day'])>(previous['start_day'],previous['end_day']):grouped[address]=option
    if not grouped:raise StorageError('一致局の所在地を取得できません。')
    result=list(grouped.values())
    basis='start_day' if all(o['start_day'] for o in result) else 'end_day' if all(o['end_day'] for o in result) else None
    result.sort(key=lambda o:(o[basis] if basis else o['start_day'] or o['end_day'],o['address']),reverse=True)
    for i,option in enumerate(result):option['latest']=bool(len(result)>1 and basis and i==0 and (len(result)==1 or result[0][basis]>result[1][basis]))
    return result

def location_from_response(data,call,locations):
    options=location_options(data,call,locations)
    if len(options)!=1:raise StorageError('複数所在地のため確定できません。候補を確認してください。')
    if options[0]['row'] is None:raise StorageError(options[0]['error'])
    return options[0]['row']


def supplied_location(root,q,code):
    """Verified per-QSO/card code; never perform home lookup for portable QSOs."""
    if not DOMESTIC.fullmatch(q.call.split('/')[0].upper()):return None,'海外局のJCC/JCGは補完しません'
    data=load_locations(root);row=unique_row_for_code(data,code)
    if row is None:return None,'入力JCC/JCGから所在地を確定できません'
    expected=prefecture_qth_from_rmks(data,q.remarks) if 'RTTY' not in q.mode.upper() else ''
    if expected and not qth_for_row(row).endswith(expected):return None,'交換情報と入力コードの都道府県が不一致'
    normalized=str(code).strip().upper()
    from input_normalization import jccjcg_parts
    if q.code and jccjcg_parts(q.code)[1]!=jccjcg_parts(normalized)[1]:return None,'既存JCC/JCGと入力コードが不一致（保持）'
    new=replace(q,his_qth=qth_for_row(row) if q.his_qth.strip() in ('','Japan') else q.his_qth,code=q.code or normalized)
    return new,''

@dataclass
class Candidate:
    session:object
    snapshot:object
    path:Path
    line:int
    raw:str
    own:str
    qso:object
    after:object=None
    note:str=''
    obtained_code:str=''
    selected:bool=True
    ambiguous:bool=False
    license_start:str=''
    license_end:str=''
    address:str=''
    @property
    def key(self):return (str(self.path),self.line)
    def proposal(self,choice=''):return self.after


def collect(repo,paths,own):
    own=base_station_call(own);allowed={p.resolve() for p in amateur_log_files(repo)};result=[]
    if not own:raise ValueError('自局コールを選択してください。')
    for path in sorted({Path(p).resolve() for p in paths}):
        if path not in allowed or base_station_call(file_identity(path)[1])!=own:raise StorageError('選択自局のアマチュアログだけを指定してください。')
        s=repo.open(path)
        if s.log.issues:raise StorageError(path.name+' に読込問題があります。')
        for line,q in s.log.records:
            if '/' in q.call or not DOMESTIC.fullmatch(q.call.upper()) or q.his_qth.strip() not in ('','Japan'):continue
            result.append(Candidate(s,s.snapshot,path,line,s.log.lines[line-1].raw,file_identity(path)[1],q))
    return sorted(result,key=lambda c:(c.qso.date,c.qso.time,str(c.path),c.line))


def validate_start(value):
    from datetime import datetime
    if not value:return ''
    if not isinstance(value,str) or not re.fullmatch(r'[0-9]{12}',value):raise ValueError('開始日時はYYYYMMDDHHiiの半角数字12桁で指定してください。空欄なら先頭からです。')
    try:datetime.strptime(value,'%Y%m%d%H%M')
    except ValueError:raise ValueError('開始日時の日付・時刻が不正です。') from None
    return value

def minute_key(q):return q.date.replace('-','')+q.time.replace(':','')[:4]

def lookup_batch(repo,paths,own,limit=20,include_code=True,*,lookup=request_location,cancelled=lambda:False,progress=lambda done,total,call:None,interval=2.0,start_at=''):
    if not 1<=int(limit)<=1000:raise ValueError('処理件数は1～1000件にしてください。')
    if interval<0:raise ValueError('照会間隔を確認してください。')
    start_at=validate_start(start_at)
    candidates=[c for c in collect(repo,paths,own) if not start_at or minute_key(c.qso)>=start_at]
    candidates=candidates[:int(limit)];locations=load_locations(repo.root);cache={};last_request=None;processed=[];status='';processed_count=0
    for index,c in enumerate(candidates):
        if cancelled():status='中止しました。取得済み結果だけ保存できます。';break
        progress(index,len(candidates),c.qso.call)
        if c.qso.call not in cache:
            if last_request is not None:
                while time.monotonic()-last_request<interval:
                    if cancelled():break
                    time.sleep(min(.1,max(0,interval-(time.monotonic()-last_request))))
            if cancelled():status='中止しました。';break
            last_request=time.monotonic()
            try:cache[c.qso.call]=location_options(lookup(c.qso.call),c.qso.call,locations)
            except StopLookup as e:c.note=str(e);processed.append(c);status=str(e);break
            except (StorageError,ValueError,TypeError) as e:cache[c.qso.call]=str(e)
        answer=cache[c.qso.call];processed_count+=1
        if isinstance(answer,str):c.note=answer;c.selected=False;processed.append(c)
        else:
            ambiguous=len(answer)>1
            for option in answer:
                candidate=replace(c,ambiguous=ambiguous,selected=not ambiguous,license_start=option['license_start'],license_end=option['license_end'],address=option['address'])
                row=option['row']
                if row is None:candidate.note=option['error'];candidate.selected=False
                else:
                    qth=qth_for_row(row);code=row['source_code'];candidate.obtained_code=code
                    expected=prefecture_qth_from_rmks(locations,c.qso.remarks) if 'RTTY' not in c.qso.mode.upper() else ''
                    from input_normalization import jccjcg_parts
                    if expected and not qth.endswith(expected):candidate.note='交換情報とAPI所在地の都道府県が不一致'
                    elif c.qso.code and jccjcg_parts(c.qso.code)[1]!=jccjcg_parts(code)[1]:candidate.note='既存JCC/JCGとAPI所在地が不一致（保持）'
                    else:
                        candidate.after=replace(c.qso,his_qth=qth,code=code if include_code and not c.qso.code.strip() else c.qso.code)
                        candidate.note=('最新候補（免許日付順）／' if option['latest'] else '')+('複数所在地：選択してください／' if ambiguous else '取得済み：')+option['address']
                    if candidate.after is None:candidate.selected=False
                processed.append(candidate)
    progress(processed_count,len(candidates),'')
    return processed,status


def commit(repo,candidates):
    from jccjcg_batch import commit as guarded_commit
    selected=[c for c in candidates if c.after is not None and c.selected]
    if len({c.key for c in selected})!=len(selected):raise StorageError('同じ交信の所在地候補は1つだけ選択してください。')
    return guarded_commit(repo,[(c,'') for c in selected])
