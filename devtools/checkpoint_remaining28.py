"""Finalize the 50 -> 28 checkpoint only after tests and source preservation."""
from pathlib import Path
import sys,json,hashlib,zipfile,re
ROOT=Path(__file__).resolve().parents[1];HANDOFF=ROOT.parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'devtools'))
from test_remaining28 import RULES,TRACKED,rule
from checkpoint_regional import collect_research
from contest_rules import RuleStore
import rule_catalog

GATES={
'ishikari':'01006は郡番号だけでは所属を断定せず、該当局・町村・後志所属の確認を追加申告。関連の過年度画像等は読了扱いにしない。',
'yamagata_sakuranbo':'通常全帯はHF2＋VU1。YCの同条件適用は原典未明示で独自強制しない。学年・YL・登録クラブは本人申告。',
'yamanashi':'県内外とも山梨1局以上。新人社団局の資格は原典未明示で参加根拠を申告。',
'all_ja8':'受信年代別得点・地域のみマルチ。R2.1のみ対応。MOのM/X等は実交換と原典を本人確認、年齢公開を推定しない。',
'okhotsk':'2026第50回最終回を保存。2027へ継承しない。未記載の最低帯数・混合構成を加えない。',
'all_miyagi':'通常単帯1＋1200UP1のみ例外併願。高帯域は実バンド別、終了12:59を含む。',
'kansai_vus':'全交信を出力し種目で採点。CWのみは電信へ案内。10.1/10.4GHz共通、24GHz等は別。',
'kcj':'JARL JST出力まで対応。Cabrillo・主催照合結果取込は未対応。未照合は暫定、DUP・?を残す。主催の時刻差10分境界は未確認。',
'kcj-topband':'2月固有の部門・宛先・日程。JARL JST対応、Cabrilloは未対応。主催の時刻差10分境界・当時版提出要領は未確認。',
'all_ja0_160m':'2025参考版の実装。2026規約待ち。管内OR条件・文字組マルチ・JARL専用列順、実連番維持。主催解析器への試験送信は未実施。',
'all_ja0_80m_40m':'台帳1項目に対し3.5/7の別大会2ファイル。専用列順・別提出、相手ログ照合後の減点は未反映。',
'scalg-6m-cw':'6競技区分＋チェック8。無効取得年でも交信点維持。初取得年・電鍵・必要写真・固定移動の事実は本人申告、認定/写真審査は主催。',
'all_mie_33':'年齢/ME/MEJを分離し53種目。県人/JLとOP年齢の事実は申告、国外も対象。実交換年齢を生年月日で書換えない。',
'oidemase_yamaguchi_hf':'No68/71は同じ実行定義を共有しOM/MOを一度だけ定義。両週の実バンド別窓・通常部門の交信再使用禁止・OM/MO排他。',
'oidemase_yamaguchi_vushf':'No68/71共有定義のVU/SHF日程。OM年齢は5月31日基準。申告県と実運用場所の同一性は本人確認。',
'all_gifu':'原PDF保存・画像照合は未了、保存済み全文抽出を使用。ハーフは運用全体片側。ジュニア担当割合は全交信と行別担当を照合、重複/無得点分母の細部は確認根拠を保持。',
'tokai_qso':'担当割合と全QSO担当を照合。D-STAR直接通信・SPA4アマ・実出力/資格は本人確認。R1.0をWeb提出用に作成。',
 'tsugaru_kaikyo':'3区域点と移動範囲を区別。任意採用は他候補を作業上のチェック行へ、元ログは消さない。',
'all_akita':'通常全帯HF＋VU、QRP/Jrは免除。併願禁止3条件、判定集合が未明示の境界は両実集合と確認根拠を入力。',
'shiga':'管外同士も得点、滋賀交信バンド係数0を許容。3バンド選択/実績とスプリント窓。係数はFDCOEFFに出さない。',
'all_gunma':'104種目、実績による部門候補を表示して本人が変更。自動採用は先頭、無断CW優先なし。学年・運用制限は本人確認。',
'kanagawa_emergency':'7桁郵便番号と県外市郡区を区別。未収録郵便番号は確認根拠入力で保持。AとHL/V/Uの実バンド条件、対象外も0点出力。',
}

def finalize(testlog):
    log=Path(testlog).read_text()
    if not log.rstrip().endswith('OK'):raise RuntimeError('Successful final test log required')
    if len(TRACKED)!=22 or set(GATES)!=set(TRACKED):raise RuntimeError('22 tracked items required')
    # Check both immutable baselines before changing progress records.
    original=HANDOFF/'pslog101_batch10_all_okayama.zip';previous=HANDOFF/'PSLOG101_remaining50.zip';preserved={}
    for archive in (original,previous):
        with zipfile.ZipFile(archive) as z:
            names=[n for n in z.namelist() if 'pslog-1.01/' in n and not n.endswith('/')];missing=[];changed=[]
            for n in names:
                rel=n.split('pslog-1.01/',1)[1];p=ROOT/rel
                if not p.is_file():missing.append(rel)
                elif rel.startswith(('docs/contest-research/sources/','tools/reference/')) and p.read_bytes()!=z.read(n):changed.append(rel)
            if missing or changed:raise RuntimeError(str(dict(archive=archive.name,missing=missing,changed_references=changed)))
            preserved[archive.name]=len(names)
    tracker_path=ROOT/'docs/CONTEST_IMPLEMENTATION_TRACKER.json';tracker=json.loads(tracker_path.read_text());remaining_before=sum(c['runtime_definition']=='未作成・未検証' for c in tracker['contests'])
    if remaining_before not in (50,28):raise RuntimeError('Unexpected starting count')
    indexes={c['id']:c for c in tracker['contests']}
    for ident,paths in TRACKED.items():
        for name in paths:
            if not (ROOT/name).is_file():raise RuntimeError('Missing '+name)
        c=indexes[ident];c['runtime_definition']=paths[0]+('：3.5MHzと7MHzの別大会。両ファイルはruntime_definitions参照' if len(paths)>1 else '')
        c['runtime_definitions']=paths;c['implementation_gate']='採点・全種目JARL出力の自動試験済み。'+GATES[ident]+' 主催受付・Windows実機未検証。'
    remaining=sum(c['runtime_definition']=='未作成・未検証' for c in tracker['contests'])
    if remaining!=28 or len(tracker['contests'])!=87:raise RuntimeError('Must finish at 28 / 87')
    tracker['checkpoint']='PSLOG101_remaining28';tracker_path.write_text(json.dumps(tracker,ensure_ascii=False,indent=2)+'\n')
    for filename in ('TARGETS_73.json','ADDITIONAL_RESEARCH.json'):
        path=ROOT/'config/rules'/filename;obj=json.loads(path.read_text())
        for c in obj['contests']:
            if c['id'] in TRACKED:
                c['rule_file']=Path(TRACKED[c['id']][0]).name;c['rule_files']=[Path(n).name for n in TRACKED[c['id']]];c['status']='定義・自動試験済み（'+str(c['year'])+'保存版、主催受付・Windows実機未検証）';c['implementation_gate']=GATES[c['id']]
        path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
    count=sum(RULES.values());tested=re.search(r'Ran (\d+) tests',log).group(1)
    report=f'''# PSLOG101 残り28 保存版

定義上の残り **28 / 87管理項目**。前回50から22項目を実装・試験しました。
管理項目数は大会の実数や作業ステップ数ではありません。今回の実行定義22ファイル・競技種目{count}コードを検証しました。
ALL JA0 3.5/7は台帳1項目に対し別大会2ファイル。山口No68/71は台帳2項目で共有定義1ファイル、OM/MOは重複生成していません。
アプリ名PSLog・版1.01は維持し、旧作業PSLOG100からの続きPSLOG101として保存しています。

## すぐ開くファイル

- ソース: pslog-1.01/
- 原案・規約調査・利用者決定の合本: pslog-1.01/docs/CONTEST_RESEARCH_ALL.md
- 原案の個別ファイルと取得原典: pslog-1.01/docs/contest-research/
- 現在の台帳: pslog-1.01/docs/CONTEST_IMPLEMENTATION_TRACKER.json
- 再生成: devtools/build_remaining28.py
- 追加試験: test_remaining28.py（全種目採点・JARL出力を含む）
- 今回の共通処理: contest_regional_extended.py と contest_regional.py

## 変更内容

地域・年代・年齢/ME/MEJ・郵便番号・連番を元の交換記録から分離して採点します。
県内相手の必要数、帯域群の最低数、選択3バンド、複数提出、半日参加の運用全体、QSO担当割合を検査します。
滋賀の追加係数0、SCALGの点あり/マルチなし、KCJの未照合/DUP/未取得番号保持、JA0の専用列順に対応しました。
群馬は実績による部門候補を示して選び直します。送信番号・元ログ・申告コードを無断で変更しません。
原PSLog TXTの11列は増減せず、原案・原典・旧資料を削除していません。

## 検証

全体{tested}件の自動試験に合格。今回の{count}競技種目を採点し、各対応JARL版の出力を検査しました。
元ログのバイト不変、定義パックの新規導入/再導入、GUIの申告/担当欄、日付・電力・年代・交信範囲の境界を含みます。
保存時に旧Okayama版{preserved[original.name]}ファイルと直前残り50版{preserved[previous.name]}ファイルの存在を照合し、原典/参照資料のバイト不変を確認しました。
ZIPのCRCと全ソースのSHA-256一覧を同梱しました。

## 未解決事項の扱い

これは定義作成・ローカル自動試験の完了です。主催者の受理、確定得点、Windows実機やEXEビルドの完了を意味しません。
2025 ALL JA0 1.8MHzは2025参考版のまま、2026規約待ちです。KCJはJARL出力対応、Cabrillo/主催照合取込は未対応です。
岐阜の原PDF保存・画像照合、秋田の判定集合の細部などは台帳と原案に残し、確認済みに書き換えていません。
電鍵写真、実運用場所、学年・資格・免許などログから証明できない事実は追加申告と原記録で確認します。
主催者への送信・Web提出は行っていません。

## 今回の22管理項目

'''+''.join('- '+k+': '+GATES[k]+'\n' for k in TRACKED)+'''
## 次回の再開

台帳のruntime_definitionが「未作成・未検証」の28項目が次の対象です。
No73新潟支部はNo9と同一と断定せず、QSOパーティも合意どおり保留しています。
この保存版を起点にし、古いメモの「未実装」は当時の履歴として残してください。
'''
    (ROOT/'docs/CHECKPOINT_PSLOG101_REMAINING28.md').write_text(report)
    # Append current implementation evidence without rewriting historical decisions.
    grouped={}
    for ident in TRACKED:grouped.setdefault(indexes[ident]['implementation_note'],[]).append(ident)
    for note,idents in grouped.items():
        path=ROOT/note;text=path.read_text();marker='## PSLOG101 残り28版の実装記録'
        addition=marker+'\n\n2026年9月のPSLOG101継続作業で実行定義と採点・全種目JARL出力を自動試験。元の調査本文・利用者決定は保持しています。\n\n'+''.join('- '+i+': '+', '.join(TRACKED[i])+'。'+GATES[i]+'\n' for i in idents)+'\n原PSログ11列は不変。主催受付・Windows実機は未検証。今回の定義は保存年度専用で次年度へ自動更新しません。\n'
        if marker in text:text=text.split(marker)[0].rstrip()+'\n'
        path.write_text(text.rstrip()+'\n\n'+addition)
    for name in ('docs/CONTEST_IMPLEMENTATION_STATUS.md','docs/history/development/CHANGES_1.01.md'):
        path=ROOT/name;text=path.read_text();marker='<!-- PSLOG101 REMAINING28 -->'
        if marker not in text:path.write_text(marker+f'\n## PSLOG101 現在の保存版：定義上残り28\n\n前回50から22管理項目を実装・試験。今回{count}競技種目、全体{tested}件試験合格。原案・原典を保持。詳細はdocs/CHECKPOINT_PSLOG101_REMAINING28.md。以下は過去の作業履歴です。\n\n'+text)
    rule_catalog.sync(RuleStore(ROOT));collect_research(tracker,list(TRACKED),28)
    summary=HANDOFF/'PSLOG101_contest_research_remaining28.md';summary.write_bytes((ROOT/'docs/CONTEST_RESEARCH_ALL.md').read_bytes())
    files=[p for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'];manifest={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files};out=HANDOFF/'PSLOG101_remaining28.zip'
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        z.writestr('PSLOG101/START_HERE.md',report);z.write(original,'PSLOG101/baseline/'+original.name)
        for p in files:z.write(p,'PSLOG101/pslog-1.01/'+str(p.relative_to(ROOT)))
        z.writestr('PSLOG101/handoff/MANIFEST.json',json.dumps(manifest,ensure_ascii=False,indent=2));z.write(testlog,'PSLOG101/handoff/tests.log')
    with zipfile.ZipFile(out) as z:
        if z.testzip():raise RuntimeError('ZIP CRC failure')
    print(json.dumps(dict(path=str(out),summary=str(summary),remaining=remaining,tracked_completed=59,files=len(files),categories=count,tests=int(tested),preserved=preserved,bytes=out.stat().st_size),ensure_ascii=False))

if __name__=='__main__':finalize(sys.argv[1])
