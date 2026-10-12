# PSLog Ver1.16 FIX3

適用先: PSLog Ver1.16 + FIX1 + FIX2 適用済み環境

## 変更内容

- メイン画面の周波数表示右側（Bandの上）にスリムな「接続／切断」ボタンを追加。
  - 接続: 保存済みの無線機設定で通常接続を開始。
  - 切断: 無線機接続と仮想COM中継を停止。
  - 設定自体は保持するため、次回起動時の自動接続設定は変えない。
- 「設定」メニュー直下に「無線機設定」を追加。
  - 既存の設定画面を再利用し、無線機設定タブを直接開く。二重実装はしない。
- 無線機設定画面に通常の「接続／切断」を追加。
  - 「接続テスト」は従来どおり一時確認のみ。
  - 「接続」は現在画面の設定を保存して通常接続を開始。
- com0com の説明を追加。
  - `setupc.exe` の例として `C:\Program Files\com0com\setupc.exe` と `C:\Program Files (x86)\com0com\setupc.exe` を表示。
  - SourceForge の com0com 公式配布ページへのリンクを追加。
  - Program Files / Program Files (x86) / PATH の既存自動検出を利用し、検出できた場合は画面へ自動設定。
- 接続テスト開始前に通常接続中だった場合だけ、テスト終了後に通常接続を復帰するよう修正。
- RadioManager に worker 稼働状態を確認する `is_running()` を追加し、接続中・接続試行中をUIで判定できるようにした。

## 試験

- `compileall`: OK
- radio_control / FIX1 / FIX2 / FIX3 の重点非GUI試験: 14件 OK
- 全体 `unittest discover`: 532件実行、FAIL 0、69 ERROR、9 skip
  - 69 ERROR はこのLinux試験環境に PySide6 がないことによるGUI系ImportError。

Windowsでは、メイン画面の接続／切断、設定メニュー直下の無線機設定、com0com自動検出、仮想COM有効時の接続を重点確認してください。
