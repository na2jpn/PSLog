# PSLog Ver1.072 PATCH 02

基準: `PSLog_1.07_CANONICAL_SOURCE.zip` + `PSLog_1.071_PATCH01.zip`

## 実装内容

### 1. JCC/JCG一括処理 — RMKS1の安全な付帯情報無視

[B] RMKS → JCC/JCG + HIS QTH、[C] RMKS → 都道府県、のRMKS1解析で次を無視します。

- PSLogが正式に認識するQSLタグ: `BURO` / `BURO.R` / `CARD` / `CARD.R` / `1way` / `1way.R` / `Direct` / `Direct.R` / `LoTW` / `LoTW.R` / `eQSL` / `eQSL.R` / `hQSL` / `hQSL.R` / `QRZ` / `QRZ.R` / `Other` / `Other.R`
- 小数点を含む単独数値: `7.030`、`433.16`、`1295.0` 等（周波数メモ想定）

例:

- `1321 hQSL.R` → `1321` として処理
- `1321 433.16 BURO` → `1321` として処理
- `35 7.030 hQSL.R` → [C]では `35` として処理
- `1321 移動 hQSL.R` → 自動処理しない
- `1321 7MHz hQSL.R` → 自動処理しない

RMKS2は解析しません。数字を任意の文章から採掘する動作には変更していません。

### 2. QSL受領一括TXT — 任意JCC/JCG 4項目対応

従来:

`日付 時刻 相手コール`

に加え、JCC/JCGが分かる場合は次を使用できます。

`日付 時刻 相手コール JCC/JCG`

3項目/4項目とも順序自由です。JCC/JCGは4桁、5桁、5桁+補助英字、6桁の正規コードを受け付けます。海外局などコード不明時は3項目のままで構いません。

時刻は従来どおり `5:10` / `05:10` のように `:` 必須です。`0510` は時刻として受け付けません。

任意JCC/JCGは照合時の確認情報として保持・詳細表示します。QSL受領一括処理は従来の安全原則を維持し、ログのJCC/JCG欄は変更せずRMKSの受領タグだけを更新します。

### 3. 画面・説明

QSL受領一括画面の「受領一覧TXTの形式」を更新し、3/4項目、順序自由、時刻コロン必須、海外局は3項目でよいことを明記しました。

## VERSION

- `storage.VERSION = 1.072`
- Windows配布ZIP: `PSLog_1.072_Windows_<timestamp>.zip`

## Windows確認

1. 差分ZIPをVer1.071へ上書き。
2. `python -m unittest discover -v` を実行。
3. JCC/JCG一括処理で `1321 hQSL.R`、`1321 433.16 BURO` 等が候補になることを確認。
4. RMKS2だけにコードがある行、QSL/周波数以外の文章が残る行は自動対象にならないことを確認。
5. QSL受領TXTで3項目、4項目、4項目の順序入替が読み込めることを確認。
6. コロンなし時刻 `0510` が書式不正になることを確認。
7. `build-windows.ps1` で `PSLog_1.072_Windows_...zip` を生成し起動確認。
