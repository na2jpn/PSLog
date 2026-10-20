"""Lossless, narrowly scoped field patches for existing historical TXT rows."""
import re
from dataclasses import fields
from storage import StorageError,parse
from model import QSO

NAMES=tuple(f.name for f in fields(QSO))

def patched_bytes(session,changes):
    lines=[r.raw for r in session.log.lines]
    for number,updates in changes.items():
        old=session.log.lines[number-1].qso
        if old is None:raise StorageError('形式不正の交信は更新できません。')
        parts=lines[number-1].split('|')
        if len(parts) not in (10,11):raise StorageError('ログの項目数を確認してください。')
        for name,value in updates.items():
            if name not in ('his_qth','code','remarks'):raise StorageError('一括補正の対象外項目です。')
            value=str(value)
            if any(c in value for c in '|\r\n') or '\\\\' in value:raise StorageError('項目内に区切り文字を使用できません。')
            index=NAMES.index(name)
            if index==10 and len(parts)==10:
                m=re.search(r'\s*\\\\\s*$',parts[-1])
                if not m:raise StorageError('ログの終端を確認してください。')
                tail=parts[-1][m.start():];parts[-1]=parts[-1][:m.start()]+' '
                parts.append(' '+value+tail)
            else:
                field=parts[index]
                if index==len(parts)-1:
                    m=re.fullmatch(r'(\s*)(.*?)(\s*\\\\\s*)',field,re.S)
                    if not m:raise StorageError('ログの終端を確認してください。')
                    parts[index]=m[1]+value+m[3]
                else:
                    left=re.match(r'\s*',field)[0];right=re.search(r'\s*$',field)[0]
                    parts[index]=left+value+right
        lines[number-1]='|'.join(parts)
    data=(b'\xef\xbb\xbf' if session.log.bom else b'')+''.join(lines).encode('utf-8')
    checked=parse(data)
    if checked.issues:raise StorageError('補正後のログ形式を確認できません。')
    for number,updates in changes.items():
        for name,value in updates.items():
            if getattr(checked.lines[number-1].qso,name)!=value:raise StorageError('補正内容の照合に失敗しました。')
    return data
