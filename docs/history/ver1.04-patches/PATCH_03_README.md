# PSLog Ver1.04 PATCH 03 — Ver1.042

適用前提: **PSLog Ver1.041（PATCH 01 + PATCH 02 + FIX1 + FIX2）**

このZIPは変更ファイルだけの差分です。PSLogソースのルートへ上書きしてください。

## 変更内容

### 1. Ver1.042

- 製品バージョンを `1.042` へ更新。
- Windows配布ZIP名も `PSLog_1.042_Windows_<timestamp>.zip` へ更新。

### 2. 補助EXEを `exec/` に整理

- Windowsビルド後の配置を `exec/PSLogUpdater.exe` へ変更。
- 将来ほかの補助EXEを追加しても `exec/` にまとめられる構成にした。
- 通常のVer1.042 Windows配布ZIPには `exec/PSLogUpdater.exe` だけを含め、ルート直下には置かない。
- Ver1.041からUpdaterで移行する場合だけ、別途生成される `PSLog_1.042_UpdateFrom_1.041_*.zip` を使用する。この橋渡しZIPは旧仕様に合わせてルート直下に1個だけUpdaterを含み、`exec/` との二重収録はしない。
- Ver1.042起動時、旧レイアウトのルート直下 `PSLogUpdater.exe` があれば `exec/PSLogUpdater.exe` へ自動整理する。

### 3. バックアップ説明文

- 「USB」表記を「USBメモリー」へ変更し、保存先の意味を明確化。

### 4. アワード「4 実績・履歴（任意）」

- 誤って一連の処理を終了する操作に見える「完了」ボタンを削除。
- 画面全体の終了は従来どおり下部の「閉じる」を使用。

### 5. ログ検索・編集画面

- 先頭列名を `出力` から `選択` へ変更。
- 選択中1件の `交信を編集…` を右側詳細欄の下へ移動。
- 一覧のQSOをダブルクリックしても同じ編集画面を開く。
- 下部の削除を `チェックを削除…` へ変更し、チェック済み複数QSOを一括削除可能にした。
- 削除前に件数と対象QSO全件をスクロール可能な一覧で確認する。削除ボタンにも件数を表示する。
- 一括削除は対象行を再検証し、元ログのバックアップを作成してから、複数ファイルでも回復可能な一括処理として実行する。
- 下部ボタンを以下へ整理。
  - `チェックをQSOパーティへ…`
  - `チェックをPOTAへ…`
  - `チェックをSOTAへ…`
  - `チェックをエクスポートへ…`
- QSOパーティーへ渡した場合は、チェックしたQSOだけを固定対象として「2 確認・選択」に表示する。
- その際 `「1 対象・抽出」でパーティーを設定してください。` と案内し、パーティー種別・交換内容はタブ1で設定する。

## テスト

開発環境で以下を確認済み。

- 変更Pythonファイルの構文チェック: OK
- 検索・一括削除・Updater・Windowsパッケージ・復元・版番号関連: **34 tests OK**

開発環境にはPySide6がないためGUIテストは実行していません。Windows側で以下を実行してください。

```powershell
python -m unittest discover -v
.\build-windows.ps1
```

## Windows実機で特に確認する点

1. ビルド後 `dist/pslog/exec/PSLogUpdater.exe` が存在し、`dist/pslog/PSLogUpdater.exe` が存在しないこと。
2. Ver1.042 Windows ZIPが正常に作成されること。
3. 検索画面の編集、ダブルクリック編集、チェック一括削除、各チェック転送が動作すること。
4. 可能ならVer1.041実機からVer1.042 Windows ZIPを選び、Updaterで更新できること。
5. 更新後、PSLogルート直下にUpdaterが残らず、`exec/PSLogUpdater.exe` に整理されること。


## PATCH 03 FIX1

- 通常配布ZIPで `PSLogUpdater.exe` がルートと `exec/` に二重収録されていた問題を修正。
- 通常版は `exec/PSLogUpdater.exe` のみ。
- Ver1.041からの更新互換は、専用の橋渡しZIPを別生成して維持。
