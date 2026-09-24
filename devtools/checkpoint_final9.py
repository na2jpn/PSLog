"""Durable in-progress checkpoint; never claims the remaining-nine goal early."""
from pathlib import Path
import sys,json,zipfile,hashlib,re
ROOT=Path(__file__).resolve().parents[1];HANDOFF=ROOT.parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'devtools'))
from checkpoint_regional import collect_research
from contest_rules import RuleStore
import rule_catalog
DONE={'kcwa_cw':'2025参考規約・3部門。帯域別実連番、相手個人局確認、JARL提出。','all_hyogo':'54部門。国外と2701、2部門目CALLSIGN -2、帯域重複排他。','hiroshima_was':'25部門。帯域時間窓、実レポート、通信区分、2サマリーを1本文へ結合。','shizuoka':'54部門。地域略符号、QRP全対象交信判定、10GHz共通、対象外帯域0点。'}
DONE.update({'qso_party':'2026部門30、名前交換・20異局・数値点0・JARL電子ログ。','shimane':'14部門、通常モード別重複、HF資格別最終1000加算、AJD最速10局と完成時刻別保持。','iburi_hidaka':'8部門、日本語コード/名称、自局常置と/8統合・地点別点/共通マルチ、OG/MT別集計。'})
DONE['toyama_emergency']='11種目、自由交換/所在地別集計、支部様式PDF・赤枠・全帯資料・50局超チェック表。日本語フォントと画面操作を試験。'
def year(k):return 2025 if k=='kcwa_cw' else 2026

def checkpoint(logpath):
    log=Path(logpath).read_text()
    if not log.rstrip().endswith('OK'):raise RuntimeError('Successful whole-suite test log required')
    preserved={}
    for archive in ['pslog101_batch10_all_okayama.zip','PSLOG101_remaining28_working_checkpoint.zip','PSLOG101_remaining50.zip','PSLOG101_remaining9.zip']:
        with zipfile.ZipFile(HANDOFF/archive) as z:
            names=[n for n in z.namelist() if 'pslog-1.01/' in n and not n.endswith('/')]
            for name in names:
                rel=name.split('pslog-1.01/',1)[1];p=ROOT/rel
                if not p.is_file():raise RuntimeError('Missing baseline file '+rel)
                if rel.startswith(('docs/contest-research/sources/','tools/reference/')) and p.read_bytes()!=z.read(name):raise RuntimeError('Changed original reference '+rel)
            preserved[archive]=len(names)
    recovered=json.loads((HANDOFF/'remaining28_recovered_local_headers.json').read_text())
    for name,size,digest in recovered:
        if 'pslog-1.01/' not in name:continue
        rel=name.split('pslog-1.01/',1)[1];f=ROOT/rel
        if not f.is_file():raise RuntimeError('Missing recovered file '+rel)
        if rel.startswith(('docs/contest-research/sources/','tools/reference/')) and hashlib.sha256(f.read_bytes()).hexdigest()!=digest:raise RuntimeError('Changed recovered reference '+rel)
    p=ROOT/'docs/CONTEST_IMPLEMENTATION_TRACKER.json';tracker=json.loads(p.read_text())
    for c in tracker['contests']:
        if c['id'] in DONE:
            path=f'config/rules/{c["id"]}_{year(c["id"])}.txt';assert (ROOT/path).exists();c['runtime_definition']=path;c['runtime_definitions']=[path];c['implementation_gate']=DONE[c['id']]+' 主催受付・Windows実機未検証。'
    remain=sum(c['runtime_definition']=='未作成・未検証' for c in tracker['contests'])
    assert remain==9-len(DONE)
    tracker['checkpoint']='PSLOG101_final9_work_remaining'+str(remain);p.write_text(json.dumps(tracker,ensure_ascii=False,indent=2)+'\n')
    for name in ['TARGETS_73.json','ADDITIONAL_RESEARCH.json']:
        p=ROOT/'config/rules'/name;data=json.loads(p.read_text())
        for c in data['contests']:
            if c['id'] in DONE:c.update(rule_file=c['id']+'_'+str(year(c['id']))+'.txt',rule_files=[c['id']+'_'+str(year(c['id']))+'.txt'],status=str(year(c['id']))+'定義・自動試験済み（主催受付・Windows実機未検証）',implementation_gate=DONE[c['id']])
        p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    for c in tracker['contests']:
        if c['id'] not in DONE:continue
        p=ROOT/c['implementation_note'];text=p.read_text();marker='## PSLOG101 最後の9件・途中実装記録 '+c['id']
        if marker not in text:p.write_text(text.rstrip()+'\n\n'+marker+'\n\n'+DONE[c['id']]+' 全体'+re.search(r'Ran (\d+) tests',log).group(1)+'試験合格。原ログ11列・原案・原典不変。主催受付とWindows実機未検証。\n')
    rule_catalog.sync(RuleStore(ROOT));collect_research(tracker,list(DONE),remain)
    tested=re.search(r'Ran (\d+) tests',log).group(1)
    report=f"""# PSLOG101 最後の9件の途中保存（現在残り{remain}）

依頼は「定義最後の9件を進める」。まだ完了ではありません。開始9から{len(DONE)}管理項目を実装・試験し、現在{remain}、目標まであと{remain}管理項目です。

全体{tested}試験合格。元ログ11列は維持。レポート未交換は双方空欄のまま保持し、架空の599/SNRを作りません。
台帳: docs/CONTEST_IMPLEMENTATION_TRACKER.json。原案合本: docs/CONTEST_RESEARCH_ALL.md。原典: docs/contest-research/sources/。
今回コード: devtools/build_remaining9.py、test_remaining9.py、contest_remaining9.py、contest_international.py。

## 今回実装した管理項目

"""+''.join('- '+k+': '+v+'\n' for k,v in DONE.items())+"""
## 保全確認と再開の注意

前回PSLOG101_remaining28.zipはローカル・再取得の双方でZIP終端欠損を確認しました。665個の完全なローカルヘッダーを解析・照合し、正常な残り28途中保存版709ソース・残り50版639ソース・原始版557ソースとも存在と原典バイトを比較しています。
大きなZIPでは今回の再作成でも保存後に欠損が再現しました。原始ZIPの入れ子を外した19MB構成で保存し直し、残り25版は再取得したZIPのCRC・全体SHA一致まで確認済みです。以後も旧ZIPを入れ子にせず、全ソース・全原案・全取得原典をこのZIPに直接収めます。
欠損ZIPを復帰元にしないでください。旧原案や未実装と記された当時の調査履歴は削除せず保持します。

CQ VHFはFT4/FT8/MSK144/Q65が初期対応。他のデジタル型式は未検証。相手Roverは/R付き記録を要求します。
主催の受付、Windows実機、EXEビルドは未検証。これは最後の9件の途中版です。新潟県支部大会記念コンテストの同一性は未確定です。
"""
    (ROOT/'docs/CHECKPOINT_PSLOG101_GOAL9_WORK.md').write_text(report)
    out=HANDOFF/f'PSLOG101_final9_work_remaining{remain}.zip';files=[p for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc']
    manifest={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('PSLOG101/START_HERE.md',report)
        for p in files:z.write(p,'PSLOG101/pslog-1.01/'+str(p.relative_to(ROOT)))
        z.write(logpath,'PSLOG101/handoff/tests.log');z.writestr('PSLOG101/handoff/MANIFEST.json',json.dumps(manifest,indent=2))
    with zipfile.ZipFile(out) as z:assert z.testzip() is None
    summary=HANDOFF/f'PSLOG101_final9_research_remaining{remain}.md';summary.write_bytes((ROOT/'docs/CONTEST_RESEARCH_ALL.md').read_bytes())
    print(json.dumps(dict(remaining=remain,goal=0,files=len(files),preserved=preserved,zip=str(out),summary=str(summary)),ensure_ascii=False))

if __name__=='__main__':checkpoint(sys.argv[1])
