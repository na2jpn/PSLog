"""Versioned declarative contest rules. No executable expressions."""
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
import json,re,math,unicodedata
from decimal import Decimal
from storage import Snapshot,replace_bytes,operation_lock,StorageError

FIELDS=('mode','band','call','exchange','prefix','length','digits_length','area','country','continent')
OPS=('eq','ne','starts','in','ge','le')

def default_rule():
    return dict(schema=1,id='new-rule',name='新しいルール',year=2026,url='',
        points={'phone':1,'cw':1,'digital':1},conditions=[],
        duplicate={'enabled':True,'by_mode':False},
        multi1={'kind':'whole','start':0,'length':2,'per_band':True},
        multi2={'kind':'off','value':1,'condition':{'all':[]}},formula='total')

def keys(obj,expected,label):
    if not isinstance(obj,dict) or set(obj)!=set(expected):raise ValueError(label+' の項目が不足、または未対応です。')
def number(v,label):
    if type(v) not in (int,float) or not 0<=v<=100000000 or not math.isfinite(v) or round(v,6)!=v:raise ValueError(label+' は0～100000000、小数6桁以内の有限数です。')
def condition(c,depth=0):
    if depth>12:raise ValueError('条件の入れ子は12段までです。')
    if isinstance(c,dict) and set(c) in ({'all'},{'any'}):
        values=next(iter(c.values()))
        if not isinstance(values,list):raise ValueError('AND/ORの条件は配列です。')
        for x in values:condition(x,depth+1)
        return
    keys(c,('field','op','value'),'条件')
    if c['field'] not in FIELDS or c['op'] not in OPS:raise ValueError('未対応の条件項目・比較方法です。')
    if c['field'] in ('length','digits_length'):
        if c['op'] not in ('eq','ne','ge','le') or type(c['value']) is not int or c['value']<0:raise ValueError('桁数条件は0以上の整数と数値比較で指定してください。')
    elif c['op'] not in ('eq','ne','starts','in') or not isinstance(c['value'],str):raise ValueError('文字条件は文字列と文字比較で指定してください。')

def validate(r):
    if not isinstance(r,dict):raise ValueError('ルールはJSONオブジェクトで指定してください。')
    keys(r,set(default_rule())|{k for k in ('sort_name','organizer') if k in r}|({'scoring'}|({'event'} if 'event' in r else set()) if r.get('schema')==2 else set()),'ルール')
    if 'sort_name' in r and (not isinstance(r['sort_name'],str) or any(c in r['sort_name'] for c in '\r\n\t')):raise ValueError('並び順用の読みは1行の文字列です。')
    for k in ('organizer',):
        if k in r and (not isinstance(r[k],str) or any(c in r[k] for c in '\r\n\t')):raise ValueError('主催は1行の文字列です。')
    if type(r['schema']) is not int or r['schema'] not in (1,2):raise ValueError('未対応のルール形式です。')
    if not isinstance(r['id'],str) or not re.fullmatch('[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}',r['id']):raise ValueError('識別子は半角英数字・_・-（80文字まで）です。')
    if not isinstance(r['name'],str) or not r['name'].strip():raise ValueError('ルール名を入力してください。')
    if type(r['year']) is not int or not 1900<=r['year']<=9999:raise ValueError('参照年を4桁で入力してください。')
    if not isinstance(r['url'],str):raise ValueError('出典URLは文字列です。')
    keys(r['points'],('phone','cw','digital'),'通常点')
    for v in r['points'].values():number(v,'得点')
    if not isinstance(r['conditions'],list):raise ValueError('条件点は配列です。')
    for c in r['conditions']:
        keys(c,('when','points'),'条件点');condition(c['when']);number(c['points'],'条件点')
    keys(r['duplicate'],('enabled','by_mode'),'重複判定')
    if any(type(v) is not bool for v in r['duplicate'].values()):raise ValueError('重複設定は真偽値です。')
    m=r['multi1'];keys(m,('kind','start','length','per_band','rules') if 'rules' in m else ('kind','start','length','per_band'),'第一マルチ')
    if 'rules' in m:
        if not isinstance(m['rules'],list):raise ValueError('抽出ルールは配列です。')
        for rule in m['rules']:
            keys(rule,('when','source','kind','start','length'),'抽出ルール');condition(rule['when'])
            if rule['source'] not in ('exchange','area','prefix','country','continent') or rule['kind'] not in ('whole','digits','slice'):raise ValueError('未対応の抽出方法です。')
            if type(rule['start']) is not int or not 0<=rule['start']<=100000000 or type(rule['length']) is not int or not 1<=rule['length']<=100000000:raise ValueError('抽出位置・文字数が不正です。')
    if m['kind']=='registered' and not m.get('rules'):raise ValueError('抽出ルールを1件以上登録してください。')
    if m['kind'] not in ('off','whole','digits','slice','registered'):raise ValueError('未対応の第一マルチです。')
    if type(m['start']) is not int or m['start']<0 or type(m['length']) is not int or not 1<=m['length']<=100000000 or m['start']>100000000 or type(m['per_band']) is not bool:raise ValueError('第一マルチの位置・文字数・バンド区分が不正です。')
    m=r['multi2'];keys(m,('kind','value','condition'),'第二マルチ')
    if m['kind'] not in ('off','fixed','bands','qsos'):raise ValueError('未対応の第二マルチです。')
    number(m['value'],'第二マルチ');condition(m['condition'])
    if r['formula'] not in ('total','band_sum'):raise ValueError('未対応の集計方式です。')
    if r['formula']=='band_sum' and not r['multi1']['per_band']:raise ValueError('バンド別積の合計では第一マルチをバンド別にしてください。')
    if r['schema']==2:
        from contest_scoring_v2 import validate_scoring
        validate_scoring(r['scoring'])
        if 'event' in r:
            from contest_event import validate_event
            validate_event(r['event'])
            if any(c['modes']==['*'] for c in r['event']['categories']) and len(set(r['points'].values()))!=1:raise ValueError('全許可モードの通常点は全分類で同じ値にしてください。')
        if r['multi1']['kind']!='off':raise ValueError('形式2では第一マルチをoffにして拡張マルチを指定してください。')
        if r['formula']=='band_sum' and any(not m['per_band'] for m in r['scoring']['multipliers']):raise ValueError('バンド別積では全マルチをバンド別にしてください。')
    return r

def loads(text):
    def pairs(items):
        d={}
        for k,v in items:
            if k in d:raise ValueError('JSONのキーが重複しています: '+k)
            d[k]=v
        return d
    try:return validate(json.loads(text,object_pairs_hook=pairs))
    except (json.JSONDecodeError,RecursionError) as e:raise ValueError('JSON形式が不正です: '+str(e)) from e

def dumps(r):return json.dumps(validate(r),ensure_ascii=False,indent=2)+'\n'

def name_key(text):
    text=unicodedata.normalize('NFKC',text).strip().casefold()
    text=''.join(chr(ord(c)-0x60) if 'ァ'<=c<='ヶ' else c for c in text)
    group=0 if text and text[0].isascii() and text[0].isalnum() else 1 if text and 'ぁ'<=text[0]<='ゖ' else 2
    return group,text

def rule_sort_key(rule):
    return (*name_key(rule.get('sort_name','').strip() or rule['name']),-rule['year'],rule['id'])

def rule_label(rule):return f"{rule['name']}（{rule['year']}）"

def management_rule_label(rule,label):
    """Add the contest start month to a preformatted rule label when available."""
    starts=[str(w.get('start','')).strip() for w in rule.get('event',{}).get('windows',[]) if isinstance(w,dict) and str(w.get('start','')).strip()]
    if not starts:return label
    date=min(starts).split(None,1)[0].split('-')
    if len(date)<2 or not date[1].isdigit():return label
    month=str(int(date[1]));suffix=f"（{rule.get('year','')}）"
    return label[:-len(suffix)]+f"（{rule.get('year','')}/{month}）" if suffix and label.endswith(suffix) else label


def seed_bundled_folder(target,relative,pattern,migrate=None):
    """Synchronize application-managed bundled data on frozen builds.

    Unchanged official assets are updated. User-modified and user-defined files
    are preserved; provenance is maintained by :mod:`bundled_sync`.
    """
    from bundled_sync import sync_bundled_folder
    return sync_bundled_folder(target,relative,pattern,migrate=migrate)


def _migrate_legacy_rule(name,local,bundled):
    """One-time safe repair for pre-1.061 stale OPPLACE official rules.

    Without old provenance we only migrate when removing obsolete ``opplace``
    makes the local rule byte-semantically equal to the current bundled rule.
    Any other user/local difference is preserved.
    """
    try:
        old=loads(local.decode('utf-8-sig'));new=loads(bundled.decode('utf-8-sig'))
        if (old.get('id'),old.get('year'))!=(new.get('id'),new.get('year')):return None
        old_fields=old.get('event',{}).get('submission',{}).get('required_fields',[])
        new_fields=new.get('event',{}).get('submission',{}).get('required_fields',[])
        if 'opplace' not in old_fields or 'opplace' in new_fields:return None
        candidate=deepcopy(old);candidate['event']['submission']['required_fields']=[x for x in old_fields if x!='opplace']
        if candidate==new:return bundled
    except (ValueError,UnicodeDecodeError,KeyError,TypeError):
        return None
    return None

class RuleStore:
    catalog_enabled=True
    catalog_warning=""
    def sync_catalog(self):
        if not self.catalog_enabled:return
        self.folder.mkdir(parents=True,exist_ok=True)
        with operation_lock(self.folder):
            from rule_pack import recover_locked
            recover_locked(self.folder)
            self._sync_catalog()
    def _sync_catalog(self):
        if not self.catalog_enabled:return
        from rule_catalog import sync
        sync(self)
    decode=staticmethod(loads)
    encode=staticmethod(dumps)
    def __init__(self,root):
        root=Path(root).resolve()
        self.folder=root/'config'/'rules'
        seed_bundled_folder(self.folder,'config/rules','*.txt',migrate=_migrate_legacy_rule)
        seed_bundled_folder(root/'config'/'db'/'contest','config/db/contest','*.json')
    def origin(self,path):
        from bundled_sync import bundled_status
        return bundled_status(self.folder,'config/rules',Path(path).name)
    def display_label(self,rule,path):
        prefix={'official':'','user_modified':'（ユーザー変更）','user_defined':'（ユーザー定義）'}.get(self.origin(path),'（ユーザー定義）')
        return prefix+rule_label(rule)
    def recover_pack(self):
        if (self.folder/'.pack-pending.json').exists():
            from rule_pack import recover
            recover(self)
    def files(self):
        self.recover_pack()
        def order(path):
            try:return (0,*rule_sort_key(self.read(path)[0]),path.name)
            except (ValueError,OSError,StorageError):
                # Preserve invalid entries so the management screen can report them.
                return (1,path.name)
        return sorted(self.folder.glob('*.txt'),key=order)
    def read(self,path):
        self.recover_pack()
        path=Path(path).resolve()
        if path.parent!=self.folder:raise ValueError('ルール保存先が異なります。')
        snap=Snapshot.read(path)
        if snap.data is None:raise ValueError('ルールが見つかりません。')
        return self.decode(snap.data.decode('utf-8-sig')),snap
    def save(self,r,path=None,snapshot=None):
        data=self.encode(r).encode('utf-8');target=self.folder/f"{r['id']}_{r['year']}.txt"
        self.folder.mkdir(parents=True,exist_ok=True)
        with operation_lock(self.folder):
            from rule_pack import recover_locked
            recover_locked(self.folder)
            if path is not None:
                if Path(path).resolve()!=target:raise ValueError('識別子・参照年の変更は「別名保存」を使用してください。')
                if snapshot is None:raise ValueError('保存前の状態がありません。再読込してください。')
                snapshot.check(target)
                if snapshot.data is not None:
                    from datetime import datetime
                    backup=self.folder/'history'/f"{target.stem}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}.txt"
                    replace_bytes(backup,snapshot.data,Snapshot(None,None))
            else:snapshot=Snapshot(None,None)
            replace_bytes(target,data,snapshot)
            self.catalog_warning=''
            try:self._sync_catalog()
            except (ValueError,OSError,StorageError) as e:self.catalog_warning='ルールは保存済みですが、台帳更新に失敗しました。管理画面の再読込で再試行してください: '+str(e)
        return target,Snapshot.read(target)

def family(mode):
    m=mode.upper().strip()
    if m in ('SSB','USB','LSB','FM','AM'):return 'phone'
    if m=='CW':return 'cw'
    if m in ('RTTY','PSK','PSK31','Q65','MSK144','JT65','JT9','MFSK','SSTV','DATA','DIG','DV','D-STAR','DSTAR','DMR','C4FM','DIGITALVOICE') or any(x in m for x in ('FT8','FT4','FT2','FREEDV')):return 'digital'
    return None

def digits(value):
    groups=re.findall('[0-9]+',value)
    if len(groups)!=1:raise ValueError('数字群を一つに特定できません: '+value)
    return groups[0]

def matches(c,values):
    if 'all' in c:return all(matches(x,values) for x in c['all'])
    if 'any' in c:return any(matches(x,values) for x in c['any'])
    field=c['field'];v=values.get(field)
    if field=='length':v=len(values['exchange'])
    if field=='digits_length':v=len(digits(values['exchange']))
    if v is None:raise ValueError('判定情報が未設定です: '+field)
    wanted=c['value'];op=c['op']
    if isinstance(v,str):v=v.upper();wanted=wanted.upper()
    if op=='eq':return v==wanted
    if op=='ne':return v!=wanted
    if op=='starts':return v.startswith(wanted)
    if op=='in':return v in [x.strip() for x in wanted.split(',')]
    if op=='ge':return v>=wanted
    if op=='le':return v<=wanted
    raise ValueError('未対応の比較方法です。')

@dataclass
class Score:
    points: float
    multi1: int
    multi2: float
    total: float | None
    rows: list
    problems: list

def manual_score(entries):
    """Neutral result for an unregistered contest handled entirely by the operator."""
    rows=[{'points':Decimal('0'),'multi':None,'reason':'手動モード'} for _ in entries]
    return Score(Decimal('0'),0,Decimal('1'),Decimal('0'),rows,[])

def score_steps(rule,entries,context=None):
    """entries in chronological order: call,band,mode,exchange plus optional area/prefix."""
    r=validate({k:v for k,v in rule.items() if k!='_calendar_applied'})
    from contest_calendar import working_rule
    r=working_rule(r,context) if not rule.get('_calendar_applied') else dict(r,_calendar_applied=True)
    if r['schema']==2:
        from contest_scoring_v2 import steps
        if 'event' in r:
            from contest_event import prepare,finish
            rows,problems,category=prepare(r,entries,context)
            result=yield from steps(r,rows)
            return finish(result,rows,category,problems)
        return (yield from steps(r,entries))
    seen=set();out=[];problems=[];multis=set();bands={};valid=[]
    for i,entry in enumerate(entries):
        try:
            v=dict(entry);v['exchange']=str(v.get('exchange','')).strip().upper()
            for f in ('call','band','mode'):
                if not isinstance(v.get(f),str) or not v[f].strip():raise ValueError(f+'が未設定です。')
                v[f]=v[f].upper().strip()
            if v.get('continent') is not None:
                v['continent']=v['continent'].strip().upper()
                if v['continent'] not in ('AF','AN','AS','EU','NA','OC','SA'):raise ValueError('大陸はAF/AN/AS/EU/NA/OC/SAで指定してください。')
            mode=family(v['mode'])
            if mode is None:raise ValueError('未分類のモード: '+v['mode'])
            k=(v['call'],v['band'],v['mode'] if r['duplicate']['by_mode'] else '')
            duplicate=r['duplicate']['enabled'] and k in seen
            points=Decimal(str(r['points'][mode]));reason='通常点'
            if duplicate:points=0;reason='重複'
            else:
                for n,c in enumerate(r['conditions']):
                    if matches(c['when'],v):points=Decimal(str(c['points']));reason=f'条件 {n+1}';break
            token=None;m=r['multi1'];b=v['band']
            if points>0 and m['kind']!='off':
                extraction=m;source='exchange'
                if m['kind']=='registered':
                    found=next(((n,x) for n,x in enumerate(m['rules'],1) if matches(x['when'],v)),None)
                    if found is None:raise ValueError('一致するマルチ抽出ルールがありません。')
                    n,extraction=found;source=extraction['source'];reason+=f' / マルチ抽出 {n}'
                token=v.get(source)
                if token is None or not str(token).strip():raise ValueError('マルチ抽出元が空欄です: '+source)
                token=str(token).strip().upper()
                if extraction['kind']=='digits':token=digits(token)
                elif extraction['kind']=='slice':
                    if len(token)<extraction['start']+extraction['length']:raise ValueError('抽出位置がナンバーの範囲を超えます。')
                    token=token[extraction['start']:extraction['start']+extraction['length']]
            qualifies=False
            if points>0 and r['multi2']['kind'] in ('bands','qsos'):qualifies=matches(r['multi2']['condition'],v)
            seen.add(k);band=bands.setdefault(b,{'points':0,'multi':set()});band['points']+=points
            multi_status=None
            if token is not None:
                multi_key=(b if m['per_band'] else '',token)
                multi_status='既出' if multi_key in multis else '新規'
                multis.add(multi_key);band['multi'].add(token)
            if qualifies:valid.append(b)
            out.append({'points':points,'multi':token,'reason':reason,'multiplier_judgement':multi_status})
        except (ValueError,TypeError) as e:problems.append(f'{i+1}行目: {e}');out.append({'points':None,'multi':None,'reason':str(e)})
        if (i+1)%100==0:yield i+1
    points=sum(b['points'] for b in bands.values());m1=1 if r['multi1']['kind']=='off' else len(multis)
    m=r['multi2'];m2=1 if m['kind']=='off' else Decimal(str(m['value'])) if m['kind']=='fixed' else len(set(valid)) if m['kind']=='bands' else len(valid)
    base=points*m1 if r['formula']=='total' else sum(b['points']*(1 if r['multi1']['kind']=='off' else len(b['multi'])) for b in bands.values())
    return Score(points,m1,m2,None if problems else base*m2,out,problems)


def score(rule,entries,context=None):
    work=score_steps(rule,entries,context)
    while True:
        try:next(work)
        except StopIteration as done:return done.value
