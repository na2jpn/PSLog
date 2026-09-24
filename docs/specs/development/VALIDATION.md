# 検証範囲 — PSLog 1.14
## Ver1.14正本化時の確認

2026-09-25: 利用者がVer1.13正本へVer1.14差分を適用し、初回起動のアマチュア/フリラ切替を含む動作を「問題なし」と確認してVer1.14正本化を指示。正本化では受入済み差分を統合し、正本文書・履歴・manifestを更新する。受入済みVer1.14差分以外のランタイム機能変更は追加しない。

Ver1.14差分作成時のGPT/Linux確認: py_compile/構文確認OK、重点回帰29件OK、`unittest discover`は507件実行・FAIL 0件（69 ERRORはPySide6未導入Linux環境のGUI import/runtime error、9 skip）、Windows package関連テストOK。

Ver1.14正本化時のGPT/Linux再確認: `python -m compileall -q .` **OK**。初回起動、フリラ、全体復元、Windows package、Updater版数順序、Ver1.070 core、Ver1.06 releaseの重点回帰 **43 tests OK**。`python -m unittest discover -v` は **507 tests / 69 ERROR / 9 SKIP / 0 FAIL**。69 ERRORはこのLinux環境にPySide6がないためのGUI import/runtime error。Ver1.14差分の全変更ファイルは受入済み差分manifestのSHA-256と一致。source manifest hashとZIP CRCも正本生成時に確認する。


## Ver1.13正本化時の確認

2026-09-25: 利用者がVer1.12 FIX1までのフリラ初期実装状態を受け入れ、Ver1.13への正本化を指示。Ver1.13正本化ではVERSION、回帰テスト期待値、正本文書、履歴整理を更新し、受入済みVer1.12 FIX1以降の新規業務/UI機能は追加しない。

利用者Windows側では、Ver1.11 PATCH01適用後の全テストで2件のFAILが報告されたが、いずれも旧版数/旧表示を期待する陳腐化テストと切り分けてFIX1で更新。その後 `build-windows.ps1` がPyInstaller/packagingまで完走したことを確認した。配布ZIP名が1.10固定だった点はVer1.12 PATCH01 FIX2で `storage.VERSION` 参照へ修正。フリラ作成ダイアログの入力エラー時終了と機種名必須問題はVer1.12 FIX1で修正した。

Ver1.13正本化後のGPT/Linux確認結果:

- `python -m compileall -q .`: **OK**。
- フリラ、全体復元、Windowsパッケージ、Updater版数順序、Ver1.070 core、Ver1.06 release回帰: **38 tests OK**。
- Updater版数順序に `1.13 > 1.12`、`1.131 > 1.13`、`1.12 < 1.13` を追加し成功。
- `python -m unittest discover -v`: **502 tests / 422成功 / 69 ERROR / 9 SKIP / 0 FAIL**。69 ERRORはこのLinux環境にPySide6がないことによるGUI import/runtime error。
- フリラ核心回帰は **8 tests OK**（種類/BAND-MODE、カナ変換・漢字拒否、任意機種名、Unicode QSO、種類横断検索、年跨ぎ編集、全体バックアップ、4タブ制限）。

最終Ver1.13のWindows全テスト、GUI、PyInstallerビルドは利用者側Windowsで確認する。特に `WINDOWS_CHECKLIST.txt` のフリラ項目を重点確認する。


## Ver1.10正本化時の確認

2026-09-24: 利用者がVer1.078 PATCH08適用状態を確認し、Ver1.10への正本化を指示。正本化ではVERSION/Windows配布名/引継ぎ文書を1.10へ整理し、1.078受入後の新規機能ロジックは追加しない。

正本化後のLinux確認結果:

- `python -m compileall -q .`: **OK**。
- Ver1.071〜1.078、全体復元、Windowsパッケージ、Ver1.06リリース回帰、87ルール表示監査を含む重点回帰: **84 tests / 75成功 / 9 GUI SKIP / 0 FAIL / 0 ERROR**。
- `python -m unittest -v test_update_package`: **5 tests OK**。`1.10 > 1.078`、`1.101 > 1.10`、`1.078 < 1.10` を含むUpdaterの前方更新判定を確認。
- `python -m unittest discover -v`: **494 tests / 69 ERROR / 9 SKIP / 0 FAIL**。69 ERRORはこのLinux環境にPySide6がないためのGUI import/runtime error。

PySide6依存のWindows GUI/EXE最終確認は利用者側Windowsを優先する。利用者はVer1.078適用状態をOKと確認したうえでVer1.10正本化を指示している。

## 以前の検証履歴

## Ver1.07正本化時の確認

2026-09-24: Ver1.069コンテストルール整備完了ソースへVer1.070 PATCH10 + FIX2を統合した状態について、利用者Windows環境でビルド・起動成功を確認。

正本化では、その受入済み機能状態を維持したままVERSION/Windows配布名を1.07へ確定し、PATCH/FIX/Work文書をhistoryへ整理した。

正本化後のLinux確認結果:

- `python -m compileall -q .`: **OK**。
- 主要非GUI回帰: **49 tests OK**。対象は `test_patch01_1061`, `test_patch10_1070_core`, `test_full_restore`, `test_windows_package`, `test_release_106`, 87ルール表示監査3モジュール。
- `python -m unittest discover -v`: **444 tests / 375成功 / 69 ERROR**。69件はこの環境にPySide6がないためのGUI import/runtime errorで、FAIL assertionは0。
- 87ルールの読込・表示は監査テストで成功。

PySide6依存のWindows GUI実機確認は利用者側Windows結果を優先する。

特にVer1.07で確認対象となる追加点:

- コンテスト管理一覧の開催年月ラベル。
- 標準の提出ログ・バンド順チェックと、愛・地球博の初期ON。
- バンド順ON/OFF双方の出力順。
- `official` / `user_modified` / `user_defined` の同梱ルール出自判定。

## Ver1.06以前の検証履歴

## Ver1.06正本化時の確認

2026-09-21: Ver1.05系1.051〜1.059を統合し、Ver1.06最終調整後に `compileall` とLinuxで実行可能な非GUI回帰を再実行する。Windows/PySide6 GUI、全unittest、`build-windows.ps1`、EXE実機確認は利用者側Windowsの担当とする。

最新結果はdocs/CHECKPOINT_PSLOG101_FINAL_PRE_WINDOWS.mdを参照してください。
以下は1.00時点から継承した検証履歴と限界です。

2026-09-12 / Python 3.12.14 / PySide6 6.8.3 / Linux Qt offscreen。
保存場所の案内修正後に自動テスト223件を再実行し、すべて成功しました。

## 確認した経路

原本保存・外部変更・バックアップ復元・年移動・一括処理回復、
入力補助・検索編集・各入出力マッピング、QSL、POTA/SOTA、
コンテスト採点・各形式の画面操作を含みます。

合成1万交信: 読込、採点、末尾ページ、zLog全件出力、34列、
原本不変、保存前外部変更停止を確認。CONTEST_VOLUME.md参照。
各コンテスト形式の画面操作範囲はCONTEST_WORKFLOW_CHECK.md参照。

## 未検証・限界

Windows EXEビルド、Windows10/11での起動・名前付きmutex・
DPI/複数モニター・長いパス・アクセス拒否の実機確認は未実施。
HAMLOG/zLog実機への取り込み、各主催者への受入確認は未実施。
全件をメモリー保持するため無制限件数の保証ではありません。
一般の外部エディタとの最終確認と置換の間の競合、物理電源断、媒体故障を完全保証しません。

過去のユーザー提供TXTの行別調査はdocs/history/20260912_before_cleanup_VALIDATION.mdに保存。
その記録を今回再実施した結果とは扱いません。

保存先の追加検証はSAVE_LOCATION.mdを参照。Windows実機確認は未実施です。

主要10画面の小画面操作到達性を確認。UI_REVIEW.md参照。

2026-09-12: 日本郵便照合による参照候補1890件を追加。確認済みは3件のまま。未整形/不一致9件。POSTAL_LOCATIONS.md参照。

2026-09-12追加: ローマ字候補1890件、9件は個別資料確認が残る。全223テスト成功。
Windowsビルド後の配布ZIP作成処理と確認票を追加。実EXE未作成。WINDOWS_BUILD.md参照。