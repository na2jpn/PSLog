# PSLog Ver1.04 PATCH 06 FIX1 — Ver1.045

PATCH 06 適用済みの Ver1.045 ソースへ上書きする修正差分です。
バージョン番号は 1.045 のままです。

## 修正理由

Windows実機で通常ZIPからUpdater更新した直後、Updaterは「更新完了」と表示したものの、新しい `pslog.exe` の起動時に PyInstaller 内部アーカイブの展開エラー（`zlib.error: incorrect header check`）が発生しました。

これまでのUpdaterは、ZIP自体のSHA-256検証は行っていましたが、展開後・設置後のファイル整合性と、新しい `pslog.exe` が実際に更新モジュールを読み込めることを確認する前にロールバック用旧本体を削除していました。

## 修正内容

- 更新ZIP展開後に、manifest記載の全ファイルをSHA-256で再検証。
- PSLogフォルダーへ設置後にも全ファイルをSHA-256で再検証。
- 新しい `pslog.exe --update-self-check` を起動し、`update_launcher` / `update_package` を実際に読み込めることを確認。
- 上記のどれかが失敗した場合は「更新成功」にせず、旧プログラムへ自動ロールバック。
- `build-windows.ps1` でもZIP生成前に同じ自己診断を実行し、壊れたWindowsビルドを配布ZIP化しない。
- 通常起動時はUpdater専用モジュールを読み込まないようにし、ログ記録機能とUpdaterを分離。

## 復旧

今回すでに壊れたVer1.045はUpdaterから自己修復できないため、このFIXをソースへ適用してWindows版を再ビルドし、従来どおりPSLogフォルダーを手動入替してください。利用者データは事前の全体バックアップから復元できます。

次回以降のUpdaterでは、新本体の自己診断が成功するまで更新完了扱いになりません。
