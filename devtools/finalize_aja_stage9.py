"""Create a checked handoff for the AJA implementation through step 9."""
from pathlib import Path
import hashlib,json,os,re,sys,tempfile,zipfile,zlib

ROOT=Path(__file__).resolve().parents[1]
HANDOFF=ROOT.parents[1]
PREFIX='PSLOG101/pslog-1.01/'
REFERENCE_PREFIXES=(
    'docs/activity-research/sources/',
    'docs/contest-research/sources/',
    'docs/reference-vault/',
    'tools/reference/',
)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def checked_tests(logpath):
    text=Path(logpath).read_text(errors='replace')
    match=re.search(r'Ran (\d+) tests',text)
    if not match or not text.rstrip().endswith('OK'):
        raise ValueError('successful unittest log required')
    count=int(match.group(1))
    if count!=575:
        raise ValueError(f'expected 575 tests, got {count}')
    return count

def groups(files):
    source=[];references=[]
    for path in files:
        rel=path.relative_to(ROOT).as_posix()
        (references if rel.startswith(REFERENCE_PREFIXES) else source).append(path)
    batches=[source];current=[];size=0
    for path in references:
        estimate=len(zlib.compress(path.read_bytes(),9))+len(str(path))*2+200
        if current and size+estimate>6*1024*1024:
            batches.append(current);current=[];size=0
        current.append(path);size+=estimate
    if current:batches.append(current)
    return batches

def package(logpath):
    tests=checked_tests(logpath)
    files=sorted(p for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc')
    manifest={p.relative_to(ROOT).as_posix():sha(p) for p in files}
    report=(ROOT/'docs/CHECKPOINT_PSLOG101_AJA_STAGE9.md').read_text()
    outputs=[]
    for index,batch in enumerate(groups(files)):
        name='PSLOG101_aja_stage9_source.zip' if index==0 else f'PSLOG101_aja_stage9_references_{index:02}.zip'
        target=HANDOFF/name
        fd,tempname=tempfile.mkstemp(prefix='pslog-aja-stage9-',suffix='.zip',dir='/tmp');os.close(fd);temp=Path(tempname)
        try:
            with zipfile.ZipFile(temp,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
                for path in batch:
                    archive.write(path,PREFIX+path.relative_to(ROOT).as_posix())
                if index==0:
                    archive.writestr('PSLOG101/START_HERE.md',report)
                    archive.writestr('PSLOG101/handoff/MANIFEST.json',json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
                    archive.write(logpath,'PSLOG101/handoff/tests.log')
            with zipfile.ZipFile(temp) as archive:
                if archive.testzip() is not None:raise ValueError('CRC verification failed')
            os.replace(temp,target)
        finally:
            if temp.exists():temp.unlink()
        outputs.append({'path':str(target),'bytes':target.stat().st_size,'sha256':sha(target),'files':len(batch)})
    check={'created':'2026-09-15','stage':'aja-9-of-12','tests':tests,'files':len(files),'manifest_entries':len(manifest),'archives':outputs,'pending_steps':[10,11,12]}
    check_path=HANDOFF/'PSLOG101_aja_stage9_package_checks.json'
    check_path.write_text(json.dumps(check,ensure_ascii=False,indent=2)+'\n')
    for item in outputs:
        with zipfile.ZipFile(item['path']) as archive:
            if archive.testzip() is not None:raise ValueError(item['path'])
    print(json.dumps(check,ensure_ascii=False))

if __name__=='__main__':
    package(sys.argv[1])
