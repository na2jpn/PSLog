# PSLOG101 再開入口（定義残り1）

依頼「残り9を進める」に対し8管理項目・170種目を実装。86/87管理項目が定義済み、残りはNo.73「新潟県支部大会記念」の大会特定だけです。No.9の新潟コンテストへ同一扱いで関連付けてよいか、または別大会の原典が必要です。未確認のものを完了扱いにはしていません。

PSLOG100からの原案・原典を保持し、作業名はPSLOG101、アプリはPSLog 1.01。全体547試験合格（Qt offscreen）。Windows実機・EXEビルド・主催者受理は未検証。元の11列ログを変更せず大会作業データで処理します。

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
