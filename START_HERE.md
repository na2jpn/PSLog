# PSLog 1.23 正本 — 2026-11-12

このフルソースを改修の基準にしてください。1.23のQRP標準収録・確認文折り返し・過去年登録・No QSLリストを統合済みです。1.21正本、検索結果からの提出修正、運用地判定のFIX1、オール大阪2026の第32回への訂正は統合済みで、旧差分の追加適用は不要です。

- 操作・ビルド：README.md、WINDOWS_BUILD.md
- 変更内容：RELEASE_NOTES_1.23.md
- 保持方針：docs/BACKUP_RETENTION_1.21.md
- 検証：docs/VALIDATION_1.23.md
- 全ファイルの照合情報：SOURCE_MANIFEST.json

RBNのC初期候補はtelnet.reversebeacon.net:7000（CW・RTTY）、設定コマンドなし。旧標準候補からのみ移行し、独自設定は保持します。A〜Eは60秒巡回、各接続先は最低300秒空けます。
backup_retention.pyで認識済みのバックアップ・完了済み記録を整理します。既存のbackup_keepを共用し、全体復元安全ZIPのみ2世代。未完了・保護印付き・未確定の退避・手動全体ZIPは保持します。startup/exitと成功したoperation_lockの終了時に処理し、保存失敗時には保存後整理をしません。

実装指示までは要望を蓄積する運用です。次の改修で旧版に戻したり、この保持方針を外したりしないでください。Windowsビルド・実回線RBNは別途実機確認が必要です。
