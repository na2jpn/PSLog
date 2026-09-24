# Windows配布準備 — PSLog 1.14

## 正本

基準ソースは `PSLog_1.14_CANONICAL_SOURCE.zip` のみです。Ver1.10正本やVer1.11/1.12のPATCH/FIXを積み直さないでください。

## テスト

```powershell
python -m unittest discover -v
```

テスト成功後にビルドします。

## ビルド

```powershell
.\build-windows.ps1
```

通常配布ZIPは `release/PSLog_1.14_Windows_<timestamp>.zip` です。ファイル名の版数は `storage.VERSION` から自動取得します。

## Ver1.14重点確認

- タイトルが `PSLog Ver1.14`。
- 標準タブとコンテスト入力で相手コール欄が太字。
- QSL処理ショートカットに `QRZ.R` / `CARD.R` がある。
- JCC/JCG交信チェックがLoading表示付きで完了し、都道府県を展開した時だけ詳細行を生成する。
- 都道府県行の全JCC/JCG達成表示とCFM残数が正しい。
- EASYタブは最大2枚、`[E]CALL`表示。
- EASYは2ページ構成、右側LogSearch常設、2ページ目のJST時刻修正と5分以上の時刻差選択が動く。
- EASY登録後はBand/Mode/Sub/My QTHを保持し、相手側情報をクリアする。
- EASYの `バンド（MHz）` 表示と緑枠を確認。
- フリラタブは同時最大4枚で、選択色は水色。
- 初回起動で「アマチュア無線のコールサイン」からフリラへ切替でき、フリラのみで開始できる。
- フリラのみで開始してもアマチュア用 `own` がフリラコールで上書きされない。
- フリラ新規作成で不正入力を警告しても作成ダイアログが閉じず、機種名空欄でも作成できる。
- フリラタブ右側LogSearchが同じ自局コールの全種類を横断し、種類列を表示する。
- メニュー「フリラ」の既存タブ呼び出し、ログ検索・編集が動く。
- `logbook_flr/` が全体バックアップ/復元対象になっている。

## 共通重点確認

- PSLog TXT 11項目、UTF-8 BOM + CRLF、JSTを維持。
- `logbook/` と `logbook_flr/` が必要時に生成される。
- Updaterで `logbook_flr/` を含む利用者データを上書きしない。
- 標準/コンテスト/QSOパーティ/アワードの既存画面が開く。
- LogSearch編集・削除、RMKS2、通常エクスポート、バックアップ/復元が動く。
- Updater用メタ情報のversionが1.14。
