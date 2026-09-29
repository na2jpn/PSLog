# PSLog Ver1.15 — Full Source / Canonical Candidate

全装ZIP: `PSLog_1.15_FULL_SOURCE.zip`  
作成日: 2026-09-29 / VERSION: **1.15**

このZIPはVer1.14正本から直接作成したVer1.15全装（正本候補）です。Windows全テスト・GUI・ビルド確認で問題がなければ、この同一ZIPをそのままVer1.15正本として扱います。再構成・再パックは不要です。

## 読む順序

1. `START_HERE.md`
2. `HANDOFF.md`
3. `NEXT_CHAT_PROMPT.md`
4. `docs/specs/development/PSLOG_1.15_BASELINE.md`
5. `docs/specs/data/FREE_RADIO_LOGGING.md`
6. 必要に応じて `docs/INDEX.md`

## Ver1.15までに統合された主な内容

- Ver1.14までのアマチュア無線、EASY、コンテスト、QSL/JCC-JCG、フリラ、初回起動切替を維持。
- バージョンアップは従来どおり利用者が**1つのWindows ZIP**を指定する。
- `meta/versionup.json` をVer1.15+の更新管理情報として追加。将来DLL用フォルダー、補助EXE、追加アプリフォルダー等が増えても、同じ1つのZIPから更新できる土台を用意。
- 配布ルート直下はEXEとフォルダーのみ。JSON/TXT等の管理情報は `meta/` 配下に置く。
- `config/`、`logbook/`、`logbook_flr/`、`bak/`、`output/` はUpdaterの保護対象で、versionup情報からも更新・削除できない。
- Ver1.15 Windows ZIPはVer1.14から更新できるよう旧 `meta/PSLOG_UPDATE_INFO.json` も併載し、Ver1.15+は `meta/versionup.json` を優先する。
- ヘルプに「PSLogの更新履歴」を追加し、「PSLogについて」の上へ配置。履歴本体は `meta/UPDATE_HISTORY.txt`。
- 画面に出す現行Versionは `storage.VERSION` を共通参照し、操作案内タイトルも直書きを廃止。
- ログ検索・編集のQSL処理画面へJCC/JCG、HIS QTH、`HIS QTHへ反映` を追加。
- QSL処理画面内のQSLタグ/JCC-JCG/HIS QTH変更は下書きで、`保存` でまとめて原本反映後に閉じる。`閉じる` は保存しない。

以後の変更は差分ZIPを基本とします。要望列挙中は実装せず、利用者から明確な「実装」指示を受けてからまとめて変更してください。
