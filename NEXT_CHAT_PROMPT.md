PSLogの継続開発です。添付の `PSLog_1.15_FULL_SOURCE.zip` をWindows受入済みの場合は現在の唯一の基準ソースとして使ってください。

最初に `START_HERE.md`、`HANDOFF.md`、`NEXT_CHAT_PROMPT.md`、`docs/specs/development/PSLOG_1.15_BASELINE.md`、`docs/specs/data/FREE_RADIO_LOGGING.md` を読んでください。Ver1.14正本やそれ以前のPATCH/FIXから再構成せず、このZIPから開始してください。VERSIONは1.15です。

Ver1.15では、将来の複数アプリファイル更新に備え `meta/versionup.json` を追加しました。利用者が指定する更新ZIPは従来どおり1つだけです。配布ルート直下はEXEとフォルダーのみ、`config/logbook/logbook_flr/bak/output` はUpdater保護対象です。Ver1.15配布ZIPはVer1.14から導入できるよう旧manifestも併載します。

ヘルプには「PSLogの更新履歴」を追加し、履歴は `meta/UPDATE_HISTORY.txt` で管理します。現行Version表示は `storage.VERSION` を共通参照します。

ログ検索・編集のQSL処理画面では、QSL受領タグに加えてJCC/JCGとHIS QTHを補正できます。ただし画面操作は下書きで、`保存` を押した時だけまとめて元ログへ反映して閉じます。`閉じる` は保存しません。変更がある場合は「変更内容を保存せず閉じますか？」と確認します。フル編集項目をこの画面へむやみに増やさないでください。

コンテストルール表示は人間向け確認機能であり、表示追加を理由に提出確認チェックや拒否条件を増やさないでください。登録87ルールはコンテスト86件＋QSOパーティ1件です。

今後は変更ファイルのみの差分ZIPで渡してください。要望を集めている段階では実装せず、私が「実装」と依頼してからまとめて対応してください。「まとめ」は確認だけで実装しないでください。次の通常開発番号は原則1.151です。まず引継ぎ内容を確認し、次の指示を待ってください。
