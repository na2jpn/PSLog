"""Offline JARL club-number/name master, with explicit publication metadata."""
from pathlib import Path
from dataclasses import dataclass
import csv,io,json,re,sys,hashlib,unicodedata
from storage import StorageError,Snapshot

INDEX_URL='https://www.jarl.org/Japanese/A_Shiryo/A-B_Club/club.htm'
LIST_URL='https://www.jarl.org/Japanese/A_Shiryo/A-B_Club/list.htm'

def normalize(value):
    return unicodedata.normalize('NFKC',value).strip().upper().translate(str.maketrans({'‐':'-','‑':'-','–':'-','−':'-'}))

def number(value,optional=False):
    value=normalize(value)
    if not value and optional:return ''
    if not re.fullmatch('[0-9]+[A-Z]?-[0-9]+-[0-9]+',value):raise ValueError('登録クラブ番号は13-1-7、01A-1-1のように入力してください。')
    return value

@dataclass
class ClubMaster:
    rows:list
    meta:dict
    guards:list
    def lookup(self,value):
        value=number(value,optional=True)
        return next((r for r in self.rows if r['number']==value),None)
    def search(self,query):
        words=normalize(query).split()
        return [r for r in self.rows if all(w in normalize(r['number']+' '+r['name']) for w in words)]
    def label(self):
        return '参照期間: '+self.meta['valid_from']+'～'+self.meta['valid_to']+' ／ 取得確認: '+self.meta['checked_at']

def load(root):
    folder=Path(root)/'config'/'db'
    if not (folder/'club_db.csv').exists() and not (folder/'club_db_meta.json').exists():folder=Path(getattr(sys,'_MEIPASS',Path(__file__).parent))/'config'/'db'
    paths=[folder/'club_db.csv',folder/'club_db_meta.json'];snaps=[Snapshot.read(p) for p in paths]
    try:
        if any(s.data is None for s in snaps):raise ValueError('クラブDB本体または更新情報が見つかりません。')
        meta=json.loads(snaps[1].data.decode('utf-8-sig'))
        if not isinstance(meta,dict) or meta.get('schema')!=1:raise ValueError('未対応のクラブDBです。')
        for field in ('valid_from','valid_to','checked_at'):
            from datetime import date
            date.fromisoformat(meta[field])
        if meta['valid_from']>meta['valid_to']:raise ValueError('参照期間が不正です。')
        if hashlib.sha256(snaps[0].data).hexdigest()!=meta.get('sha256'):raise ValueError('クラブDBと更新情報の組み合わせが一致しません。')
        reader=csv.DictReader(io.StringIO(snaps[0].data.decode('utf-8-sig')))
        if reader.fieldnames!=['number','name']:raise ValueError('クラブDBの列が不正です。')
        rows=[];seen=set()
        for i,row in enumerate(reader,2):
            if set(row)!=set(reader.fieldnames):raise ValueError(f'{i}行目の列数が不正です。')
            n=number(row['number']);name=row['name']
            if n in seen or not isinstance(name,str) or not name.strip() or any(ord(c)<32 for c in name):raise ValueError(f'{i}行目の番号重複または名称が不正です。')
            seen.add(n);rows.append({'number':n,'name':name})
        if not rows or len(rows)!=meta.get('count'):raise ValueError('クラブDB件数が更新情報と一致しません。')
        for p,s in zip(paths,snaps):s.check(p)
        return ClubMaster(rows,meta,list(zip(paths,snaps)))
    except (ValueError,UnicodeError,KeyError,TypeError) as e:raise StorageError('クラブDBを読み込めません: '+str(e)) from e
