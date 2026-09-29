# 検証範囲 — PSLog 1.15

## GPT/Linux側

- `PSLog_1.14_CANONICAL_SOURCE.zip` を新規展開し、Ver1.15を直接実装。古いPATCH/FIXから再構成していない。
- Python `compileall`：OK。
- Ver1.15重点回帰（Updater/versionup、Windows package、フリラ、全体復元、初回起動、主要リリース回帰）：**58 tests OK**。
- Ver1.15更新系重点回帰（Updater/versionup、Windows package、更新履歴、QSL作業画面）：**30 tests OK**。
- `python -m unittest discover -v`：**515 tests run / 0 FAIL / 69 ERROR / 9 skipped**。
- 上記69 ERRORは、このLinux検証環境にPySide6が入っていないためのGUI import/runtime error。FAIL assertionは0件。
- `SOURCE_MANIFEST.json` は生成物除去後の全ソースツリーSHA-256を記録する。
- 全装ZIP作成後にZIP CRC、全装内 `SOURCE_MANIFEST.json`、source tree hashを再確認する。

## Windows側で必要

- `python -m unittest discover -v`
- QSL処理画面のGUI確認
  - QSLタグ・JCC/JCG・HIS QTHが「保存」まで元ログへ書かれないこと
  - `HIS QTHへ反映` の動作
  - `保存` で一括保存後に閉じること
  - 未保存変更ありで `閉じる` → **「変更内容を保存せず閉じますか？」** が出ること
  - 未変更なら確認なしで閉じること
- Ver1.14 → Ver1.15の実Windows ZIPアップデート確認
  - 指定ZIPは1個だけ
  - `meta/versionup.json` とVer1.14移行互換manifestを確認
  - `config/`、`logbook/`、`logbook_flr/`、`bak/`、`output/` が保護されること
- `build-windows.ps1`
- 生成Windows ZIPの起動・自己診断・更新後自動再起動
- ヘルプ → `PSLogの更新履歴` と `PSLogについて` のVersion表示確認

問題がなければ、**同一 `PSLog_1.15_FULL_SOURCE.zip` を再構成・再パックせずVer1.15正本として扱う。**
