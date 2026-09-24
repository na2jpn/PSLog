# PSLog Ver1.04 PATCH 09 FIX1 — Ver1.048

適用元: PATCH 09 / Ver1.048 適用済みソース。

## 修正内容

- PATCH 09でJCC/JCGの正規形を「コードのみ」に統一したため、QSL一括処理結果CSVのテスト期待値も `JCC 100121` から `100121` へ更新しました。
- 実装本体の不具合ではなく、旧表記を期待していた回帰テストの更新漏れです。
- Verは1.048のままです。

## 確認

`python -m unittest test_qsl_batch -v` で9件すべてOKを確認済みです。
