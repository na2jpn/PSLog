"""Preserve all historical sources; deliver small independently extractable ZIPs."""
from pathlib import Path
import sys,json,zipfile,hashlib,re,zlib
ROOT=Path(__file__).resolve().parents[1];HANDOFF=ROOT.parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'devtools')]
from checkpoint_final9 import DONE,year
from checkpoint_regional import collect_research
from contest_rules import RuleStore
import rule_catalog

def prepare(logpath):
    log=Path(logpath).read_text();assert log.rstrip().endswith('OK');tested=int(re.search(r'Ran (\d+) tests',log)[1])
    tracker=json.loads((ROOT/'docs/CONTEST_IMPLEMENTATION_TRACKER.json').read_text())
    for c in tracker['contests']:
        if c['id'] in DONE:
            path=f'config/rules/{c["id"]}_{year(c["id"])}.txt';assert (ROOT/path).is_file();c.update(runtime_definition=path,runtime_definitions=[path],year=year(c['id']),implementation_gate=DONE[c['id']]+' 主催受付・Windows実機未検証。')
        if c['id']=='niigata_branch':c['implementation_gate']='No.73の大会特定待ち。既存No.9新潟との同一性を確認するまで別名定義を作らない。'
    pending=[c['id'] for c in tracker['contests'] if c['runtime_definition']=='未作成・未検証'];assert pending==['niigata_branch'];assert len(tracker['contests'])==87
    tracker['checkpoint']='PSLOG101_remaining1';(ROOT/'docs/CONTEST_IMPLEMENTATION_TRACKER.json').write_text(json.dumps(tracker,ensure_ascii=False,indent=2)+'\n')
    for n in ['TARGETS_73.json','ADDITIONAL_RESEARCH.json']:
        p=ROOT/'config/rules'/n;data=json.loads(p.read_text())
        for c in data['contests']:
            if c['id'] in DONE:c.update(rule_file=c['id']+'_'+str(year(c['id']))+'.txt',rule_files=[c['id']+'_'+str(year(c['id']))+'.txt'],status=str(year(c['id']))+'定義・自動試験済み',implementation_gate=DONE[c['id']])
        p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    for c in tracker['contests']:
        if c['id'] not in DONE:continue
        p=ROOT/c['implementation_note'];s=p.read_text();marker='## PSLOG101 最後の9件・最終実装記録 '+c['id']
        if marker not in s:p.write_text(s.rstrip()+'\n\n'+marker+'\n\n'+DONE[c['id']]+' 詳細と操作条件はPSLOG101_FINAL9_IMPLEMENTATION.md。全体試験と保全結果はSTART_HEREを参照。原案の旧未実装記録は履歴として残す。\n')
    rule_catalog.sync(RuleStore(ROOT));collect_research(tracker,list(DONE),1)
    report=f'''# PSLOG101 再開入口（定義残り1）

依頼「残り9を進める」に対し8管理項目・170種目を実装。86/87管理項目が定義済み、残りはNo.73「新潟県支部大会記念」の大会特定だけです。No.9の新潟コンテストへ同一扱いで関連付けてよいか、または別大会の原典が必要です。未確認のものを完了扱いにはしていません。

PSLOG100からの原案・原典を保持し、作業名はPSLOG101、アプリはPSLog 1.01。全体{tested}試験合格（Qt offscreen）。Windows実機・EXEビルド・主催者受理は未検証。元の11列ログを変更せず大会作業データで処理します。

## 展開と保全

PSLOG101_remaining1_source.zipとPSLOG101_remaining1_references_01.zip以降の原典ZIPを同じフォルダーへ全て展開してください。分割圧縮形式ではなく、それぞれ通常ZIPです。同じPSLOG101/pslog-1.01へ重ならないファイルが入ります。ソースZIPに実行コード・設定・原案合本・個別調査・試験・PDF作例、原典ZIPに全取得原典と元の参照資料を収録します。欠けた原典ZIPがある状態で原案調査や再生成を始めないでください。

原案単体: PSLOG101_contest_research_remaining1.md
原案合本: pslog-1.01/docs/CONTEST_RESEARCH_ALL.md
最新8件の判断: pslog-1.01/docs/contest-research/PSLOG101_FINAL9_IMPLEMENTATION.md
台帳: pslog-1.01/docs/CONTEST_IMPLEMENTATION_TRACKER.json
実装: devtools/build_final9.py、contest_final9.py、contest_bundle.py、contest_toyama_pdf.py
試験: test_final9.py、test_final9_completion.py、handoff/tests.log
全ファイルSHA: handoff/MANIFEST.json

過去のPSLOG101_remaining28.zipは終端破損、今回のPSLOG101_final9_work_remaining2.zipも保存時のサイズ不一致/終端破損があり復帰元に使えません。残り9版と今回の小さいZIP群を使ってください。正常な原始557ファイル・残り50版639・残り28途中版709・残り9版802、破損28版から復元した665ファイルについて存在を照合し、原典バイト不変を確認します。今回も保存後に全ZIPのCRC・全ファイルSHAを再照合します。

## 重要な操作

島根AJDは数値0・完成時刻別表示、提出10局・得点欄HH:MM。HF移動資格時1000点は各HF部門の最後だけ。
胆振日高は専用対象選択で常置と/8を統合し、各QSOのfixed/portableと両住所を指定します。
広島WASの単帯2提出は各部門をセットへ追加し、セットを確認して1本文へ保存します。
富山は「所定様式PDF」。日本語/欧文の実交換と集計所在地を別入力し、赤枠・全帯参考資料・改ページをPDFで確認します。長い文字を切り捨てず、日本語フォント不在も停止します。docs/samplesのPDFは試験値です。
KCWAは原典が2025年版、勝手に2026へ更新しません。QSOパーティは取得した2026日本語規約に基づく電子提出、20異局・得点競争なしです。

## 再開時に残る一点

No.73（原一覧5月16日10〜19時）の正体を確認してください。既存No.9の2026新潟は5月17日と6月14日の3帯域区分を48種目で実装済みです。同一という確認が取れればNo.73をNo.9に関連付けます。別大会ならその規約を確認して実装します。順位判定・失格確定・送信をソフトが代行するものではありません。
'''
    (ROOT/'docs/CHECKPOINT_PSLOG101_FINAL9.md').write_text(report)
    (HANDOFF/'PSLOG101_remaining1_START_HERE.md').write_text(report)
    (HANDOFF/'PSLOG101_contest_research_remaining1.md').write_bytes((ROOT/'docs/CONTEST_RESEARCH_ALL.md').read_bytes())
    return report

def preserve():
    found={}
    for name in ['pslog101_batch10_all_okayama.zip','PSLOG101_remaining50.zip','PSLOG101_remaining28_working_checkpoint.zip','PSLOG101_remaining9.zip']:
        with zipfile.ZipFile(HANDOFF/name) as z:
            files=[n for n in z.namelist() if 'pslog-1.01/' in n and not n.endswith('/')];found[name]=len(files)
            for n in files:
                rel=n.split('pslog-1.01/',1)[1];p=ROOT/rel;assert p.is_file(),rel
                if rel.startswith(('docs/contest-research/sources/','tools/reference/')):assert p.read_bytes()==z.read(n),rel
    recovered=json.loads((HANDOFF/'remaining28_recovered_local_headers.json').read_text())
    for n,size,sha in recovered:
        if 'pslog-1.01/' not in n:continue
        rel=n.split('pslog-1.01/',1)[1];p=ROOT/rel;assert p.is_file(),rel
        if rel.startswith(('docs/contest-research/sources/','tools/reference/')):assert hashlib.sha256(p.read_bytes()).hexdigest()==sha,rel
    found['recovered_remaining28']=len(recovered);return found

def package(logpath):
    report=prepare(logpath);preserved=preserve();files=sorted(p for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc');manifest={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    references=[p for p in files if p.relative_to(ROOT).as_posix().startswith(('docs/contest-research/sources/','tools/reference/'))];source=[p for p in files if p not in references]
    batches=[source];current=[];size=0
    for p in references:
        compressed=len(zlib.compress(p.read_bytes(),9))+len(str(p))*2+150
        if size+compressed>6*1024*1024 and current:batches.append(current);current=[];size=0
        current.append(p);size+=compressed
    if current:batches.append(current)
    outputs=[]
    for i,group in enumerate(batches):
        out=HANDOFF/('PSLOG101_remaining1_source.zip' if i==0 else f'PSLOG101_remaining1_references_{i:02}.zip')
        with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
            for p in group:z.write(p,'PSLOG101/pslog-1.01/'+p.relative_to(ROOT).as_posix())
            if i==0:
                z.writestr('PSLOG101/START_HERE.md',report);z.writestr('PSLOG101/handoff/MANIFEST.json',json.dumps(manifest,indent=2));z.write(logpath,'PSLOG101/handoff/tests.log');z.writestr('PSLOG101/handoff/preservation.json',json.dumps(preserved,indent=2))
        with zipfile.ZipFile(out) as z:assert z.testzip() is None
        assert out.stat().st_size<7*1024*1024
        outputs.append(dict(path=str(out),bytes=out.stat().st_size,sha256=hashlib.sha256(out.read_bytes()).hexdigest(),source_files=len(group)))
    metadata=dict(files=len(files),defined=86,pending=['niigata_branch'],preserved=preserved,archives=outputs)
    (HANDOFF/'PSLOG101_remaining1_package_checks.json').write_text(json.dumps(metadata,indent=2));print(json.dumps(metadata,ensure_ascii=False))
if __name__=='__main__':
    if sys.argv[1]=='--prepare':prepare(sys.argv[2])
    else:package(sys.argv[1])
