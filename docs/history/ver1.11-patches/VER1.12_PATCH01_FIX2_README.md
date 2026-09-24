# PSLog Ver1.12 PATCH01 FIX2

適用元: `PSLog_1.11_PATCH01` + `PATCH01_FIX1` 適用済みソース。

## 修正内容

- PSLog の `VERSION` を **1.12** に更新。
- `build-windows.ps1` の Windows 配布ZIP名を固定 `PSLog_1.10_Windows_*` から、`storage.VERSION` を読み取る方式へ変更。
  - 今回は `PSLog_1.12_Windows_YYYYMMDD-HHMMSS.zip` になります。
  - 今後の版上げでもビルドスクリプト側の固定文字列修正が不要になります。
- Windows確認票の表示バージョン／配布ZIP名を1.12へ更新。
- VERSION を直接確認する既存回帰テストの期待値を1.12へ更新。
- PATCH01_FIX1 の2件（旧VERSION期待値／ユーザー定義表示）は維持した状態を前提とします。

## GPT側確認

- 変更Pythonファイルの構文確認: OK
- PySide6不要の関連回帰テスト: **159件 OK**
- Windows配布パッケージ生成ロジックのテスト: OK
- Updater版数比較: `1.12 > 1.11`, `1.12 > 1.101`, `1.12 > 1.10` を確認
- PySide6依存GUIテストはGPT/Linux環境では実行不可。Windows側全テストで確認してください。
