# Windows配布準備 — PSLog 1.16

## ビルド前

1. `pip install -r requirements.txt` を実行し、PySide6 / PyInstaller / pyserial等を揃える。
2. `storage.VERSION` が `1.16` であることを確認。
3. `meta/UPDATE_HISTORY.txt` の先頭がVer1.16であることを確認。
4. `python -m unittest discover` を実行し、Windows GUIテストを含め確認。
5. `powershell -ExecutionPolicy Bypass -File .\build-windows.ps1` でビルド。

配布ZIP名は `storage.VERSION` から自動取得し、`PSLog_1.16_Windows_<timestamp>.zip` となります。

## Ver1.16追加依存

- `pyserial` はCI-V直接接続とCOM列挙に使用し、PyInstallerへ同梱。
- Hamlib方式は利用者環境の `rigctld.exe` を使用。PSLog配布物へHamlibを同梱しない。
- 仮想COM試験機能はWindowsへ既に導入済みのcom0com `setupc.exe` を使用。PSLog配布物へcom0comカーネルドライバを同梱/自動導入しない。

## Windows実機重点

- CI-V: 接続/切断、起動時自動接続、周波数追従、無線機未接続時もPSLog継続。
- Hamlib: rigctld起動/終了、Model ID、周波数追従。
- 自動セット: 標準/EASY/コンテスト、RMKS1/RMKS2/Band、MODE不変、フリラ非適用。
- 仮想COM: OFF初期値。物理COM8なら外部COM208/内部COM209、競合時COM308/309等。作成/削除時だけUAC、通常終了では常設ペアを削除しない。外部ソフト双方向CI-Vと中継中の周波数追従を確認する。
- コンテスト非数値RST: 編集およびQSL簡易処理後に元値を保持して保存できる。

Ver1.15の1-ZIP updater構造と利用者データ保護も従来どおり確認します。
