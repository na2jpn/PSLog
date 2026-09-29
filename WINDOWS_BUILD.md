# Windows配布準備 — PSLog 1.15

Windows側では `build-windows.ps1` を使用します。GPT/Linux側ではPyInstallerによるWindows EXE実機確認は行いません。

## ビルド前

1. `python -m unittest discover -v` を実行し、Windows環境で全テストを確認。
2. `storage.VERSION` が `1.15` であることを確認。
3. `meta/UPDATE_HISTORY.txt` の先頭がVer1.15であることを確認。

## ビルド

```powershell
.\build-windows.ps1
```

配布ZIP名は `storage.VERSION` から自動取得し、`PSLog_1.15_Windows_<timestamp>.zip` となります。

## Ver1.15更新ZIPの構造

利用者が指定するZIPは常に1つです。ルート直下の通常ファイルはEXEだけとし、その他はフォルダーへ格納します。

- `PSLog/pslog.exe`
- `PSLog/exec/PSLogUpdater.exe`
- `PSLog/_internal/...`
- `PSLog/meta/BUILD_INFO.json`
- `PSLog/meta/PSLOG_UPDATE_INFO.json` — Ver1.14からの移行互換
- `PSLog/meta/versionup.json` — Ver1.15+の更新管理
- `PSLog/meta/UPDATE_HISTORY.txt`
- `PSLog/docs/`

`config/`, `logbook/`, `logbook_flr/`, `bak/`, `output/` は更新対象に含めません。

## Windows実機確認

`WINDOWS_CHECKLIST.txt` を使用し、特に次を確認します。

- Ver1.14→Ver1.15の1-ZIP更新
- 更新履歴メニュー
- QSL処理画面の下書き→保存方式
- 未保存変更で閉じる際の確認文言
- PyInstallerビルド後の自己診断と自動再起動
