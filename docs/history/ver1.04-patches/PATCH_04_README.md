# PSLog Ver1.04 PATCH 04 — Ver1.043

適用前提: PATCH 03 + FIX1 適用済み Ver1.042 ソース。

## 変更内容

### Windows配布ルートの整理

通常のVer1.043 Windows配布ZIPでは、PSLogルート直下のファイルを `pslog.exe` だけにしました。

- `exec/PSLogUpdater.exe` — 補助実行ファイル
- `meta/BUILD_INFO.json` — ビルド情報
- `meta/PSLOG_UPDATE_INFO.json` — Updater用更新情報
- `docs/` — 将来の利用者向け文書用。Ver1.043では空
- `_internal/` — PyInstallerランタイム

従来ルートに置いていた次の文書はWindows配布版から外しました。

- `USER_GUIDE.txt`
- `SAVE_LOCATION.md`
- `WINDOWS_CHECKLIST.txt`

ソースツリー側の文書は削除していません。

### Updater互換

Ver1.043から更新manifestは `meta/PSLOG_UPDATE_INFO.json` に移動しました。
Ver1.042/1.041の既存Updaterは新形式を直接解釈できないため、Windowsビルドでは旧版ごとの橋渡しZIPも生成します。

- `PSLog_1.043_UpdateFrom_1.042_*.zip`
- `PSLog_1.043_UpdateFrom_1.041_*.zip`

橋渡し更新後、Ver1.043初回起動時に旧ルートJSONを `meta/` へ移し、旧配布文書を除去、空の `docs/` を作成します。

### 配布検査

パッケージ作成時に、通常版のルートへ `pslog.exe` 以外のファイルが混入した場合は失敗させます。また `meta/` のJSONはパッケージ作成処理が毎回生成し、古いJSONの混入を拒否します。

## Windows確認

```powershell
python -m unittest discover -v
.\build-windows.ps1
```

ビルド後は通常ZIPを展開し、ルート直下が `pslog.exe` とフォルダーだけになっていること、`docs/` が空であることを確認してください。
