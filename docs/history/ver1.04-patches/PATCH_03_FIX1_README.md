# PSLog Ver1.04 PATCH 03 FIX1 — Ver1.042

適用前提: PATCH 03 適用済み Ver1.042 ソース。

## 修正内容

通常の Windows 配布 ZIP に `PSLogUpdater.exe` がルート直下と `exec/` の両方へ収録されていた問題を修正しました。

- 通常版 `PSLog_1.042_Windows_*.zip`
  - `exec/PSLogUpdater.exe` のみを収録
  - ルート直下に `PSLogUpdater.exe` は置かない
- Ver1.041 から PSLog 内の Updater で 1.042 へ更新するための互換性は、別の橋渡し ZIP に分離
  - `PSLog_1.042_UpdateFrom_1.041_*.zip`
  - 旧 1.041 の検証仕様に合わせ、ルート直下に Updater を1個だけ収録
  - `exec/` との二重収録はしない
  - 更新後の最初の 1.042 起動で `exec/PSLogUpdater.exe` へ自動整理

通常の新規展開・手動入れ替え・1.042 以降の更新には `PSLog_1.042_Windows_*.zip` を使用してください。
Ver1.041 の「PSLogをバージョンアップ」から 1.042 へ進む場合だけ `PSLog_1.042_UpdateFrom_1.041_*.zip` を選択します。

## テスト

更新パッケージ、Windowsパッケージ、Updater、復元、ルールパック等の関連 40 tests OK。
