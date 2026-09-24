"""Persist a reviewable checkpoint; refuses missing definitions or source loss."""
from pathlib import Path
import json,hashlib,zipfile,sys,csv,io
ROOT=Path(__file__).resolve().parents[1];HANDOFF=ROOT.parents[1]
sys.path.insert(0,str(ROOT))
from contest_rules import RuleStore
import rule_catalog

def checkpoint(ids,label,testlog):
    log=Path(testlog).read_text()
    if not log.rstrip().endswith('OK'):raise RuntimeError('Regression log is not successful')
    tracker_path=ROOT/'docs/CONTEST_IMPLEMENTATION_TRACKER.json';tracker=json.loads(tracker_path.read_text());targets_path=ROOT/'config/rules/TARGETS_73.json';targets=json.loads(targets_path.read_text())
    for ident in ids:
        p=ROOT/f'config/rules/{ident}_2026.txt'
        if not p.is_file():raise RuntimeError('Missing '+str(p))
        entry=next(c for c in tracker['contests'] if c['id']==ident)
        entry['runtime_definition']=str(p.relative_to(ROOT));entry['implementation_gate']='大会定義・全部門採点/出力の自動試験済み。原案の未記載事項、主催受付・Windows実機は別途確認。'
        t=next(c for c in targets['contests'] if c['id']==ident);t['rule_file']=p.name;t['status']='実装・自動試験済み（2026参考版、主催受付・Windows実機未検証）'
    gates={'oita':'全41部門・採点/出力試験済み。管外部門エリア判定基準・県人移動範囲は原典未明示で追加申告必須。主催受付・Windows実機未検証。','nagasaki':'全16部門・採点/出力試験済み。締切4月14日(月)の曜日不一致は未解消。主催受付・Windows実機未検証。','all_kushiro':'全16部門・採点/出力試験済み。混合構成・全帯以外の最低帯数・提出本文/添付は原典未明示。主催受付・Windows実機未検証。','ja9_vu':'全9部門・高得点優先と実交信OP数を試験済み。10GHz超の追加は規約確認待ち。主催受付・Windows実機未検証。','niigata_low_band':'同一大会3区分・全48部門を試験済み。予約IDを互換維持。No.73との同一性は未確認で別途保留。'}
    for c in tracker['contests']:
        if c['id'] in ids and c['id'] in gates:c['implementation_gate']=gates[c['id']]
    remaining=sum(c['runtime_definition']=='未作成・未検証' for c in tracker['contests'])
    tracker['checkpoint']=label
    tracker_path.write_text(json.dumps(tracker,ensure_ascii=False,indent=2)+'\n');targets_path.write_text(json.dumps(targets,ensure_ascii=False,indent=2)+'\n')
    rule_catalog.sync(RuleStore(ROOT))
    category_count=sum(len(__import__('contest_rules').loads((ROOT/f'config/rules/{ident}_2026.txt').read_text())['event']['categories']) for ident in ids)
    report=f'''# PSLOG101 {label}

未作成・未検証の管理項目: **{remaining} / 87**。異なる大会数や実装ステップ数ではありません。
今回の対象は71項目から50項目へ進める作業です。今回 {len(ids)} 管理項目・{category_count} 部門を実装・自動試験しました。
原案を一つに集めたファイルは pslog-1.01/docs/CONTEST_RESEARCH_ALL.md です。
定義作成済みと、全条件の主催確認・実機検証完了は別です。

## 今回の実装済み対象
'''+''.join('- '+x+'\n' for x in ids)+f'''
## 保持したもの

- PSLOG100からの原案・大会調査メモ・利用者確認・取得原典を保持。
- PSLog 1.01の11列TXT原本を変更せず、追加申告は提出作業データ。
- 元のOkayama時点ZIPも同梱し、すべての旧ファイルの存在を照合。
- 2026年版を2027へ自動更新しない。

## 検証と限界

{log[log.rfind('----------------------------------------------------------------------'):]}

JARL出力はローカル自動試験です。主催者への送信・受付試験、Windows実機とEXE作成は行っていません。
地方規約で未記載の最低帯数、混合構成、本文/添付の指定等は、原案の保留記録を保持し独自に補っていません。
全体チェックログの受付可否も大会別の原典に従います。

## 再開箇所

台帳: docs/CONTEST_IMPLEMENTATION_TRACKER.json
原案: docs/contest-research/（各末尾の利用者確定事項を優先）
再生成: devtools/build_regional_2026.py
追加試験: test_regional_2026.py
共通処理: contest_regional.py
'''
    (ROOT/'docs/CHECKPOINT_PSLOG101_REGIONAL.md').write_text(report)
    collect_research(tracker,ids,remaining)
    base=HANDOFF/'pslog101_batch10_all_okayama.zip'
    files=[p for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc']
    with zipfile.ZipFile(base) as z:
        original=[n for n in z.namelist() if not n.endswith('/')]
        # Baseline has a single project folder; preserve all historical paths.
        missing=[];changed_refs=[]
        for name in original:
            rel=name.split('pslog-1.01/',1)[-1];p=ROOT/rel
            if not p.exists():missing.append(rel)
            elif rel.startswith(('docs/contest-research/sources/','tools/reference/')) and p.read_bytes()!=z.read(name):changed_refs.append(rel)
        if missing or changed_refs:raise RuntimeError(str(dict(missing=missing,changed_references=changed_refs)))
    manifest={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    out=HANDOFF/(label+'.zip')
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        z.writestr('PSLOG101/START_HERE.md',report);z.write(base,'PSLOG101/baseline/'+base.name)
        for p in files:z.write(p,'PSLOG101/pslog-1.01/'+str(p.relative_to(ROOT)))
        z.writestr('PSLOG101/handoff/MANIFEST.json',json.dumps(manifest,ensure_ascii=False,indent=2));z.write(testlog,'PSLOG101/handoff/tests.log')
    with zipfile.ZipFile(out) as z:
        if z.testzip():raise RuntimeError('ZIP CRC failure')
    print(json.dumps(dict(path=str(out),bytes=out.stat().st_size,remaining=remaining,files=len(files),original_preserved=len(original)),ensure_ascii=False))


def collect_research(tracker,ids,remaining):
    research=ROOT/'docs/contest-research'
    parts=['# PSLOG101 コンテスト原案・調査・実装対応まとめ\n\nPSLOG100からの記録を含む原案の累積版です。\n\n現在の未作成・未検証管理項目は **'+str(remaining)+' / 87**。大会数ではなく管理項目数です。\n\n本文の「未実装」は各調査時点の記録を保持したものです。現在の実装状況は冒頭台帳を優先し、規約解釈は各メモ末尾の利用者確定事項を優先します。過去の判断根拠は削除しません。\n\n## 現在の管理台帳\n\n|No.|ID|大会|実行定義|確認が残る事項|\n|---|---|---|---|---|\n']
    for c in tracker['contests']:
        parts.append('|'+str(c.get('no','追加'))+'|'+c['id']+'|'+c['name']+'|'+c['runtime_definition']+'|'+c.get('implementation_gate','').replace('|','／')+'|\n')
    for name in ['SCOPE.md','CONFIRMATIONS_20260914.md']:
        parts.append('\n\n---\n\n## 保持した基本決定: '+name+'\n\n'+(research/name).read_text())
    for p in sorted(research.glob('*.md')):
        if p.name in ['SCOPE.md','CONFIRMATIONS_20260914.md']:continue
        parts.append('\n\n---\n\n## 原案ファイル: '+p.name+'\n\n'+p.read_text())
    parts.append('\n\n---\n\n## 取得原典の保管一覧\n\n原典ファイルはcontest-research/sources/に保管しています。以下はバイト数とSHA-256です。\n\n|ファイル|バイト数|SHA-256|\n|---|---:|---|\n')
    for p in sorted((research/'sources').rglob('*')):
        if p.is_file():parts.append('|'+str(p.relative_to(research/'sources'))+'|'+str(p.stat().st_size)+'|'+hashlib.sha256(p.read_bytes()).hexdigest()+'|\n')
    (ROOT/'docs/CONTEST_RESEARCH_ALL.md').write_text(''.join(parts))

if __name__=='__main__':
    from test_regional_2026 import IDS
    checkpoint(IDS,sys.argv[1],sys.argv[2])
