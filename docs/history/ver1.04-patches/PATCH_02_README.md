# PSLog Ver1.04 PATCH 02 — Updater / Ver1.041

適用前提: **PSLog Ver1.04 PATCH 01 適用済みソース**。
このZIPは差分のみです。展開先の同名ファイルを上書きしてください。

## このPATCHでの版

- `VERSION = 1.041`
- 今後の小修正版は `1.042`, `1.043` ... の形式を使用。
- 比較はPSLog独自の「小数としての版番号」。例: `1.041 < 1.042 < 1.05`。

## PSLogUpdater

- Windowsビルド時に `PSLogUpdater.exe` を別EXEとして生成。
- 配置先は `PSLog/PSLogUpdater.exe`。
- Updaterを直接ダブルクリックした場合は更新せず、PSLogのバージョンアップ機能から実行するよう案内して終了。
- PSLog本体から起動するときは、一時フォルダーへUpdaterをコピーし、一回限りのセッション情報を渡して起動する。
- PSLog終了を確認してから本体を入れ替えるため、実行中の `pslog.exe` / `_internal` を直接上書きしない。
- Updater自身も一時コピーから動くため、インストール先の `PSLogUpdater.exe` を新しい版へ交換可能。

## アプリ内バージョンアップ

`ヘルプ → PSLogをバージョンアップ`

1. 新しい **PSLog Windows版ZIP** を選択。
2. ZIPの製品名、版、構成、ファイル一覧、SHA-256を検証。
3. 現在より新しい版だけを許可。同じ版・古い版は拒否。
4. `config` / `logbook` を `bak/update-safety` へ自動安全バックアップ。
5. PSLogを終了。
6. `PSLogUpdater.exe` がプログラム本体だけを入れ替える。
7. 新しい `pslog.exe` を自動起動。

更新対象外として保持する利用者領域:

- `config/`
- `logbook/`
- `bak/`
- `output/`

プログラム入れ替え中に失敗した場合は、Updater内部の一時ロールバック領域から旧プログラムを戻し、旧PSLogの再起動を試みます。これは「旧版へ戻す機能」ではなく、更新処理失敗時だけのトランザクション保護です。

## Windows配布ZIP

`build-windows.ps1` は今後、

1. test suite
2. `PSLogUpdater.exe` onefile build
3. `pslog.exe` onedir build
4. Updaterを `dist/pslog` へ同梱
5. `PSLog_1.041_Windows_<timestamp>.zip` 作成

の順に実行します。

配布ZIPには `PSLog/PSLOG_UPDATE_INFO.json` を追加し、Updaterが更新パッケージとして検証できるようにしました。

## テスト

この環境でUpdater/パッケージ/バックアップ/版番号関連 **23 tests OK**、変更Pythonの構文チェックOK。
全suiteはこのLinux環境にPySide6がないためGUI系73件がimport errorになります。Windows環境では従来どおり `python tools/run_tests.py` を通してから `build-windows.ps1` を実行してください。

## Windowsで今回特に確認する点

- ビルド後のPSLogフォルダー直下に `PSLogUpdater.exe` がある。
- `PSLogUpdater.exe` を直接起動すると説明だけ表示して終了する。
- `ヘルプ → PSLogをバージョンアップ` がある。
- 自分で今作った Ver1.041 Windows ZIP を選ぶと「現在と同じ版」として拒否する。
- `WINDOWS_CHECKLIST.txt` のUpdater項目を確認する。

実際の `1.041 → 1.042` 自動更新は、次版Windows ZIPができた時点で最終実機確認できます。
