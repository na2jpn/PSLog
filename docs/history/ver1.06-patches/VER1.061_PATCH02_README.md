# PSLog Ver1.061 PATCH 02

## 適用基準

- Ver1.061 PATCH 01 + FIX1 + FIX2 適用済みソースへ上書きする差分です。
- Ver1.05系や1.051〜1.059のPATCH/FIXを再適用しないでください。
- VERSIONはVer1.061のままです。

## 実装内容

### 1. HAMLOG Remarks出力

- RMKS1 / RMKS2とは別に `MYCALL / MYQTHをRemarks2へ出力する` を選択可能にしました。
- RMKS1=出力しない、RMKS2=出力しない、MYCALL/MYQTH=OFF の場合、HAMLOGのRemarks1 / Remarks2は完全に空欄になります。
- 従来互換のため、MYCALL/MYQTH出力は既定ONです。

### 2. コンテスト提出「対象ログ」の縦空白

- 対象自局フォームを上寄せ・最大必要高さに固定し、ログ一覧との間に不自然な大空白が発生しないようにしました。
- 胆振日高専用の非表示項目も不要な高さを保持しません。

### 3. 交信編集 JCC/JCG → HIS QTH

- JCC/JCG欄右に `HIS QTHへ反映` を追加しました。
- 所在地DBで一意に特定できるコードだけをHIS QTHへ反映します。
- 5桁だけのJCG郡コードなど複数候補になる場合は推測せずエラー表示します。

### 4. ウィンドウのバージョン表示

古い `PSLog 1.00` が残っていた次の画面を共通 `storage.VERSION` 参照へ変更しました。

- ブラックリスト管理
- POTA提出
- QSL受領一括処理
- 交信編集
- 交信削除確認
- ログ検索・編集
- SOTA提出

### 5. 編集 → ログ一括処理 → JCC/JCG

3段階ウィザードを追加しました。

1. 対象ログ・期間・処理方法
   - 自局コールフィルター
   - ログ複数選択
   - 開始/終了日時はPATCH01の省略入力方式。`20260909`だけでも可、空欄は制限なし
   - 次の4方式から1つ選択
     - JCC/JCG → HIS QTH
     - RMKS → JCC/JCG + HIS QTH
     - HIS QTH → JCC/JCG
     - JCC/JCGとHIS QTHの不一致修正
2. 対象QSO確認
   - 先頭の対象チェックで実行対象を選択
   - 全て選択 / 全て解除
   - 不一致修正だけ `HIS QTH採用` / `JCC/JCG採用` を行ごとに排他的に選択
3. 実行確認
   - 対象数、対象ログ、変更件数、変更予定を表示
   - `実行内容を確認しました` をチェックするまで実行ボタン無効
   - 実行直前に対象ログをバックアップ

所在地DBは曖昧な候補を自動決定しません。RMKSをJCC/JCGとして使う方式も、RMKS1全体がJCC/JCGコードとして解釈できる場合だけ対象にし、RMKS中の任意の数字を拾って推測しません。

## GPT側テスト

Linux環境で実施:

- 変更Pythonファイル `py_compile`: OK
- PATCH02専用非GUI回帰: 9 / 9 OK
- `python -m unittest discover -v`: 378 tests検出、FAIL 0、ERROR 67
- ERROR 67件はLinux環境にPySide6がないことによるGUIテストの `ModuleNotFoundError`。それ以外の失敗なし。

## Windows側で確認してほしい項目

1. `python -m unittest discover -v` を実行し、全テストが通ること。
2. HAMLOG CSVでRMKS1/RMKS2を出力しない + MYCALL/MYQTHをOFFにし、Remarks1/Remarks2が空欄になること。
3. コンテスト提出の「2 対象ログ」で、対象自局とログ一覧の間の巨大な空白が消えていること。
4. 交信編集でJCC/JCGコードからHIS QTHへ反映できること。曖昧なJCGコードは勝手に決めないこと。
5. 上記対象ウィンドウのタイトルが `PSLog Ver1.061` になっていること。
6. `編集 → ログ一括処理 → JCC/JCG` が開き、4方式それぞれで対象抽出→確認→最終確認→バックアップ付き実行ができること。
7. 不一致修正でHIS QTH採用/JCC-JCG採用が同時選択できず、対象行ごとに選択が必要なこと。
