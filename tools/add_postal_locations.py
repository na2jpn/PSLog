"""Build reviewable PSLog spellings from Japan Post's seven-column roman CSV ZIP."""
import csv,io,json,re,sys,zipfile,hashlib
from pathlib import Path
try:from .postal_exceptions import ALIASES,TRUNCATED,PARENT_CITIES,HISTORICAL_QTH
except ImportError:from postal_exceptions import ALIASES,TRUNCATED,PARENT_CITIES,HISTORICAL_QTH

def normalize(value):return re.sub(r'\s+','',value)
def spelling(pref,city):
    pref=re.sub(r' (TO|FU|KEN)$','',pref).title()
    district=re.fullmatch(r'(.+) GUN (.+) (CHO|MACHI|MURA|SON)',city)
    ward=re.fullmatch(r'(.+) SHI (.+) KU',city)
    ordinary=re.fullmatch(r'(.+) (SHI|KU|CHO|MACHI|MURA|SON)',city)
    if city in TRUNCATED:place=TRUNCATED[city]
    elif district:place=district[2].title()+' '+district[1].title()+' gun'
    elif ward:place=ward[2].title()+' '+ward[1].title()
    elif ordinary:place=ordinary[1].title()
    else:return None
    return place+' '+pref+' Japan'

def build(db,raw):
    lookup={}
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        names=[n for n in z.namelist() if n.lower().endswith('.csv')]
        if len(names)!=1:raise ValueError('CSVが1個のZIPを指定してください')
        for row in csv.reader(io.StringIO(z.read(names[0]).decode('cp932'))):
            if len(row)!=7:raise ValueError('郵便ローマ字CSVは7列が必要です')
            lookup.setdefault(normalize(row[1]+row[2]),set()).add((row[4],row[5]))
    unresolved=[];count=0;historical_count=0
    for row in db['rows']:
        if row['kind']=='JCG' and row['source_code']=='24010H' and row['name']=='奈良県吉野郡':
            row['original_name']=row['name']
            row['name']='奈良県吉野郡天川村'
            row['name_correction_source']='利用者確認: 奈良県支部ページ掲載情報（URL未提供）'
        name=normalize(row['name']);alias=ALIASES.get(name,name)
        matches=lookup.get(alias,set());basis='所在地名照合' if alias==name else '明示的表記対応: '+alias
        if not matches and name in PARENT_CITIES:
            jp,roman=PARENT_CITIES[name]
            matches={(pref,roman) for key,values in lookup.items() if key.startswith(jp) and key.endswith('区')
                     for pref,city in values if city.startswith(roman+' ')}
            basis='同一市の各区に共通する市名から取得'
        row.pop('reference_qth',None);row.pop('reference_source',None);row.pop('reference_match',None);row.pop('reference_notice',None)
        historical=HISTORICAL_QTH.get((row['source_code'],row['name']))
        if historical:
            row['reference_qth']=historical
            row['reference_source']='提供PHPの旧所在地名をPSLog形式でローマ字化／現在の所在地へ置換しない'
            row['reference_match']=row['name'];historical_count+=1;continue
        if len(matches)==1:
            pref,city=next(iter(matches));value=spelling(pref,city)
            if value:
                row['reference_qth']=value;row['reference_source']='日本郵便2025年6月版・'+basis+'／PSLog用整形・要確認';row['reference_match']=alias;count+=1;continue
        row['reference_notice']=('元資料に町村名がありません。町村を番号から推定せず、交信当時の所在地を確認してください。' if row['name']=='奈良県吉野郡' else '日本郵便2025年6月版に一致しません。旧名称・当時の所在地を確認してください。現在の名称や番号へ自動置換しません。')
        unresolved.append(dict(name=row['name'],kind=row['kind'],source_code=row['source_code'],reason='所在地名不一致' if not matches else '複数表記または未対応構造'))
    db['postal_reference']={'url':'https://www.post.japanpost.jp/service/search/zipcode/download/roman-zip.html','version':'2025-06','retrieved':'2026-09-12','zip_sha256':hashlib.sha256(raw).hexdigest(),'matched':count,'historical_candidates':historical_count,'total_candidates':count+historical_count,'unresolved':unresolved,'policy':'参照候補のみ。既存の確認済み表記や交信原本は変更しない。'}
    return db
if __name__=='__main__':
    db_path,zip_path=map(Path,sys.argv[1:]);data=build(json.loads(db_path.read_text('utf-8')),zip_path.read_bytes());db_path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(data['postal_reference']['matched'])
