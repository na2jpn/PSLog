# PSLog Ver1.16 FIX9

適用先: **PSLog Ver1.16 + FIX1～FIX8 適用済み環境**

## 修正内容

com0com の「仮想COMを作成」で UAC 許可後、`setupc.exe` が `C:\Windows\System32\com0com.inf` を探して `ERROR: 2 - The system cannot find the file specified.` になる問題を修正しました。

### 原因

管理者権限で起動した `setupc.exe` / PowerShell の作業ディレクトリが `C:\Windows\System32` になり、com0com が同梱の INF ファイルを誤った場所から探していました。

### 変更

- 管理者権限で com0com を操作するとき、作業ディレクトリを **`setupc.exe` が存在するフォルダー**へ固定します。
- 仮想COM作成用の管理者 PowerShell 内でも `setupc.exe` のフォルダーへ `Set-Location` してから `list / install / change / remove` を実行します。
- 「仮想COMを削除」でも同じ作業ディレクトリを指定します。
- 通常権限で `setupc list` を呼ぶ場合も `setupc.exe` のフォルダーをカレントディレクトリとして使用します。
- 既存の仮想COM番号、CI-V接続、FIX8の設定画面レイアウトには変更ありません。

## GPT側確認

- `py_compile`: OK
- `test_radio_fix9`, `test_radio_fix7`, `test_radio_fix5`, `test_storage_replace_retry_fix6`: **14件 OK**
- 差分ZIP CRC確認済み

Windows側では、無線機を切断した状態で **設定 → 無線機設定 → 仮想COM中継 → 仮想COMを作成** を実行し、UAC許可後に `COM208 ⇔ COM209` 等が作成済み表示になることを確認してください。
