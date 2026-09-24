"""Free-radio cross-kind search for PSLog 1.14."""
from dataclasses import dataclass,replace
from input_normalization import jccjcg_code
from time_range import prefix_boundary
from storage import StorageError
from search import Hit
from free_radio import validate_free_call,free_files,free_file_identity,FREE_TYPES

@dataclass(frozen=True)
class FreeCriteria:
    own:str
    kind:str=''
    call:str=''
    remarks:str=''
    his_qth:str=''
    my_qth:str=''
    jccjcg:str=''
    start:str=''
    end:str=''
    def validate(self):
        validate_free_call(self.own)
        if self.kind and self.kind not in FREE_TYPES:raise ValueError('種類を選択してください。')
        try:start=prefix_boundary(self.start,False,12)
        except ValueError as e:raise ValueError('開始'+str(e)) from e
        try:end=prefix_boundary(self.end,True,12)
        except ValueError as e:raise ValueError('終了'+str(e)) from e
        if start and end and start>end:raise ValueError('開始日時は終了日時以前にしてください。')

@dataclass
class FreeResults:
    hits:list
    problems:list
    files:int


def free_search(repo,criteria):
    criteria.validate();start=prefix_boundary(criteria.start,False,12);end=prefix_boundary(criteria.end,True,12)
    hits=[];problems=[];count=0
    for path in free_files(repo,call=criteria.own,kind=criteria.kind):
        ident=free_file_identity(path)
        if not ident:continue
        _year,own,kind,_model=ident;count+=1
        try:session=repo.open(path)
        except (StorageError,OSError) as e:
            problems.append(f'{path.name}: {e}');continue
        problems.extend(f'{path.name}:{i.line} {i.reason}' for i in session.log.issues)
        for line,q in session.log.records:
            stamp=q.date.replace('-','')+q.time.replace(':','')+'00'
            if start and stamp<start:continue
            if end and stamp>end:continue
            if criteria.call.casefold() not in q.call.casefold():continue
            if criteria.remarks.casefold() not in q.remarks.casefold():continue
            if criteria.his_qth.casefold() not in q.his_qth.casefold():continue
            if criteria.my_qth.casefold() not in q.my_qth.casefold():continue
            if criteria.jccjcg:
                if jccjcg_code(criteria.jccjcg).casefold() not in jccjcg_code(q.code).casefold():continue
            hit=Hit(session,session.snapshot,line,session.log.lines[line-1].raw,replace(q),own)
            # Runtime-only presentation metadata; Hit stays compatible with existing edit safety.
            object.__setattr__(hit,'free_kind',kind)
            object.__setattr__(hit,'free_model',ident[3])
            hits.append(hit)
    hits.sort(key=lambda h:(h.qso.date,h.qso.time,h.path.name,h.line),reverse=True)
    return FreeResults(hits,problems,count)
