"""Validated ZIP rule delivery with durable roll-forward recovery.

ZIP files contain manifest.json and flat rules/<id>_<year>.txt files only.
A kernel lock serializes cooperating writers. Unknown external changes stop
recovery; they are never silently overwritten. Packs do not delete old years.
"""
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import base64, hashlib, json, re, stat, zipfile, uuid
from decimal import Decimal, InvalidOperation
from storage import Snapshot, replace_bytes, operation_lock, StorageError, VERSION
from contest_rules import loads, dumps

STATE = '.pack-state.json'
JOURNAL = '.pack-pending.json'
MAX_FILE = 1024*1024
MAX_TOTAL = 32*1024*1024

def digest(data): return hashlib.sha256(data).hexdigest()
def semantic(data): return digest(dumps(loads(data.decode('utf-8-sig'))).encode('utf-8'))
def version(v):
    # PSLog uses compact decimal versions: 1.04, 1.041, ... 1.049, 1.05, 1.051, 1.052, 1.053, 1.054, 1.055, ...
    # Compare them as decimal numbers so 1.041 > 1.04 and 1.05 > 1.049.
    if not isinstance(v,str) or not re.fullmatch(r'\d{1,4}\.\d{2,3}',v):
        raise ValueError('必要バージョンは1.01または1.041のように指定してください。')
    try:
        return Decimal(v)
    except InvalidOperation as e:
        raise ValueError('必要バージョンは1.01または1.041のように指定してください。') from e
def strict_json(data):
    def pairs(items):
        out={}
        for k,v in items:
            if k in out:raise ValueError('JSONキーが重複しています: '+k)
            out[k]=v
        return out
    try:return json.loads(data,object_pairs_hook=pairs)
    except (json.JSONDecodeError,RecursionError,UnicodeError) as e:raise ValueError('JSONが不正です。') from e

def encode(data):return None if data is None else base64.b64encode(data).decode('ascii')
def decode(data):return None if data is None else base64.b64decode(data,validate=True)

def safe_target(name):
    if name==STATE:return
    if not isinstance(name,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}_\d{4}\.txt',name):
        raise ValueError('ルール更新先が不正です。')

def read_index(raw):
    index={} if raw is None else strict_json(raw)
    if not isinstance(index,dict):raise ValueError('配布履歴が不正です。')
    for name,value in index.items():
        safe_target(name)
        if name==STATE or not isinstance(value,dict) or set(value)!={'sha256','revision','pack_id'}:raise ValueError('配布履歴が不正です。')
        if not isinstance(value['sha256'],str) or not re.fullmatch('[0-9a-f]{64}',value['sha256']) or type(value['revision']) is not int or value['revision']<1 or not isinstance(value['pack_id'],str):raise ValueError('配布履歴が不正です。')
    return index

def recover_locked(folder):
    path=folder/JOURNAL;snap=Snapshot.read(path)
    if snap.data is None:return
    try:
        j=strict_json(snap.data)
        if set(j)!= {'schema','changes'} or j['schema']!=1 or not isinstance(j['changes'],list):raise ValueError('更新記録形式')
        seen=set();changes=[]
        for x in j['changes']:
            if set(x)!= {'name','before','after'}:raise ValueError('更新記録項目')
            safe_target(x['name'])
            if x['name'] in seen:raise ValueError('更新先重複')
            seen.add(x['name']);before=decode(x['before']);after=decode(x['after'])
            if after is None:raise ValueError('削除は禁止')
            if x['name']==STATE:read_index(after)
            else:loads(after.decode('utf-8-sig'))
            target=folder/x['name']
            if target.is_symlink():raise ValueError('シンボリックリンクは禁止')
            current=Snapshot.read(target)
            if current.data not in (before,after):raise StorageError('更新中に外部変更がありました。バックアップと更新記録を保護して停止しました: '+x['name'])
            changes.append((target,current,after))
        # Validate all targets before replacing any remaining ones.
        for target,current,after in changes:
            if current.data!=after:replace_bytes(target,after,current)
        snap.check(path);path.unlink()
    except (ValueError,TypeError,KeyError) as e:
        raise StorageError('ルール更新の復旧記録が不正です。自動上書きを停止しました。') from e

def recover(store):
    with operation_lock(store.folder):recover_locked(store.folder)

@dataclass
class Item:
    rule: dict
    revision: int
    minimum: str
    data: bytes
    target: Path
    before: Snapshot
    status: str
    reason: str

@dataclass
class Preview:
    items: list
    state: Snapshot
    inventory: dict
    pack_id: str


def read_archive(path):
    try:
        with zipfile.ZipFile(path) as z:
            infos=z.infolist()
            if len(infos)>501 or sum(x.file_size for x in infos)>MAX_TOTAL:raise ValueError('ZIPの件数または展開サイズが上限を超えています。')
            names=set();payload={}
            for info in infos:
                name=info.filename
                if name in names or name.casefold() in {n.casefold() for n in names}:raise ValueError('ZIP内の名前が重複しています。')
                names.add(name)
                if info.is_dir():raise ValueError('ZIPにはmanifest.jsonとルールファイルだけを入れてください。')
                if '\\' in name or any(x in ('','..','.') for x in name.split('/')) or PurePosixPath(name).is_absolute():raise ValueError('ZIP内のパスが不正です。')
                if stat.S_ISLNK(info.external_attr>>16) or info.flag_bits&1:raise ValueError('リンクまたは暗号化ZIPには対応しません。')
                if info.file_size>MAX_FILE:raise ValueError('ファイルが大きすぎます。')
                if name!='manifest.json' and not re.fullmatch(r'rules/[A-Za-z0-9][A-Za-z0-9_-]{0,79}_\d{4}\.txt',name):raise ValueError('ZIPに対象外のファイルがあります: '+name)
                payload[name]=z.read(info)
        m=strict_json(payload.pop('manifest.json'))
        if not isinstance(m,dict) or set(m)!= {'schema','pack_id','rules'} or type(m['schema']) is not int or m['schema']!=1:raise ValueError('未対応のルールパック形式です。')
        if not isinstance(m['pack_id'],str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',m['pack_id']):raise ValueError('パック識別子が不正です。')
        if not isinstance(m['rules'],list) or not 1<=len(m['rules'])<=500:raise ValueError('ルールは1～500件です。')
        items=[];seen=set()
        for e in m['rules']:
            if not isinstance(e,dict) or set(e)!= {'file','id','year','revision','minimum_version','sha256'}:raise ValueError('パックのルール情報が不正です。')
            if not isinstance(e['file'],str):raise ValueError('ファイル名が不正です。')
            raw=payload.pop(e['file']);r=loads(raw.decode('utf-8-sig'));key=(r['id'],r['year'])
            if key in seen or (e['id'],e['year'])!=key or e['file']!=f"rules/{r['id']}_{r['year']}.txt":raise ValueError('ID・年度・ファイル名が不一致または重複しています。')
            seen.add(key)
            if type(e['revision']) is not int or e['revision']<1:raise ValueError('改訂番号は1以上の整数です。')
            if version(e['minimum_version'])>version(VERSION):raise ValueError('このパックにはPSLog '+e['minimum_version']+'以降が必要です。')
            if digest(raw)!=e['sha256']:raise ValueError('ルールのハッシュが一致しません。')
            items.append((r,e,raw))
        if payload:raise ValueError('台帳にないファイルがZIPにあります。')
        return m['pack_id'],items
    except (KeyError,UnicodeError,zipfile.BadZipFile,RuntimeError) as e:raise ValueError('ルールパックを読み込めません: '+str(e)) from e


def preview(store,path):
    pack_id,incoming=read_archive(path)
    with operation_lock(store.folder):
        recover_locked(store.folder)
        state=Snapshot.read(store.folder/STATE);index=read_index(state.data)
        inventory={p.name:Snapshot.read(p) for p in store.folder.glob('*.txt')}
        existing={}
        for name,snap in inventory.items():
            r=loads(snap.data.decode('utf-8-sig'));key=(r['id'],r['year'])
            if key in existing:raise ValueError('既存ルールのID・年度が重複しています。先に整理してください。')
            existing[key]=(store.folder/name,snap)
        items=[]
        for r,e,raw in incoming:
            key=(r['id'],r['year']);target,before=existing.get(key,(store.folder/f"{r['id']}_{r['year']}.txt",Snapshot(None,None)))
            safe_target(target.name)
            if target.is_symlink():raise ValueError('リンク先のルールは更新できません。')
            if before.data is None:status,reason='追加','新しいID・年度'
            elif semantic(before.data)==semantic(raw):status,reason='変更なし','内容は同じ'
            else:
                prior=index.get(target.name,{})
                if prior.get('sha256')!=semantic(before.data):status,reason='競合','手動編集または配布履歴なし'
                elif e['revision']<=prior.get('revision',0):status,reason='競合','同じ改訂番号の別内容、または旧版'
                else:status,reason='更新','配布版の新しい改訂'
            items.append(Item(r,e['revision'],e['minimum_version'],raw,target,before,status,reason))
        return Preview(items,state,inventory,pack_id)


def install(store,plan,replace_conflicts=()):
    replace_conflicts=set(replace_conflicts)
    allowed={i.target.name for i in plan.items if i.status=='競合'}
    if not replace_conflicts<=allowed:raise ValueError('更新対象の指定が不正です。')
    with operation_lock(store.folder):
        recover_locked(store.folder)
        if {p.name for p in store.folder.glob('*.txt')}!=set(plan.inventory):raise StorageError('確認後にルール一覧が変更されました。ZIPを読み直してください。')
        for name,snap in plan.inventory.items():snap.check(store.folder/name)
        plan.state.check(store.folder/STATE)
        index=read_index(plan.state.data)
        changes=[];selected=[]
        for i in plan.items:
            if i.target.parent.resolve()!=store.folder or i.target.is_symlink():raise ValueError('更新先が不正です。')
            if i.status=='競合' and i.target.name not in replace_conflicts:continue
            i.before.check(i.target)
            # Identical files do not reset the user's provenance or revision.
            if i.status=='変更なし':continue
            selected.append(i)
            changes.append(dict(name=i.target.name,before=encode(i.before.data),after=encode(i.data)))
            index[i.target.name]=dict(sha256=semantic(i.data),revision=i.revision,pack_id=plan.pack_id)
        if not changes:return 0
        history=store.folder/'history'/('pack-'+uuid.uuid4().hex);history.mkdir(parents=True)
        for i in selected:
            if i.before.data is not None:replace_bytes(history/i.target.name,i.before.data,Snapshot(None,None))
        if plan.state.data is not None:replace_bytes(history/STATE,plan.state.data,Snapshot(None,None))
        changes.append(dict(name=STATE,before=encode(plan.state.data),after=encode(json.dumps(index,ensure_ascii=False,indent=2).encode('utf-8'))))
        replace_bytes(store.folder/JOURNAL,json.dumps(dict(schema=1,changes=changes)).encode('utf-8'),Snapshot(None,None))
        recover_locked(store.folder)
        store.catalog_warning=''
        try:store._sync_catalog()
        except (ValueError,OSError,StorageError) as e:store.catalog_warning='ルール更新済み。台帳の再読込が必要です: '+str(e)
        return len(selected)


def build(path, rules, pack_id):
    """Publisher API: rules is [(validated_rule, revision, minimum_version), ...]."""
    contents={};entries=[]
    for r,revision,minimum in rules:
        raw=dumps(r).encode('utf-8');name=f"rules/{r['id']}_{r['year']}.txt"
        if name in contents:raise ValueError('ID・年度重複')
        contents[name]=raw;entries.append(dict(file=name,id=r['id'],year=r['year'],revision=revision,minimum_version=minimum,sha256=digest(raw)))
    import io
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('manifest.json',json.dumps(dict(schema=1,pack_id=pack_id,rules=entries),ensure_ascii=False))
        for name,raw in contents.items():z.writestr(name,raw)
    read_archive(io.BytesIO(out.getvalue()))
    path=Path(path);replace_bytes(path,out.getvalue(),Snapshot(None,None))
