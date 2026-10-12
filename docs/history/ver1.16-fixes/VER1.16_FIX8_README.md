# PSLog Ver1.16 FIX8

適用先: **PSLog Ver1.16 + FIX1～FIX7 適用済み環境**

## 修正内容

Windowsの小さい画面（テスト条件 480×320）で `SettingsDialog` を開いた場合に、操作ボタンが安全スクロール領域から外れて到達不能と判定される問題を修正しました。

### 変更

- 「無線機設定」「仮想COM中継」タブ内の二重 `QScrollArea` を廃止しました。
- `SafeDialog` が提供する外側の安全スクロールへ一本化しました。
- 通常サイズでは従来どおりタブ表示、小さい画面ではダイアログ全体をスクロールして各ボタンへ到達できます。
- FIX7の「無線機設定」と「仮想COM中継」のタブ分離、接続/切断、仮想COM作成機能そのものには変更ありません。
- FIX7のレイアウト構造を固定していた回帰テストは、FIX8の二重スクロール廃止仕様へ更新しました。テストの削除・無効化はしていません。

## GPT側確認

- `compileall`: OK
- `test_radio_fix7`, `test_radio_fix5`, `test_storage_replace_retry_fix6`: 12件 OK
- 差分構文・manifest・ZIP CRC確認済み

Windows側では、全テストを再実行し、特に `test_dialog_access.DialogAccessTests.test_small_screen_buttons_tabs_and_cancel` が通ることを確認してください。
