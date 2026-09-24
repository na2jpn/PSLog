# PSLog Ver1.066 PATCH06 FIX1

## 修正内容
Windows の `test_qsl_gui.QSLGuiTests.test_selection_invalidation_pagination_and_detail_choice` で、同一日時の複数QSOが存在すると `qsl_batch.prepare()` 内の周辺QSO一覧生成で `Hit` オブジェクト同士を比較しようとして `TypeError` になる問題を修正しました。

### 原因
周辺QSO用の `(datetime, Hit)` タプルを `sorted()` していたため、日時が同一の場合に2要素目の `Hit` 比較へ進んでいました。`Hit` は順序比較を持たないためエラーになっていました。

### 修正
日時だけをソートキーに指定し、同一日時QSOを安全に保持できるようにしました。

### 回帰テスト
`test_qsl_batch.py` に「同一日時に複数QSOがある場合でも前後±3分一覧を作成できる」テストを追加しました。

Linux側確認:
- PATCH06/05/04 + QSL batch 重点テスト: 30/30 OK
- `test_qsl_batch.py`: 11/11 OK

VERSION は Ver1.066 のままです。

## 適用方法
Ver1.066 PATCH06 適用済みソースへ、このZIPの内容を相対パスのまま上書きしてください。
