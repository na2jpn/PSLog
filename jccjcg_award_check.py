"""Read-only JCC/JCG worked/QSL status aggregation for award checking."""
from dataclasses import dataclass
from pathlib import Path
import json
import re
import unicodedata

from input_normalization import jccjcg_parts
from logbook_sources import amateur_log_files,file_identity,base_station_call
from storage import StorageError

STATE_NONE = 0
STATE_WORKED = 1
STATE_QSL = 2
STATE_TEXT = {STATE_NONE:'—', STATE_WORKED:'交信済', STATE_QSL:'QSL済'}

BAND_ORDER = (
    '0.135','0.475','1.8','1.9','3.5','7','10','14','18','21','24','28',
    '50','144','430','1200','2400','5600','10000','24000','47000','77000',
    '135000','248000','SAT',
)
BAND_LABEL = {
    '0.135':'135k','0.475':'475k','1.8':'1.8','1.9':'1.9','3.5':'3.5','7':'7',
    '10':'10','14':'14','18':'18','21':'21','24':'24','28':'28','50':'50',
    '144':'144','430':'430','1200':'1200','2400':'2400','5600':'5.6G',
    '10000':'10G','24000':'24G','47000':'47G','77000':'77G','135000':'135G',
    '248000':'248G','SAT':'SAT',
}

_PREF_NAMES = {
    '01':'北海道','02':'青森県','03':'岩手県','04':'秋田県','05':'山形県','06':'宮城県','07':'福島県',
    '08':'新潟県','09':'長野県','10':'東京都','11':'神奈川県','12':'千葉県','13':'埼玉県','14':'茨城県',
    '15':'栃木県','16':'群馬県','17':'山梨県','18':'静岡県','19':'岐阜県','20':'愛知県','21':'三重県',
    '22':'京都府','23':'滋賀県','24':'奈良県','25':'大阪府','26':'和歌山県','27':'兵庫県','28':'富山県',
    '29':'福井県','30':'石川県','31':'岡山県','32':'島根県','33':'山口県','34':'鳥取県','35':'広島県',
    '36':'香川県','37':'徳島県','38':'愛媛県','39':'高知県','40':'福岡県','41':'佐賀県','42':'長崎県',
    '43':'熊本県','44':'大分県','45':'宮崎県','46':'鹿児島県','47':'沖縄県',
}

@dataclass(frozen=True)
class LocationStatus:
    kind: str              # JCC / JCG
    code: str
    name: str
    prefecture_code: str
    prefecture_name: str
    states: dict

    @property
    def all_state(self):
        return max(self.states.values(), default=STATE_NONE)

@dataclass(frozen=True)
class PrefectureStatus:
    code: str
    name: str
    locations: tuple

    def badges(self):
        """Return the strongest completion badge for each award kind.

        QSL complete implies worked complete, so showing both is redundant in the
        folded prefecture row. Keep only the stronger QSL badge when applicable.
        """
        out=[]
        for kind in ('JCC','JCG'):
            rows=[r for r in self.locations if r.kind==kind]
            if not rows:
                continue
            if all(r.all_state>=STATE_QSL for r in rows):out.append(f'全{kind}-QSL済')
            elif all(r.all_state>=STATE_WORKED for r in rows):out.append(f'全{kind}-交信済')
        return out

    def cfm_remaining(self):
        """Return unconfirmed award-unit counts as ``((kind,count),...)``.

        Unworked units are also unconfirmed. A kind with no current master units
        is omitted.
        """
        out=[]
        for kind in ('JCC','JCG'):
            rows=[r for r in self.locations if r.kind==kind]
            if not rows:
                continue
            remaining=sum(1 for r in rows if r.all_state<STATE_QSL)
            if remaining:out.append((kind,remaining))
        return tuple(out)

    def folded_summary(self):
        """Human-facing text appended to a folded prefecture row."""
        parts=list(self.badges())
        remaining=self.cfm_remaining()
        if remaining:
            parts.append('（CFM '+'　'.join(f'残{kind} {count}' for kind,count in remaining)+'）')
        return '　'.join(parts)

@dataclass(frozen=True)
class AwardCheckResult:
    own: str
    portable: bool
    files: int
    qsos: int
    matched: int
    bands: tuple
    prefectures: tuple
    problems: tuple


def _db_path(root, filename):
    path=Path(root)/'config/db'/filename
    if path.exists():return path
    import sys
    return Path(getattr(sys,'_MEIPASS',Path(__file__).parent))/'config/db'/filename


def _pref_code(row):
    match=re.search(r'\b(\d{2})\s*$',str(row.get('prefecture','')))
    if match:return match.group(1)
    code=str(row.get('code',''))
    return code[:2] if len(code)>=2 else ''


def _strip_prefecture(full,code):
    text=' '.join(str(full or '').split())
    prefix=_PREF_NAMES.get(code,'')
    if prefix and text.startswith(prefix):return text[len(prefix):].strip()
    return text


def _current_master(root):
    """Build current award units from PSLog's current location database."""
    path=_db_path(root,'locations.json')
    try:data=json.loads(path.read_text('utf-8'))
    except (OSError,ValueError,TypeError) as e:raise StorageError('JCC/JCG地域一覧を読めません: '+str(e)) from e
    rows=data.get('rows') if isinstance(data,dict) else None
    if data.get('version')!=1 or not isinstance(rows,list):return None
    units={}
    jcc6=[]
    for row in rows:
        kind=row.get('kind');code=str(row.get('code',''))
        pc=code[:2] if len(code)>=2 else ''
        if kind=='JCC' and re.fullmatch(r'\d{4}',code):
            units[('JCC',code)]={'kind':'JCC','code':code,'name':_strip_prefecture(row.get('name',''),pc),'prefecture_code':pc,'prefecture_name':_PREF_NAMES.get(pc,'')}
        elif kind=='JCC' and re.fullmatch(r'\d{6}',code):
            jcc6.append(row)
        elif kind=='JCG' and re.fullmatch(r'\d{5}',code):
            if ('JCG',code) in units:continue
            local=_strip_prefecture(row.get('name',''),pc)
            match=re.match(r'(.+?(?:郡|支庁))(?:.+)?$',local)
            name=match.group(1) if match else local
            units[('JCG',code)]={'kind':'JCG','code':code,'name':name,'prefecture_code':pc,'prefecture_name':_PREF_NAMES.get(pc,'')}
    for row in jcc6:
        code=str(row['code']);parent=code[:4];pc=code[:2];local=_strip_prefecture(row.get('name',''),pc)
        if parent=='1001':
            units[('JCC',code)]={'kind':'JCC','code':code,'name':local,'prefecture_code':pc,'prefecture_name':_PREF_NAMES.get(pc,'東京都')}
            continue
        if ('JCC',parent) not in units:
            match=re.match(r'(.+?市)(?:.+)?$',local)
            name=match.group(1) if match else local
            units[('JCC',parent)]={'kind':'JCC','code':parent,'name':name,'prefecture_code':pc,'prefecture_name':_PREF_NAMES.get(pc,'')}
    return tuple(sorted(units.values(),key=lambda r:(r['prefecture_code'],0 if r['kind']=='JCC' else 1,r['code'])))


def _legacy_master(root):
    """Fallback for older development trees that do not have locations.json."""
    path=_db_path(root,'aja_locations.json')
    try:data=json.loads(path.read_text('utf-8'))
    except (OSError,ValueError,TypeError) as e:raise StorageError('JCC/JCG地域一覧を読めません: '+str(e)) from e
    rows=data.get('rows') if isinstance(data,dict) else None
    if not isinstance(rows,list):raise StorageError('JCC/JCG地域一覧の形式が不正です。')
    units={}
    for row in rows:
        kind=row.get('kind');code=str(row.get('code',''))
        if kind=='city' and re.fullmatch(r'\d{4}',code):award_kind='JCC'
        elif kind=='gun' and re.fullmatch(r'\d{5}',code):award_kind='JCG'
        else:continue
        pc=_pref_code(row);units[(award_kind,code)]={'kind':award_kind,'code':code,'name':str(row.get('name','')).strip(),'prefecture_code':pc,'prefecture_name':_PREF_NAMES.get(pc,str(row.get('prefecture','')).rsplit(' ',1)[0])}
    ward_rows=[r for r in rows if r.get('kind')=='ward' and re.fullmatch(r'\d{6}',str(r.get('code','')))]
    for row in ward_rows:
        code=str(row['code']);parent=code[:4];pc=_pref_code(row);local=str(row.get('name','')).strip()
        if parent=='1001':
            units[('JCC',code)]={'kind':'JCC','code':code,'name':local,'prefecture_code':pc,'prefecture_name':_PREF_NAMES.get(pc,'東京都')}
        elif ('JCC',parent) not in units:
            match=re.match(r'(.+?市)(?:\s|$)', ' '.join(local.split()))
            units[('JCC',parent)]={'kind':'JCC','code':parent,'name':match.group(1) if match else local,'prefecture_code':pc,'prefecture_name':_PREF_NAMES.get(pc,'')}
    return tuple(sorted(units.values(),key=lambda r:(r['prefecture_code'],0 if r['kind']=='JCC' else 1,r['code'])))


def load_award_master(root):
    """Return current JCC/JCG award units, with a legacy DB fallback."""
    current=_current_master(root)
    return current if current is not None else _legacy_master(root)

def award_band(qso):
    text=unicodedata.normalize('NFKC',(str(qso.remarks or '')+' '+str(qso.mode or '')).upper())
    if re.search(r'(?<![A-Z0-9])(?:SAT(?:ELLITE)?|FO[- ]?\d+|JAS[- ]?\d+)(?![A-Z0-9])',text):return 'SAT'
    raw=unicodedata.normalize('NFKC',str(qso.band or '')).strip().upper().replace('MHZ','').replace('GHZ','G')
    aliases={'3.8':'3.5','29':'28','433':'430','5.6G':'5600','5.7G':'5600','10G':'10000','10.1G':'10000','10.4G':'10000','10100':'10000','10400':'10000','24G':'24000','47G':'47000','77G':'77000','135G':'135000','248G':'248000'}
    raw=aliases.get(raw,raw)
    if raw in BAND_ORDER:return raw
    # Preserve an otherwise valid machine-like band as a visible extra column
    # rather than silently dropping a QSO from the all-band result.
    return raw


def _award_unit(kind,code,date,known):
    if kind=='JCG':
        match=re.fullmatch(r'(\d{5})(?:[A-Z])?',code or '')
        return ('JCG',match.group(1)) if match and ('JCG',match.group(1)) in known else None
    if kind!='JCC':return None
    if re.fullmatch(r'\d{4}',code or ''):
        return ('JCC',code) if ('JCC',code) in known else None
    if re.fullmatch(r'\d{6}',code or ''):
        if code.startswith('1001'):
            # JARL/AJA treatment changed in 2010; pre-change Tokyo ward QSOs do
            # not satisfy the current JCC-equivalent special-ward unit.
            return ('JCC',code) if (not date or date>='2010-04-01') and ('JCC',code) in known else None
        parent=code[:4]
        return ('JCC',parent) if ('JCC',parent) in known else None
    return None


def aggregate(repo, own, portable=True):
    own=base_station_call(own)
    if not own:raise ValueError('対象自局コールを選択してください。')
    master=load_award_master(repo.root);known={(r['kind'],r['code']):r for r in master}
    states={key:{} for key in known};problems=[];files=qsos=matched=0;extra_bands=set()
    for path in amateur_log_files(repo):
        identity=file_identity(path)
        if not identity:continue
        actual=identity[1]
        if not (actual==own or (portable and actual.startswith(own+'/'))):continue
        files+=1
        try:session=repo.open(path)
        except (StorageError,OSError) as e:
            problems.append(f'{path.name}: {e}');continue
        problems.extend(f'{path.name}:{issue.line} {issue.reason}' for issue in session.log.issues)
        for _,qso in session.log.records:
            qsos+=1
            kind,code=jccjcg_parts(qso.code)
            unit=_award_unit(kind,code,qso.date,known)
            if not unit:continue
            matched+=1
            band=award_band(qso)
            if band and band not in BAND_ORDER:extra_bands.add(band)
            current=states[unit].get(band,STATE_NONE) if band else STATE_NONE
            status=STATE_QSL if qso.confirmed else STATE_WORKED
            if band:states[unit][band]=max(current,status)
            # Preserve a QSO with an unknown/blank band in the all-band state.
            states[unit]['*']=max(states[unit].get('*',STATE_NONE),status)
    bands=tuple(BAND_ORDER)+tuple(sorted(extra_bands,key=str.casefold))
    grouped={code:[] for code in _PREF_NAMES}
    for row in master:
        key=(row['kind'],row['code']);band_states={b:states[key].get(b,STATE_NONE) for b in bands}
        band_states['*']=states[key].get('*',STATE_NONE)
        grouped.setdefault(row['prefecture_code'],[]).append(LocationStatus(states=band_states,**row))
    prefectures=[]
    for code in sorted(grouped):
        rows=tuple(grouped[code])
        if not rows:continue
        prefectures.append(PrefectureStatus(code,_PREF_NAMES.get(code,rows[0].prefecture_name),rows))
    return AwardCheckResult(own,portable,files,qsos,matched,bands,tuple(prefectures),tuple(problems))
