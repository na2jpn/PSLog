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

def prepare(logpath):
    log=Path(logpath).read_text();assert log.rstrip().endswith('OK');tested=int(re.search(r'Ran (\d+) tests',log)[1])
    tracker=json.loads((ROOT/'docs/CONTEST_IMPLEMENTATION_TRACKER.json').read_text());assert len(tracker['contests'])==87
    assert all(c['runtime_definition']!='未作成・未検証' for c in tracker['contests'])
    audit={'checked_on':'2026-09-15','defined_management_items':87,'undefined_management_items':0,'local_tests_passed':tested,'windows_verified':False,'organizer_acceptance_verified':False,'current_report':'PSLOG101_CURRENT_AUDIT.md','contests':tracker['contests']}
    (ROOT/'docs/contest-research/PSLOG101_CURRENT_AUDIT.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
    collect_research(tracker,['niigata_low_band','niigata_branch'],0)
    report=f"""# PSLOG101 再開入口・定義残り0

2026-09-15：新潟No.9／No.73の同一性を利用者確認により確定。87/87管理項目が定義済み、未定義0。新潟は7MHz・ハイバンド・ローバンドを独立提出し、ローバンドだけでも提出できます。別大会を87件作成した意味ではありません。

全体{tested}試験合格（Qt offscreen）。追加試験は他区分混在ログからローバンドだけを出力し、元ログ不変を確認。Windows実機・EXE作成・主催者受付は未検証です。追加形式、原典、年度、解釈の残件はPSLOG101_current_audit.mdをご覧ください。未定義0と全機能・全条件の確認済みは別です。

## この版のファイル

同じフォルダーへ次の通常ZIPをすべて展開してください。4ファイルは分割圧縮形式ではなく、それぞれ独立したZIPです。同じPSLOG101/pslog-1.01配下へ内容が揃います。

- PSLOG101_remaining0_source.zip：最終ソース、設定、試験、原案合本、個別研究、今回のJARL様式参照原本。
- PSLOG101_remaining0_references_01.zip
- PSLOG101_remaining0_references_02.zip
- PSLOG101_remaining0_references_03.zip

原案合本の単体：PSLOG101_contest_research_remaining0.md。
現在の残件一覧の単体：PSLOG101_current_audit.md。
コード内の原案：docs/CONTEST_RESEARCH_ALL.md。
現状台帳：docs/CONTEST_IMPLEMENTATION_TRACKER.json。
詳細監査：docs/contest-research/PSLOG101_CURRENT_AUDIT.md・json。
JARL様式：docs/reference-vault/jarl-forms/2026-09-15/。公式PDFは未改変、取得日入り名称と.pdf.reference拡張子。PROVENANCE.jsonにURL・取得UTC時刻・SHA-256。開発参照用でWindowsアプリ配布対象外です。

## 継続と保全

作業名PSLOG101、アプリPSLog 1.01、PSLOG100以来の原案と取得原典を保持。過去の「未実装」は当時の記録として残し、現状は上記監査と最新確認を優先。2025年版の大会を勝手に2026年へ変更していません。

旧残り1版845ファイルを含め欠落なし、取得原典のバイト不変を照合。全ファイルのSHA-256はhandoff/MANIFEST.json、試験はhandoff/tests.log、旧版保全はhandoff/preservation.json。ZIPは一時領域で閉じてCRC検証後に完成品へ置き換え、保存後も全ファイルを照合します。

以前のPSLOG101_remaining28.zip、PSLOG101_final9_work_remaining2.zipは破損があり復帰元に使用しないでください。残り1版source.zipにも古い破損版があるため、過去版を使う場合は検証済みversion1に限ります。この残り0版を新しい再開入口とします。

再開時は現在の残件一覧を読み、提出対象の年度・形式確認とWindows実機試験を優先してください。全保留を完了に変更しないこと。自動送信はしません。
"""
    (ROOT/'docs/CHECKPOINT_PSLOG101_REMAINING0.md').write_text(report)
    (HANDOFF/'PSLOG101_remaining0_START_HERE.md').write_text(report)
    (HANDOFF/'PSLOG101_contest_research_remaining0.md').write_bytes((ROOT/'docs/CONTEST_RESEARCH_ALL.md').read_bytes())
    (HANDOFF/'PSLOG101_current_audit.md').write_bytes((ROOT/'docs/contest-research/PSLOG101_CURRENT_AUDIT.md').read_bytes())
    return report

def package(logpath):
    report=prepare(logpath);preserved=preserve();preserved.update(preserve_remaining1());files=sorted(p for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc');manifest={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    references=[p for p in files if p.relative_to(ROOT).as_posix().startswith(('docs/contest-research/sources/','tools/reference/'))];source=[p for p in files if p not in references]
    batches=[source];current=[];size=0
    for p in references:
        compressed=len(zlib.compress(p.read_bytes(),9))+len(str(p))*2+150
        if size+compressed>6*1024*1024 and current:batches.append(current);current=[];size=0
        current.append(p);size+=compressed
    if current:batches.append(current)
    outputs=[]
    for i,group in enumerate(batches):
        out=HANDOFF/('PSLOG101_remaining0_source.zip' if i==0 else f'PSLOG101_remaining0_references_{i:02}.zip')
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
    (HANDOFF/'PSLOG101_remaining0_package_checks.json').write_text(json.dumps(metadata,indent=2));print(json.dumps(metadata,ensure_ascii=False))
if __name__=='__main__':package(sys.argv[1])
