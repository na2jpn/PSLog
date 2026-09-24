"""JCC/JCG log maintenance helpers and recoverable batch commit.

Pure-Python core used by the GUI.  It never guesses an ambiguous municipality:
unique code/QTH matches are proposed, while a bare five-digit JCG may safely
resolve only to its county (gun).  Original log bytes are revalidated before a
batch write and every touched file is backed up first.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
import re

from input_normalization import jccjcg_code
from locations import load as load_locations, exact_matches, qth_for_row, normalize_jcg_gun
from countries import load as load_countries
from remarks_sections import primary as primary_remarks
from qsl_marks import TOKEN as QSL_TOKEN
import unicodedata
from search import file_identity
from storage import StorageError, ExternalChange, operation_lock, replace_bytes
from time_range import boundary_datetime

MODE_CODE_TO_QTH='code_to_qth'
MODE_RMKS_TO_BOTH='rmks_to_both'
MODE_RMKS_TO_PREF='rmks_to_pref'
MODE_QTH_TO_CODE='qth_to_code'
MODE_MISMATCH='mismatch'
MODES=(MODE_CODE_TO_QTH,MODE_RMKS_TO_BOTH,MODE_RMKS_TO_PREF,MODE_QTH_TO_CODE,MODE_MISMATCH)
DEFAULT_RECENT_LIMIT=2000

MODE_LABELS={
    MODE_CODE_TO_QTH:'[A] HIS QTHがJapanまたは空欄のものに、記録済みJCC/JCGを参考にHIS QTHを上書き',
    MODE_RMKS_TO_BOTH:'[B] HIS QTHがJapanまたは空欄のものに、記録済みRMKSをJCC/JCGとして扱いJCC/JCGとHIS QTHを上書き',
    MODE_RMKS_TO_PREF:'[C] HIS QTHがJapanまたは空欄の場合、RMKSを参考に都道府県までを上書き',
    MODE_QTH_TO_CODE:'[D] JCC/JCGが空欄のものに、記録済みHIS QTHを参考にJCC/JCGを上書き',
    MODE_MISMATCH:'[E] JCC/JCGとHIS QTHの不一致を修正',
}


def _stamp(qso):
    return datetime.strptime(qso.date+' '+qso.time,'%Y-%m-%d %H:%M')


def _japan_or_blank(value):
    return str(value or '').strip().casefold() in ('','japan')


def _row_qth(row):
    return qth_for_row(row)


def _normalized_code(value):
    code=jccjcg_code(value)
    return code if re.fullmatch(r'(?:\d{4}|\d{6}|\d{5}[A-Z]?)',code) else ''


def rows_for_code(data,value):
    """Return the safest matching rows for one stored JCC/JCG code.

    Municipality-level ``source_code`` wins.  A bare five-digit JCG can map to
    several municipalities; callers may collapse those rows only to the common
    county level and must not pick a municipality.
    """
    code=_normalized_code(value)
    if not code:return []
    exact=[r for r in data.get('rows',[]) if str(r.get('source_code','')).upper()==code]
    if exact:return exact
    return [r for r in data.get('rows',[]) if str(r.get('code','')).upper()==code]


def _jcg_county_qth(rows):
    """Return a safe county-level QTH for a bare five-digit JCG.

    A bare JCG identifies the county (gun), not the town/village suffix.  The
    location master stores one row per municipality, so several rows can share
    the same five-digit JCG.  We intentionally collapse only the common county
    portion and never choose one municipality.

    Reference QTH is preferred here because it is the mechanically-normalized
    master spelling; verified per-municipality spellings may contain legacy
    forms such as ``Itanogun``.
    """
    qths=[]
    for row in rows:
        if str(row.get('kind','')).upper()!='JCG':continue
        qth=str(row.get('reference_qth') or row.get('verified_qth') or '').strip()
        if qth:qths.append(qth)
    if not qths:return ''

    county=[]
    for qth in qths:
        parts=qth.split(); folded=[p.casefold() for p in parts]
        if 'gun' not in folded:continue
        i=folded.index('gun')
        if i<1:continue
        county.append(' '.join(parts[i-1:]))
    if county and len({x.casefold() for x in county})==1:
        return normalize_jcg_gun(county[0])

    # Tokyo island JCGs and other non-"gun" exceptions do not have a common
    # county token in the current master.  Do not guess a branch/subprefecture
    # from a municipality name; keep those cases ambiguous.
    return ''


def _generic_jcg_row(data,code):
    if not re.fullmatch(r'\d{5}',code):return None
    rows=rows_for_code(data,code)
    qth=_jcg_county_qth(rows)
    if not qth:return None
    return {'name':'','source_code':code,'kind':'JCG','code':code,
            'verified_qth':qth,'reference_qth':qth,'synthetic_county':True}


def unique_row_for_code(data,value):
    code=_normalized_code(value)
    if not code:return None
    generic=_generic_jcg_row(data,code)
    if generic:return generic
    rows=rows_for_code(data,code)
    return rows[0] if len(rows)==1 and _row_qth(rows[0]) else None


def unique_row_for_qth(data,value):
    rows=[r for r in exact_matches(data,value) if str(r.get('source_code','')).strip()]
    return rows[0] if len(rows)==1 else None


def qth_from_code(root,value):
    row=unique_row_for_code(load_locations(root),value)
    if row is None:
        code=_normalized_code(value)
        if not code:raise ValueError('JCC/JCGコードとして解釈できません。')
        rows=rows_for_code(load_locations(root),code)
        if len(rows)>1 and re.fullmatch(r'\d{5}',code):raise ValueError('JCGコードから郡・支庁単位の所在地を安全に確定できません。より詳細なコードを指定してください。')
        if len(rows)>1:raise ValueError('JCC/JCGコードだけでは所在地を一意に決められません。より詳細なコードを指定してください。')
        raise ValueError('JCC/JCGに対応する所在地を確認できません。')
    return _row_qth(row)


DECIMAL_MEMO = re.compile(r'(?<![\w.])\d+\.\d+(?![\w.])')
RMKS_SEPARATORS = re.compile(r'[(),;\[\]{}]+')


def _rmks_location_text(value):
    """Return RMKS1 after removing only known harmless side information.

    JCC/JCG batch conversion must never mine an arbitrary integer out of prose.
    For practical logs, however, RMKS1 often contains a formal QSL marker or a
    decimal frequency memo beside the location code.  Those tokens are safe to
    ignore because they are structurally distinct from JCC/JCG/area codes.
    RMKS2 is deliberately excluded by ``primary_remarks``.
    """
    raw=unicodedata.normalize('NFKC',primary_remarks(value)).strip()
    raw=QSL_TOKEN.sub(' ',raw)
    raw=DECIMAL_MEMO.sub(' ',raw)
    raw=RMKS_SEPARATORS.sub(' ',raw)
    return re.sub(r'\s+',' ',raw).strip()


def code_from_rmks(value):
    """Treat cleaned RMKS1 as a JCC/JCG value; never mine arbitrary numbers."""
    return _normalized_code(_rmks_location_text(value))


def _prefecture_map(data):
    values={}
    for row in data.get('rows',[]):
        code=str(row.get('source_code','')).strip()
        qth=_row_qth(row)
        if len(code)<2 or not code[:2].isdigit() or not qth.casefold().endswith(' japan'):continue
        parts=qth.split()
        if len(parts)<2:continue
        values.setdefault(code[:2],set()).add(parts[-2])
    return {k:next(iter(v))+' Japan' for k,v in values.items() if len(v)==1}


HOKKAIDO_REGION_CODES={str(n) for n in range(101,115)}


def prefecture_qth_from_rmks(data,value):
    raw=_rmks_location_text(value)
    code=jccjcg_code(raw)
    # JARL's contest area numbers use 101-114 for the fourteen Hokkaido
    # regions.  For this prefecture-level maintenance mode they all collapse
    # safely to Hokkaido; municipality/JCC/JCG inference is intentionally not
    # attempted here.  The ordinary JCC/JCG-derived 01 prefix remains valid.
    if code in HOKKAIDO_REGION_CODES:return 'Hokkaido Japan'
    if not re.fullmatch(r'(?:\d{2}|\d{4}|\d{6}|\d{5}[A-Z]?)',code):return ''
    return _prefecture_map(data).get(code[:2],'')


def _domestic_qso(country_db,data,qso):
    qth=str(qso.his_qth or '').strip()
    try:hint=country_db.lookup(qso.call)
    except Exception:hint=None
    if hint and str(hint.get('country','')).casefold()!='japan':return False
    if qth:
        folded=qth.casefold()
        if folded=='japan' or folded.endswith(' japan'):return True
        if unique_row_for_qth(data,qth):return True
        return False
    return bool(hint and str(hint.get('country','')).casefold()=='japan')


@dataclass
class Candidate:
    session: object
    snapshot: object
    path: Path
    line: int
    raw: str
    own: str
    qso: object
    mode: str
    qth_row: dict|None=None
    code_row: dict|None=None
    rmks_code: str=''
    prefecture_qth: str=''

    @property
    def key(self):return (str(self.path),self.line)

    def proposal(self,choice=''):
        """Return a changed QSO or None.  ``choice`` is only for mismatch mode."""
        q=self.qso
        if self.mode==MODE_CODE_TO_QTH:
            if not self.code_row:return None
            return replace(q,his_qth=_row_qth(self.code_row))
        if self.mode==MODE_RMKS_TO_BOTH:
            if not self.code_row:return None
            return replace(q,code=str(self.code_row.get('source_code','')).strip(),his_qth=_row_qth(self.code_row))
        if self.mode==MODE_RMKS_TO_PREF:
            return replace(q,his_qth=self.prefecture_qth) if self.prefecture_qth else None
        if self.mode==MODE_QTH_TO_CODE:
            if not self.qth_row:return None
            return replace(q,code=str(self.qth_row.get('source_code','')).strip())
        if self.mode==MODE_MISMATCH:
            if choice=='his_qth' and self.qth_row:
                return replace(q,code=str(self.qth_row.get('source_code','')).strip())
            if choice=='jccjcg' and self.code_row:
                return replace(q,his_qth=_row_qth(self.code_row))
        return None

    @property
    def can_adopt_his_qth(self):return bool(self.qth_row)
    @property
    def can_adopt_jccjcg(self):return bool(self.code_row)


def _consistent(qth_row,code_row):
    if not qth_row or not code_row:return False
    qsrc=str(qth_row.get('source_code','')).upper();csrc=str(code_row.get('source_code','')).upper()
    if qsrc==csrc:return True
    # A generic five-digit JCG is consistent with its municipality-specific row.
    qcode=str(qth_row.get('code','')).upper();ccode=str(code_row.get('code','')).upper()
    return bool(qcode and qcode==ccode and (qsrc==ccode or csrc==qcode))


def collect(repo,paths,own,mode,start='',end='',force=False):
    if mode not in MODES:raise ValueError('JCC/JCG一括処理の方法を選択してください。')
    start_text=str(start).strip();end_text=str(end).strip()
    lo=boundary_datetime(start_text,False,14) if start_text else None
    hi=boundary_datetime(end_text,True,14) if end_text else None
    if lo and hi and lo>hi:raise ValueError('開始日時は終了日時以前にしてください。')
    data=load_locations(repo.root);country_db=load_countries(repo.root);wanted=str(own or '').strip().upper()

    # First collect only lightweight QSO references.  When no date range is
    # supplied, reduce the working set to the latest 2,000 QSOs *before* the
    # comparatively expensive JCC/JCG/QTH matching.  This keeps large,
    # multi-year logbooks responsive while an explicit date range remains
    # unlimited.
    source_rows=[]
    for path in sorted({Path(p).resolve() for p in paths}):
        identity=file_identity(path)
        if not identity:raise ValueError(f'自局を特定できないログ名です: {path.name}')
        if wanted and identity[1].split('/',1)[0]!=wanted.split('/',1)[0]:continue
        session=repo.open(path)
        if session.snapshot.data is None:raise StorageError('選択したログが見つかりません。')
        if session.log.issues:raise StorageError(path.name+' に要確認行があります。一括処理できません。')
        for line,q in session.log.records:
            st=_stamp(q)
            if lo and st<lo or hi and st>hi:continue
            source_rows.append((st,str(path),line,session,path,identity[1],q))
    if not lo and not hi and len(source_rows)>DEFAULT_RECENT_LIMIT:
        source_rows=sorted(source_rows,key=lambda x:(x[0],x[1],x[2]),reverse=True)[:DEFAULT_RECENT_LIMIT]
    source_rows.sort(key=lambda x:(x[0],x[1],x[2]))

    out=[];code_cache={};qth_cache={}
    def code_row(value):
        key=str(value or '').strip().upper()
        if key not in code_cache:code_cache[key]=unique_row_for_code(data,key) if key else None
        return code_cache[key]
    def qth_row(value):
        key=str(value or '').strip()
        folded=key.casefold()
        if folded not in qth_cache:qth_cache[folded]=unique_row_for_qth(data,key) if key and not _japan_or_blank(key) else None
        return qth_cache[folded]

    for _,_,line,session,path,identity_own,q in source_rows:
        if not _domestic_qso(country_db,data,q):continue
        qrow=qth_row(q.his_qth)
        crow=code_row(q.code)
        rmks_code='';prefecture_qth=''
        include=False
        if mode==MODE_CODE_TO_QTH:
            include=(bool(force) or _japan_or_blank(q.his_qth)) and bool(crow)
        elif mode==MODE_RMKS_TO_BOTH:
            if bool(force) or _japan_or_blank(q.his_qth):
                rmks_code=code_from_rmks(q.remarks);crow=code_row(rmks_code) if rmks_code else None
                include=bool(crow)
        elif mode==MODE_RMKS_TO_PREF:
            if _japan_or_blank(q.his_qth):
                prefecture_qth=prefecture_qth_from_rmks(data,q.remarks);include=bool(prefecture_qth)
        elif mode==MODE_QTH_TO_CODE:
            include=not str(q.code).strip() and bool(qrow)
        else:
            if str(q.code).strip() and str(q.his_qth).strip():
                include=bool((qrow or crow) and not _consistent(qrow,crow))
        if include:
            out.append(Candidate(session,session.snapshot,path,line,session.log.lines[line-1].raw,identity_own,q,mode,qrow,crow,rmks_code,prefecture_qth))
    return out


def _edited_bytes(session,changes):
    new=[]
    for number,row in enumerate(session.log.lines,1):
        if number not in changes:new.append(row.raw);continue
        q=changes[number];q.validate()
        old=row.raw
        ending='\r\n' if old.endswith('\r\n') else '\n' if old.endswith('\n') else '\r' if old.endswith('\r') else ''
        new.append(q.to_ps()+ending)
    body=''.join(new).encode('utf-8')
    return (b'\xef\xbb\xbf' if session.log.bom else b'')+body


def commit(repo,selections):
    """Apply ``[(candidate, choice), ...]`` as one recoverable multi-file batch."""
    selections=list(selections)
    if not selections:raise StorageError('実行する交信が選択されていません。')
    targets={}
    seen=set()
    for candidate,choice in selections:
        if candidate.key in seen:continue
        seen.add(candidate.key)
        q=candidate.proposal(choice)
        if q is None:raise StorageError('選択した交信の修正内容を確定できません。')
        if q==candidate.qso:continue
        t=targets.setdefault(candidate.path,{'session':candidate.session,'changes':{},'candidates':[]})
        if t['session'].snapshot!=candidate.snapshot:raise ExternalChange('同じログの読み込み状態が一致しません。再読込してください。')
        t['changes'][candidate.line]=q;t['candidates'].append(candidate)
    if not targets:raise StorageError('実際に変更される交信がありません。')
    plans=[]
    for path,t in sorted(targets.items(),key=lambda x:str(x[0])):
        s=t['session'];s.snapshot.check(path)
        if s.log.issues:raise StorageError(path.name+' に要確認行があります。一括処理できません。')
        for c in t['candidates']:
            if c.snapshot!=s.snapshot or not 1<=c.line<=len(s.log.lines) or s.log.lines[c.line-1].raw!=c.raw:
                raise ExternalChange('対象行が変更されています。対象を再抽出してください。')
        plans.append((path,s,_edited_bytes(s,t['changes'])))
    with operation_lock(repo.book):
        for path,s,_ in plans:s.snapshot.check(path)
        for path,s,_ in plans:repo.backup(path,s.snapshot.data)
        from batch_recovery import create,recover_locked
        intent=create(repo,'jccjcg',[(path,s.snapshot,data) for path,s,data in plans],{})
        try:
            for path,s,data in plans:
                replace_bytes(path,data,s.snapshot);repo.started.add(path);repo.changed.add(path)
            intent.finish()
        except (StorageError,OSError):
            try:recover_locked(repo.book)
            except (StorageError,OSError) as recovery_error:
                raise StorageError('JCC/JCG一括処理を完了できませんでした。回復記録を保全して「ログを再読込」してください。\n'+str(recovery_error)) from recovery_error
            for path,_,_ in plans:repo.started.add(path);repo.changed.add(path)
        for path,_,_ in plans:
            try:repo.prune(path)
            except OSError:pass
    return len(seen),len(plans)
