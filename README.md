# PSLog Ver1.15 Full Source / Canonical Candidate

このツリーは `PSLog_1.14_CANONICAL_SOURCE.zip` から直接作成したVer1.15全装です。Windows側の全テスト・GUI確認・PyInstallerビルド確認で問題がなければ、**この同一ZIPをそのままVer1.15正本として扱います**。PATCH/FIXの再適用や正本化のための再構成は不要です。

## Read first

1. `START_HERE.md`
2. `HANDOFF.md`
3. `NEXT_CHAT_PROMPT.md`
4. `docs/specs/development/PSLOG_1.15_BASELINE.md`
5. `docs/specs/data/FREE_RADIO_LOGGING.md`
6. `meta/UPDATE_HISTORY.txt`

## Ver1.15 highlights

- 更新時に指定するZIPは従来どおり1つだけ。`meta/versionup.json` を追加し、将来の追加DLLフォルダー、補助EXE、追加アプリフォルダーを1つのZIPで更新できる土台を実装。
- 配布ルート直下はEXEとフォルダーのみ。`config/`, `logbook/`, `logbook_flr/`, `bak/`, `output/` はUpdater保護対象。
- `ヘルプ → PSLogの更新履歴` を追加。履歴は `meta/UPDATE_HISTORY.txt` で管理。
- 現行Version表示は `storage.VERSION` を共通参照。
- ログ検索・編集のQSL処理画面でJCC/JCGとHIS QTHを素早く補正可能。QSLタグも含めて下書きし、`保存` で一括反映。変更後に `閉じる` を選ぶと「変更内容を保存せず閉じますか？」と確認。

## Invariants

- PSLog TXTは11固定項目、JST、UTF-8 BOM + CRLFを維持。
- アマチュア原本は `logbook/`、フリラ原本は `logbook_flr/` で分離。
- コンテストルール表示を理由に採点・提出拒否条件を勝手に増やさない。
- 登録87ルール = コンテスト86件 + QSOパーティ1件。
