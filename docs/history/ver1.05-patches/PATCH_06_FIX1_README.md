# PSLog Ver1.056 PATCH 06 FIX1

PATCH 06のWindows GUIテストで判明した不具合・テスト追随不足を修正する差分です。

## 修正
- `SearchDialog(repo, own, parent, filename=..., autorun=...)` の `filename` 引数を、画面上の対象ログファイル入力欄を作るローカル変数が上書きしていた問題を修正しました。入力欄変数を `filename_filter` に分離しています。
- 標準タブのPATCH 06既定値 430/FM に合わせ、Blacklist GUIテストのRSTを59/59へ更新しました。
- コンテストサブメニューが4項目になったPATCH 06仕様に合わせ、POTA GUIテストを更新しました。

## 影響
- 実装本体の変更は `search_ui.py` の変数名衝突修正のみです。
- VERSIONは 1.056 のままです。
- Ver1.056 PATCH 06適用後にこのZIPを上書きしてください。
