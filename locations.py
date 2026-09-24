"""Location master and separately identified unverified log spellings."""
import json,sys,re,unicodedata
from pathlib import Path
from storage import StorageError
from input_normalization import jccjcg_parts

def normalize_jcg_gun(value):
    """Return PSLog's display spelling for a JCG county: ``Inagun``, not ``Ina gun``.

    The supplied reference master intentionally keeps mechanically separated
    tokens.  PSLog's human-facing QTH convention joins the county name and
    ``gun`` while leaving all other spacing untouched.
    """
    parts=str(value or '').strip().split()
    for i,part in enumerate(parts):
        if part.casefold()=='gun' and i>0:
            parts[i-1]=parts[i-1]+'gun'
            del parts[i]
            break
    return ' '.join(parts)


def qth_for_row(row):
    qth=str(row.get('verified_qth') or row.get('reference_qth') or '').strip()
    if str(row.get('kind','')).upper()=='JCG':
        qth=normalize_jcg_gun(qth)
    return qth


def load(root):
    path=Path(root)/'config/db/locations.json'
    if not path.exists():path=Path(getattr(sys,'_MEIPASS',Path(__file__).parent))/'config/db/locations.json'
    try:
        data=json.loads(path.read_text('utf-8'))
        if data.get('version')!=1 or not isinstance(data['rows'],list):raise ValueError('未対応の所在地DBです。')
        from location_overrides import merge
        return merge(data,root)
    except (OSError,ValueError,KeyError,TypeError) as e:raise StorageError('所在地DBを読めません: '+str(e)) from e

def find(data,query):
    words=query.casefold().split()
    return [r for r in data['rows'] if all(w in (r['name']+' '+r['kind']+' '+r['source_code']+' '+r['verified_qth']+' '+r.get('reference_qth','')+' '+qth_for_row(r)).casefold() for w in words)]

def candidates(data,row):
    keys=[row['kind']+' '+row['source_code']]
    if row['kind']=='JCG' and row['source_code']!=row['code']:keys.append('JCG '+row['code'])
    values=[]
    if row['verified_qth']:
        values.append((normalize_jcg_gun(row['verified_qth']) if row.get('kind')=='JCG' else row['verified_qth'],row.get('qth_source','会話で確認済み')))
    if row.get('reference_qth') and row['reference_qth']!=row['verified_qth']:
        values.append((normalize_jcg_gun(row['reference_qth']) if row.get('kind')=='JCG' else row['reference_qth'],row['reference_source']))
    seen={v[0] for v in values}
    for key in keys:
        for qth,count in sorted(data['spellings'].get(key,{}).items(),key=lambda i:(-i[1],i[0])):
            display_qth=normalize_jcg_gun(qth) if row.get('kind')=='JCG' else qth
            if display_qth not in seen:
                values.append((display_qth,f'ログ由来・未確認（{count}件）'+('／郡内の別町村を含む' if key=='JCG '+row['code'] and row['source_code']!=row['code'] else '')));seen.add(display_qth)
    return values

def confirmed(data,japanese,code=''):
    kind,value=jccjcg_parts(code) if str(code or '').strip() else ('','')
    found=[r for r in data['rows'] if r['name']==japanese and r['verified_qth'] and (not kind or r['kind']==kind) and (not value or value in (r['code'],r['source_code']))]
    return qth_for_row(found[0]) if len(found)==1 else None


def normalize_lookup(value):
    value=unicodedata.normalize('NFKC',str(value or '')).casefold()
    value=re.sub(r'[,，、]+',' ',value)
    return ' '.join(value.split())

def exact_matches(data,text):
    needle=normalize_lookup(text)
    if not needle:return []
    found=[]
    for row in data.get('rows',[]):
        values={normalize_lookup(row.get('name','')),normalize_lookup(row.get('verified_qth','')),normalize_lookup(row.get('reference_qth','')),normalize_lookup(qth_for_row(row))}
        values.discard('')
        if needle in values:found.append(row)
    return found
