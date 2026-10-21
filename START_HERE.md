# PSLog 1.21 正本 — 2026-10-22

このフルソースを改修の基準にしてください。1.20正本までの変更は統合済みで、旧差分の追加適用は不要です。

- 操作・ビルド：README.md、WINDOWS_BUILD.md
- 変更内容：RELEASE_NOTES_1.21.md
- 保持方針：docs/BACKUP_RETENTION_1.21.md
- 検証：docs/VALIDATION_1.21.md
- 全ファイルの照合情報：SOURCE_MANIFEST.json

RBNのC初期候補はtelnet.reversebeacon.net:7000（CW・RTTY）、設定コマンドなし。旧標準候補からのみ移行し、独自設定は保持します。A〜Eは60秒巡回、各接続先は最低300秒空けます。
backup_retention.pyで認識済みのバックアップ・完了済み記録を整理します。既存のbackup_keepを共用し、全体復元安全ZIPのみ2世代。未完了・保護印付き・未確定の退避・手動全体ZIPは保持します。startup/exitと成功したoperation_lockの終了時に処理し、保存失敗時には保存後整理をしません。

実装指示までは要望を蓄積する運用です。次の改修で旧版に戻したり、この保持方針を外したりしないでください。Windowsビルド・実回線RBNは別途実機確認が必要です。
