"""Convert supplied PHP dictionaries without executing PHP; collect log spellings."""
import re,json,hashlib,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from storage import parse

def build(jcc,jcg,logfile,out):
    rows=[];sources=[]
    for kind,path in [('JCC',Path(jcc)),('JCG',Path(jcg))]:
        data=path.read_bytes();sources.append({'name':path.name,'sha256':hashlib.sha256(data).hexdigest()})
        for name,code in re.findall(r'"([^"\n]+)"\s*=>\s*"([0-9]+[A-Z]?)"',data.decode('utf-8-sig')):
            rows.append({'name':name,'source_code':code,'kind':kind,'code':code[:5] if kind=='JCG' else code,'verified_qth':''})
    spellings={};data=Path(logfile).read_bytes();sources.append({'name':Path(logfile).name,'sha256':hashlib.sha256(data).hexdigest()})
    for _,q in parse(data).records:
        code=re.fullmatch(r'(JCC|JCG)\s+([0-9]+[A-Z]?)',q.code.strip(),re.I)
        if not code:continue
        text=re.sub(r'^[A-Ra-r]{2}[0-9]{2}(?:[A-Xa-x]{2}(?:[0-9]{2})?)?\s+','',q.his_qth.strip())
        if not text.isascii() or not text.endswith(' Japan'):continue
        key=code[1].upper()+' '+code[2].upper();values=spellings.setdefault(key,{})
        values[text]=values.get(text,0)+1
    # Explicit spellings established in the supplied conversation/specification.
    approved={'東京都足立区':'Adachi Tokyo Japan','埼玉県草加市':'Soka Saitama Japan','徳島県板野郡上板町':'Kamiita Itanogun Tokushima Japan'}
    for row in rows:row['verified_qth']=approved.get(row['name'],'')
    result={'version':1,'sources':sources,'note':'所在地コードは提供PHP時点。ログ由来の表記候補は自動確定しない。verified_qthは会話で確認済みの表記。','rows':rows,'spellings':spellings}
    Path(out).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print({'places':len(rows),'confirmed':sum(bool(r['verified_qth']) for r in rows),'codes_with_candidates':len(spellings)})
if __name__=='__main__':build(*sys.argv[1:])
