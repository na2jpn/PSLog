# PSLog Ver1.044 PATCH 05 FIX1

Windows実機で標準タブ「交信入力」の先頭余白が大きく崩れる回帰を修正します。

原因は PATCH 05 で QGroupBox 内の QVBoxLayout に `setContentsMargins()` / `setSpacing()` を直接指定した変更です。既存の QGroupBox スタイルシート（margin-top / padding-top）との組み合わせでWindows上のレイアウトが崩れたため、この変更だけを元の安定したレイアウト指定へ戻します。

バージョンは Ver1.044 のままです。
