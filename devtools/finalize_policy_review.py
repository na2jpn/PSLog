"""Final definition checkpoint: keep history and atomically create archives."""
from pathlib import Path
import json,sys,zipfile,hashlib,zlib,tempfile,os,re
ROOT=Path(__file__).resolve().parents[1];HANDOFF=ROOT.parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'devtools')]
from finalize_final9 import preserve
from checkpoint_regional import collect_research

def preserve_remaining1():
    count=0
    for path in [HANDOFF/'verify_remaining1_v1/PSLOG101_remaining1_source.zip']+sorted(HANDOFF.glob('PSLOG101_remaining1_references_*.zip')):
        with zipfile.ZipFile(path) as z:
            assert z.testzip() is None
            for n in z.namelist():
                if 'pslog-1.01/' not in n or n.endswith('/'):continue
                rel=n.split('pslog-1.01/',1)[1];p=ROOT/rel;assert p.is_file(),rel;count+=1
                if rel.startswith(('docs/contest-research/sources/','tools/reference/')):assert p.read_bytes()==z.read(n),rel
    assert count==845,count
    return {'remaining1_preserved_files':count}

def preserve_remaining0():
    with zipfile.ZipFile(HANDOFF/'verify_remaining0/PSLOG101_remaining0_source.zip') as z:
        manifest=json.loads(z.read('PSLOG101/handoff/MANIFEST.json'))
    for rel,digest in manifest.items():
        p=ROOT/rel;assert p.is_file(),rel
        if rel.startswith(('docs/contest-research/sources/','tools/reference/','docs/reference-vault/')):assert hashlib.sha256(p.read_bytes()).hexdigest()==digest,rel
    assert len(manifest)==854
    return {'remaining0_preserved_files':len(manifest)}

def prepare(logpath):
    log=Path(logpath).read_text();assert log.rstrip().endswith('OK');tested=int(re.search(r'Ran (\d+) tests',log)[1]);assert tested==554
    tracker=json.loads((ROOT/'docs/CONTEST_IMPLEMENTATION_TRACKER.json').read_text())
    audit={'checked_on':'2026-09-15','defined':87,'undefined':0,'tests':tested,'report':'PSLOG101_POLICY_REVIEW.md','contests':tracker['contests']}
    (ROOT/'docs/contest-research/PSLOG101_CURRENT_AUDIT.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
    collect_research(tracker,[],0)
    report=(ROOT/'docs/contest-research/PSLOG101_POLICY_REVIEW.md').read_text()
    (HANDOFF/'PSLOG101_policy_review_START_HERE.md').write_text(report)
    (HANDOFF/'PSLOG101_contest_research_policy_review.md').write_bytes((ROOT/'docs/CONTEST_RESEARCH_ALL.md').read_bytes())
    return report

def package(logpath):
    report=prepare(logpath);preserved=preserve();preserved.update(preserve_remaining1());preserved.update(preserve_remaining0());files=sorted(p for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc');manifest={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    references=[p for p in files if p.relative_to(ROOT).as_posix().startswith(('docs/contest-research/sources/','tools/reference/'))];source=[p for p in files if p not in references]
    batches=[source];current=[];size=0
    for p in references:
        compressed=len(zlib.compress(p.read_bytes(),9))+len(str(p))*2+150
        if size+compressed>6*1024*1024 and current:batches.append(current);current=[];size=0
        current.append(p);size+=compressed
    if current:batches.append(current)
    outputs=[]
    for i,group in enumerate(batches):
        out=HANDOFF/('PSLOG101_policy_review_source.zip' if i==0 else f'PSLOG101_policy_review_references_{i:02}.zip')
        temp=Path(tempfile.mkstemp(prefix='pslog0-',suffix='.zip',dir='/tmp')[1])
        with zipfile.ZipFile(temp,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
            for p in group:z.write(p,'PSLOG101/pslog-1.01/'+p.relative_to(ROOT).as_posix())
            if i==0:
                z.writestr('PSLOG101/START_HERE.md',report);z.writestr('PSLOG101/handoff/MANIFEST.json',json.dumps(manifest,indent=2));z.write(logpath,'PSLOG101/handoff/tests.log');z.writestr('PSLOG101/handoff/preservation.json',json.dumps(preserved,indent=2))
        with zipfile.ZipFile(temp) as z:assert z.testzip() is None
        os.replace(temp,out)
        assert out.stat().st_size<7*1024*1024
        outputs.append(dict(path=str(out),bytes=out.stat().st_size,sha256=hashlib.sha256(out.read_bytes()).hexdigest(),source_files=len(group)))
    metadata=dict(files=len(files),defined=87,pending=[],preserved=preserved,archives=outputs)
    (HANDOFF/'PSLOG101_policy_review_package_checks.json').write_text(json.dumps(metadata,indent=2));print(json.dumps(metadata,ensure_ascii=False))
if __name__=='__main__':package(sys.argv[1])
