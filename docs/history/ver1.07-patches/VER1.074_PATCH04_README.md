# PSLog Ver1.074 PATCH 04

基準: Ver1.073 PATCH03 適用済みソース

## 変更内容

### 1. 交信編集/QSL処理の導線

- 交信編集画面の「QSL追加」を次の順へ拡張。
  - `LoTW.R`
  - `hQSL.R`
  - `eQSL.R`
  - `BURO.R`
  - `QRZ.R`
  - `CARD.R`
  - `Other.R`
- `QRZ.R` / `CARD.R` は既存のPSLog正式QSLタグ処理をそのまま利用し、元タグから`.R`への昇格・重複防止・RMKS2保持を既存処理と共通化。
- 「ログ検索・編集」右側の「交信を編集…」を左右2ボタンへ変更し、左へ「QSL処理…」を追加。
- QSL処理画面は選択QSOの日時・バンド・モード・相手コール・HIS QTH・JCC/JCG・現在RMKSを表示のみでコンパクトに確認し、QSL受領タグだけを即時反映する。通常の交信編集とは別の人間向けショートカットで、保存処理は同じ原本保護機構を使用。

### 2. JCC/JCG交信チェック

メニュー `提出ログファイル作成 > アワード > JCC/JCG交信チェック…` を追加。

- 対象自局コールはアマチュアログに実在するベースコールだけをプルダウン表示。
- ログが無い場合は「ログがありません」と表示し、集計不可。
- `/1`、`/P` 等の運用サフィックス付きログを含めるオプションを用意。
- 画面を開いただけでは集計せず、「集計」を押した時だけ対象ログ全体を走査。処理負荷の注意を画面上部に表示。
- 結果は47都道府県単位の折りたたみ表示。初期状態は折りたたみ。
- 都道府県見出しには成立時のみ、`全JCC-交信済` / `全JCC-QSL済` / `全JCG-交信済` / `全JCG-QSL済` を表示。
- 各JCC/JCGについて「全バンド」と各バンドの `未交信 / 交信済 / QSL済` を表示。
- JCGは町村識別アルファベットを無視し、5桁の郡単位で集計。
- 政令指定都市の6桁区コードはJCC親市へ集約。東京23特別区は現行のJCC相当単位として個別表示し、2010-04-01以後の交信を対象。
- QSL済はPSLogの正式受領タグ（LoTW.R、BURO.R、CARD.R、Direct.R、1way.R、eQSL.R、hQSL.R、QRZ.R、Other.R）のいずれかがあるQSOとして判定。
- 地域一覧は現行 `locations.json` を優先して使用し、現行JCC/JCGを対象にする。旧開発ツリー用にAJA一覧へのフォールバックも保持。

### 3. アマチュア/フリラのログ領域分離基盤

- 共通ログ取得モジュール `logbook_sources.py` を追加。
- アマチュア無線ログは `logbook/` のみを正式取得元とし、新規機能は共通取得関数を経由。
- 将来のフリラ専用フォルダー名を `logbook_flr/` として予約。
- PSLog起動時に `logbook/` と `logbook_flr/` が無ければ生成。
- `Repository.free_book` で将来用フリラログルートを明示。
- Windows更新パッケージでも `logbook_flr/` を利用者データ領域として保護し、更新ZIPへの混入を拒否。
- 現時点ではフリラQSO保存機能は未実装。全体バックアップ/復元への追加はフリラ機能有効化時に行う。

## VERSION

- `storage.VERSION = 1.074`
- Windows配布ZIP: `PSLog_1.074_Windows_<timestamp>.zip`

## この環境での確認

- `python -m compileall -q .` : OK
- PATCH04コア、検索、QSL一括、更新、ストレージ、復元、Windowsパッケージ関連の選別回帰テスト: OK
- `python -m unittest discover -v` : PySide6未導入によるGUI系ImportErrorのみ。assertion FAILは0件。

GUIの新規QSL処理画面・JCC/JCG交信チェック画面はWindows側の全テストと起動確認で最終確認してください。

## Windows確認

Ver1.073へこの差分ZIPを上書きしてから:

```powershell
python -m unittest discover -v
.\build-windows.ps1
```

全テスト成功後、起動確認してください。
