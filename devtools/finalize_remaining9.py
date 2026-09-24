"""Commit the verified 19-item milestone and produce a complete, bounded ZIP."""
from pathlib import Path
import sys,json,re,zipfile,hashlib
from checkpoint_remaining9_work import checkpoint,DONE,ROOT,HANDOFF,year
from checkpoint_regional import collect_research
from contest_rules import loads
DONE.update({
'all_asian_dx_cw':'2026 CW22種目。AS entity/非AS WPX・帯域別点・MM例外、最初24運用時間・MS系列別10分/新マルチ、UTC Cabrillo3と全帯出力。',
'all_asian_dx_phone':'2026 Phone22種目。CWと独立日程、実RS・年齢交換、SOJR/SOSV資格、CONTEST=AADX-SSB。',
'jarl_world_wide_rtty':'2026の5種目。大陸2/3点、JA/K/VE/VK本土コールエリアと島嶼entity、MM2点/マルチなし、年齢代替とYOUTH、JARL R1.0/R2.1 UTC。Cabrillo専用テンプレートは未対応。',
'ww-digi':'28種目。GL4中心間距離点/GL2マルチ・FT4/FT8共通重複・系列別毎時8変更。ZZ00は総得点未確定でCLAIMED-SCORE省略。Cabrillo3・全帯保持。',
'all_okayama_ft':'12種目L/H/V。レポートなしGL4、FT4/FT8共通重複、QRP5W、部門別出力。公式案内WSJT-XのWW-DIGI形式でCabrillo3 UTCを生成し専用フォームで部門選択。受付パーサーはサーバー側のため独立検証未了。',
'miyazaki':'29種目。利用者確定の県人国外1点/マルチなし、県内国外6大陸、市郡KJ統合、手動重複採用、新人と混合最低条件、JARL本文1MB。MKJの追加モード構成は原典未明示のため独自条件なし。'})

def finalize(logpath):
    log=Path(logpath).read_text();assert log.rstrip().endswith('OK');tested=int(re.search(r'Ran (\d+) tests',log).group(1));assert tested>=533
    checkpoint(logpath)
    p=ROOT/'docs/CONTEST_IMPLEMENTATION_TRACKER.json';tracker=json.loads(p.read_text());pending=[c for c in tracker['contests'] if c['runtime_definition']=='未作成・未検証'];assert len(DONE)==19 and len(pending)==9
    tracker['checkpoint']='PSLOG101_remaining9';p.write_text(json.dumps(tracker,ensure_ascii=False,indent=2)+'\n')
    categories=sum(len(loads((ROOT/f'config/rules/{k}_{year(k)}.txt').read_text())['event']['categories']) for k in DONE);assert categories==448
    report=f'''# PSLOG101 定義上残り9・保存版

2026-09-15。依頼「定義残り9まで」の到達版です。アプリはPSLog 1.01のままです。
**開始28 → 今回19項目追加 → 残り9 / 87管理項目（定義あり78）。** 今回448競技種目。
管理項目数を実装工程数、ファイル数、全製品の残作業数とは混同しません。
全体{tested}自動試験合格（Linux / Qt offscreen）。実行ルール作成済みは主催審査・全規約解釈の確認完了を意味しません。

## 再開入口

- 全ソース: pslog-1.01/。起動・Windowsビルドの案内は既存README.md、WINDOWS_BUILD.md。
- 現在の台帳: docs/CONTEST_IMPLEMENTATION_TRACKER.json。
- 原案の累積まとめ: docs/CONTEST_RESEARCH_ALL.md（別添MDも同内容）。
- 元の原案・利用者の確定事項: docs/contest-research/。末尾の利用者確定を優先。
- 取得した原典: docs/contest-research/sources/。出典・保存版・SHAはまとめに収録。
- 追加実装詳細と境界: docs/PSLOG101_REMAINING9_NOTES.md。
- 生成コード: devtools/build_remaining9.py / build_last6.py。
- 追加試験: test_remaining9.py / test_last6.py。
- 最新試験結果・全ソースSHA: このZIPのhandoff/tests.log / MANIFEST.json。

## 今回の19管理項目

'''+''.join('- '+k+': '+v+'\n' for k,v in DONE.items())+'''
## 残る9管理項目

'''+''.join('- '+str(c.get('no','追加'))+' '+c['name']+' (`'+c['id']+'`)\n' for c in pending)+'''
No.73新潟支部は同一性未確認のまま保持。QSOパーティを後回しにする方針も維持。
広島WASは調査原案を残し、今回の定義数には含めていません。

## 保全と復元

旧PSLOG100に相当する原案・取得原典を削除せず、PSLOG101へ累積継承しています。
原本TXTは11列、JST、UTF-8 BOM/CRLFを維持し、提出用追加情報だけ別管理。交換しなかったレポートを作りません。
原始版557ファイル、残り50版639ファイル、正常な残り28途中版709ファイルの全パス存在と取得原典バイト一致を照合しました。
破損した残り28最終ZIPから回収できた665個の完全なファイルも同様に照合しました。

PSLOG101_remaining28.zipは保存済みの再取得でもZIP終端欠損があり、復元元にしてはいけません。
正常な途中保存版と回収内容から復旧しました。大きいZIPでは再作成時にも欠損が再現したため、旧ZIPを入れ子にせず全ソースと資料を直接収める構成に変更しました。
残り25・残り15の保存版は再取得CRC/全体SHA一致を確認済みです。今回の最終版も保存後に同じ確認を行います。
旧の正常な原始ZIPは以前の保存物として保持され、このZIPにはその全ソース・原案が継承されています。

## 残る検証範囲

Windows実機・EXE作成・主催者受付は未検証。大会定義や提出形式の初期対応範囲、保存年、手動申告が必要な境界は原案と台帳を参照してください。
CQ WW CW/SSBは確認済み2025規約の保存版で、2026開催版として作っていません。その他今回追加は明示された2026版です。
岡山FTは公式のWSJT-X WW-DIGI形式に従うローカル生成試験済みですが、専用フォームのサーバー内パーサー受入は未検証です。
JARL RTTYはJARL電子形式を実装し、識別子未確認のCabrilloを推測生成しません。
'''
    (ROOT/'docs/CHECKPOINT_PSLOG101_REMAINING9.md').write_text(report)
    (ROOT/'docs/CHECKPOINT_PSLOG101_GOAL9_WORK.md').write_text('# 残り9目標の途中作業は完了しました\n\n現在はCHECKPOINT_PSLOG101_REMAINING9.mdを参照してください。途中版の記録は別途保存済みです。\n')
    intro=f'<!-- PSLOG101 REMAINING9 -->\n## PSLOG101 現在の保存版：定義上残り9\n\n28から19管理項目・448競技種目を追加。78/87項目に定義あり。全体{tested}試験合格。原案・原典・旧ソースを保全。詳細: docs/CHECKPOINT_PSLOG101_REMAINING9.md。以下は過去の履歴です。\n\n'
    for name in ['docs/history/development/CHANGES_1.01.md','docs/CONTEST_IMPLEMENTATION_STATUS.md','docs/history/development/STATUS_1.00.txt','docs/history/development/REMAINING_1.00.txt']:
        p=ROOT/name;s=p.read_text();
        if '<!-- PSLOG101 REMAINING9 -->' not in s:p.write_text(intro+s)
    p=ROOT/'README.md';s=p.read_text();marker='PSLOG101 再開入口：docs/CHECKPOINT_PSLOG101_REMAINING9.md。定義上残り9、原案合本はdocs/CONTEST_RESEARCH_ALL.md。\n\n'
    if marker not in s:p.write_text(marker+s)
    collect_research(tracker,list(DONE),9)
    files=[p for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'];manifest={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    out=HANDOFF/'PSLOG101_remaining9.zip'
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('PSLOG101/START_HERE.md',report)
        for p in files:z.write(p,'PSLOG101/pslog-1.01/'+str(p.relative_to(ROOT)))
        z.write(logpath,'PSLOG101/handoff/tests.log');z.writestr('PSLOG101/handoff/MANIFEST.json',json.dumps(manifest,indent=2));z.writestr('PSLOG101/handoff/PROGRESS.json',json.dumps(dict(total=87,defined=78,remaining=9,new_managed_items=19,new_categories=448,tests=tested,pending_ids=[c['id'] for c in pending]),ensure_ascii=False,indent=2))
    with zipfile.ZipFile(out) as z:assert z.testzip() is None
    summary=HANDOFF/'PSLOG101_contest_research_remaining9.md';summary.write_bytes((ROOT/'docs/CONTEST_RESEARCH_ALL.md').read_bytes());guide=HANDOFF/'PSLOG101_remaining9_START_HERE.md';guide.write_text(report)
    print(json.dumps(dict(remaining=9,defined=78,categories=categories,tests=tested,files=len(files),bytes=out.stat().st_size,sha256=hashlib.sha256(out.read_bytes()).hexdigest(),zip=str(out),summary=str(summary),guide=str(guide)),ensure_ascii=False))
if __name__=='__main__':finalize(sys.argv[1])
