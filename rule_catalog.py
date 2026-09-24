"""Rebuild the generated catalog section from canonical rule files."""
from datetime import datetime,timezone
from storage import Snapshot,replace_bytes,StorageError

BEGIN='<!-- PSLOG GENERATED RULES BEGIN -->'
END='<!-- PSLOG GENERATED RULES END -->'

def cell(value):
    return str(value).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('|','&#124;').replace('\r',' ').replace('\n',' ')

def sync(store):
    path=store.folder/'CATALOG.md';before=Snapshot.read(path)
    old=before.data.decode('utf-8-sig') if before.data is not None else '# コンテストルール管理台帳\n\n自動欄はルール実ファイルから再生成します。手動メモは自動欄の外に記入してください。\n'
    if old.count(BEGIN)!=old.count(END) or old.count(BEGIN)>1 or (BEGIN in old and old.index(BEGIN)>old.index(END)):
        raise ValueError('台帳の自動欄マーカーが不正です。手動メモを保護するため更新を停止しました。')
    rows=[];errors=[];seen=set()
    for file in store.files():
        try:
            r,_=store.read(file);key=(r['id'],r['year'])
            duplicate=key in seen;seen.add(key)
            modified=datetime.fromtimestamp(file.stat().st_mtime,timezone.utc).isoformat(timespec='seconds')
            status='ID・年度重複あり' if duplicate else '登録済み（規約確認済みを意味しません）'
            rows.append('| '+' | '.join(map(cell,(r['id'],r['name'],r['year'],r.get('sort_name',''),file.name,r['url'],modified,status)))+' |')
        except (ValueError,OSError,StorageError) as e:errors.append(cell(file.name+': '+str(e)))
    block=BEGIN+'\n## 作成済みファイル（自動更新）\n\n'
    block+='| 大会ID | 正式名 | 年度 | 読み | ファイル名 | 規約URL | ファイル更新日時（UTC） | 状態 |\n| --- | --- | --- | --- | --- | --- | --- | --- |\n'
    block+='\n'.join(rows)+'\n\n'+f'有効なルールファイル: {len(rows)}件。\n'
    if errors:block+='\n読込できなかったファイル:\n\n'+'\n'.join('- '+x for x in errors)+'\n'
    block+=END
    if BEGIN in old:
        a=old.index(BEGIN);b=old.index(END)+len(END);new=old[:a]+block+old[b:]
    else:new=old.rstrip()+'\n\n'+block+'\n'
    raw=new.encode('utf-8')
    if raw!=before.data:replace_bytes(path,raw,before)
