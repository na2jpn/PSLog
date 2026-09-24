# PSLog Ver1.061 PATCH 01 FIX1

## 対象
Ver1.06正本へ `PSLog_Ver1.061_PATCH01.zip` を適用済みのソース。

## 修正内容
Windows全テストで `test_v101.V101Tests.test_years_kana_order_old_rules_and_editor_roundtrip` が失敗する問題を修正。

原因は、ソース実行／テスト環境で、公式ルールと同名のユーザー作成ルールを `（ユーザー変更）` と誤判定していたこと。

FIX1では由来判定を次のように整理した。

- PSLogが管理状態を持つ公式ファイルを編集したもの: `（ユーザー変更）`
- frozen/配布版で旧版から引き継がれた同名公式候補: 既存保護のため `（ユーザー変更）`
- ソース実行／テスト環境でPSLogが導入していない同名ルール: `（ユーザー定義）`
- 公式同梱内容と同一: 公式（接頭辞なし）

既存のVer1.01回帰テストは、新しい「ユーザー定義」表示仕様に合わせて更新した。

## Linux側確認
`python -m unittest -v test_patch01_1061`

9 tests / OK

PySide6を必要とする `test_v101` 自体はLinux環境では実行不可のため、Windows側で全テストを再実行してください。
