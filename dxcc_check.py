"""Read-only DXCC worked/confirmed counts with QSO/file drilldown."""
from dataclasses import dataclass,field
import re
from countries import load
from country_history import load_history,historic_name,key,valid_entity
from logbook_sources import amateur_log_files,file_identity,base_station_call

@dataclass
class Entity:
    ident:str
    name:str
    deleted:bool=False
    hits:list=field(default_factory=list)
    names:set=field(default_factory=set)
    @property
    def confirmed(self):return sum(h.qso.confirmed for h in self.hits)
    @property
    def unconfirmed(self):return len(self.hits)-self.confirmed

@dataclass
class Result:
    entities:list
    files:int
    qsos:int
    problems:list
    unresolved:list
    @property
    def worked(self):return len(self.entities)
    @property
    def confirmed(self):return sum(bool(e.confirmed) for e in self.entities)


# Award labels are independent of historical names stored in HIS QTH.
AWARD_NAMES={'TA':'Turkey','ZS':'Republic of South Africa','ZD7':'Saint Helena','J6':'Saint Lucia','C2':'Nauru'}
ENTITY_ALIASES={
    'JD/m':('Minamitorishima','Minami Torishima Island','Marcus Island'),
    'E5/n':('North Cook Island','Northern Cook Islands'),
    'E5/s':('South Cook Island','Southern Cook Islands'),
    '3D2/r':('Rotuma','Rotuma Islands'),
}

def award_name(ident,name):
    return AWARD_NAMES.get(ident,name)

def resolve(db,history,q):
    if 'C7A' in q.call.strip().upper().split('/'):
        return None,'C7A：DXCC扱い未確定（局の公開説明）。ARRLの認定確認が必要です'
    if q.call.upper().endswith(('/MM','/AM')):return None,'海上／航空移動はDXCC対象外'
    if q.date<'1945-11-15':return None,'DXCC対象開始日前'
    raw=q.his_qth.strip()
    if getattr(db,"_dxcc_history_id",None)!=id(history):
        rows={r['entity_prefix']:{'id':r['entity_prefix'],'name':r['country']} for r in list(db.prefixes.values())+list(db.exact.values())}
        for r in history.get('entities',[]):rows[r['id']]=dict(r)
        aliases={}
        for r in rows.values():
            for name in [r['name'],award_name(r['id'],r['name'])]+r.get('aliases',[])+list(ENTITY_ALIASES.get(r['id'],())):
                aliases[key(name)]=r
                aliases[key(re.sub(r'\bSt\.?\s+', 'Saint ',name))]=r
        for r in history.get('names',[]):
            target=next((v for v in rows.values() if key(v['name'])==key(r['canonical'])),None)
            if target:
                for name in r['aliases']+[x['name'] for x in r['periods']]:aliases[key(name)]=target
        for old,new in history.get('aliases',{}).items():
            if key(new) in aliases:aliases[key(old)]=aliases[key(new)]
        db._dxcc_history_id=id(history);db._dxcc_rows=rows;db._dxcc_aliases=aliases
    rows=db._dxcc_rows;aliases=db._dxcc_aliases
    found=None
    words=raw.split()
    while words and re.fullmatch(r"[A-Ra-r]{2}\d{2}(?:[A-Xa-x]{2})?",words[-1]):words.pop()
    for n in range(len(words)):
        found=aliases.get(key(' '.join(words[n:])))
        if found:break
    if not found and raw:
        # Unknown written locality is not replaced with a home-prefix guess.
        if not re.fullmatch(r'[A-Ra-r]{2}\d{2}(?:[A-Xa-x]{2})?',raw):return None,'記録QTHからエンティティを確認できません'
    if not found:
        hint=db.lookup(q.call)
        if not hint:return None,'運用地を確認できません'
        found=rows.get(hint['entity_prefix'])
        if q.date<'1945-11-15':return None,'DXCC対象開始日前'
        if q.date<'1991-01-01':return None,'過去プリフィックスの有効期間を確認してください'
    if not found or not valid_entity(found,q):return None,'交信日時がエンティティの確認済み有効期間外です'
    name=historic_name(found['name'],q.date,history)
    return dict(found,historical_name=name),''


def aggregate(repo,own,cancelled=lambda:False):
    from search import Hit
    own=base_station_call(own)
    if not own:raise ValueError('対象自局コールを選択してください。')
    db=load(repo.root);history=load_history(repo.root);entities={};problems=[];unresolved=[];count=files=0
    for path in amateur_log_files(repo):
        if cancelled():raise InterruptedError('集計を中止しました。')
        identity=file_identity(path)
        if base_station_call(identity[1])!=own:continue
        files+=1;s=repo.open(path)
        problems.extend(f'{path.name}: {x}' for x in s.log.issues)
        for line,q in s.log.records:
            if cancelled():raise InterruptedError('集計を中止しました。')
            count+=1;hit=Hit(s,s.snapshot,line,s.log.lines[line-1].raw,q,identity[1])
            row,reason=resolve(db,history,q)
            if not row:unresolved.append((hit,reason));continue
            e=entities.setdefault(row['id'],Entity(row['id'],award_name(row['id'],historic_name(row['name'],None,history)),row.get('deleted',False)))
            e.hits.append(hit);e.names.add(row['historical_name'])
    return Result(sorted(entities.values(),key=lambda e:e.name.casefold()),files,count,problems,unresolved)
