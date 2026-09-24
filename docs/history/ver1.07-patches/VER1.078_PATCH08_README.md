# PSLog Ver1.078 PATCH08

## 基準

Ver1.077 PATCH07 適用済みソースへ上書きする差分です。

## 実装内容

### EASYのバンド表記

- EASY入力1/2ページの `バンド` を `バンド（MHz）` へ変更しました。
- EASYモードだけの表示変更で、標準タブ・コンテスト画面の既存表記は変更しません。

### EASY入力の枠線

- `EASY入力` グループボックスの外枠を、PSLogで使用している緑系アクセント `#6fa37d` に変更しました。
- EASY内の `1 / 2 ページの入力内容`、`His QTH`、`My QTH` 等の子グループボックスへスタイルを波及させず、外側の `EASY入力` 枠だけを緑にします。

## VERSION

`1.078`

Windows配布名は `PSLog_1.078_Windows_YYYYMMDD-HHMMSS.zip`。

## Windows確認ポイント

1. `python -m unittest discover -v` が完走すること。
2. EASYタブの1/2ページで `バンド（MHz）` と表示されること。
3. `EASY入力` の外枠だけが緑色で表示され、右側LogSearchやEASY内の子グループボックスの枠色は従来どおりであること。
4. `build-windows.ps1` で `PSLog_1.078_Windows_...zip` が生成されること。
