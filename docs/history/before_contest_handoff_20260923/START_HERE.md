# START HERE — PSLog 1.06 CANONICAL SOURCE

## このツリーについて

これは **PSLog Ver1.06 の確定正本ソース**です。
Ver1.05正本から始めた1.051〜1.059の開発内容と、Ver1.06移行時の最終調整を統合しています。

正本ファイル名:

`PSLog_1.06_CANONICAL_SOURCE.zip`

**次のチャットはこの正本ZIPだけから開始してください。**
Ver1.05正本やVer1.05系PATCH/FIX ZIPを順番に再適用して再構成しないでください。

## 新しいチャットで最初に読むもの

1. `START_HERE.md`
2. `HANDOFF.md`
3. `docs/specs/development/PSLOG_1.06_BASELINE.md`
4. `docs/specs/development/PSLOG_1.06_NEXT_CHAT_PLAN.md`
5. `docs/IMPLEMENTATION_STATUS.md`
6. `docs/INDEX.md`

`docs/history/` は履歴確認専用です。

## Ver1.06正本で特に重要な状態

- アマチュア標準タブは `[A]JH1HST` 形式。付与文字は `[A]JH1HST-JP1220`。
- RMKS2はPSLog TXTの11項目を増やさず `RMKS1 <<RMKS2>> RMKS2` で保存。
- LogSearchは記録直後編集、削除、各機能へのチェック済みQSO引継ぎ、現在ログ全件表示に対応。
- コンテストはルール表示、参加部門汎用選択、バンド別QSO色分け、検索表の相手コール列等を実装。
- 通常エクスポートは「対象条件 → 項目対応 → 確認・出力」の3段階。
- 起動時既定サイズは1360×850。`--reset-window` で位置・サイズ・最大化状態を初期化可能。
- コンテスト提出最終画面の `入力内容を確認` / `ファイルを保存` は下部固定フッターへ配置。
- 運用地(OPPLACE)は、移動運用時は共通処理で必須。大会全体で常時必須なのは、現行登録ではオール千葉・オール兵庫・KCJ・KCJトップバンドのみ。
- フリラ本体対応はVer1.06開発チャットから開始する。Ver1.06正本時点では未実装。

## PSLogの基本原則

- Windows desktop: Python + PySide6 + PyInstaller。
- マスターログは **PSLog TXT 11固定項目**。
- 新規TXTは UTF-8 BOM + CRLF。
- ログ日時はJST。
- 未知のMODEを不必要に拒否しない。
- Windowsでは二重起動禁止。
- 新Verは旧Verバックアップを可能な限り復元できる後方互換を維持する。逆方向は保証しない。
- 元ログを更新しない処理は、黙って原本を書き換えない。
- サンプル用コールサインは `JX1XXX`。

## 主な入口

- `main.py` — アプリ入口、標準/コンテストタブ。
- `storage.py` — PSLog TXT、設定、VERSION、バックアップ。
- `session_state.py` — タブ/最近閉じたタブ。
- `search_ui.py`, `search.py` — ログ検索・編集。
- `remarks_sections.py` — RMKS1/RMKS2解析。
- `export_ui.py` — 通常エクスポート3段階UI。
- `contest_ui.py`, `contest_submit_ui.py` — コンテスト提出ワークフロー。
- `rule_view_ui.py`, `rule_view_data.py` — コンテスト/QSOパーティ/アワードのルール・条件表示。
- `build-windows.ps1`, `tools/run_tests.py`, `tools/package_windows.py` — Windowsテスト/ビルド。

## 次チャットを始めるとき

1. `PSLog_1.06_CANONICAL_SOURCE.zip` を展開する。
2. `START_HERE.md` と `HANDOFF.md` を読む。
3. `docs/specs/development/PSLOG_1.06_NEXT_CHAT_PLAN.md` を読む。
4. 変更前に `python -m unittest discover -v` を実行する。
5. 以後は変更ファイルだけの差分ZIPを基本とする。
6. **Ver1.05系PATCH/FIXを再適用しない。**
7. パッチは情報集積から始め、ユーザーが `1実装`, `2実装` 等と言うまで実装しない。
