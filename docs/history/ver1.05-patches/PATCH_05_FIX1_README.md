# PSLog Ver1.055 / PATCH 05 FIX1

Ver1.055 PATCH 05適用後へ上書きするテスト追随FIXです。

## 修正内容

- `test_patch05.py` のソース読込へ `encoding="utf-8"` を明示し、Windows cp932既定環境での `UnicodeDecodeError` を解消。
- `test_search_gui.py` の下部操作ボタン期待値をPATCH 05の新表記へ更新。
- `コンテスト提出へ…` ボタンの期待値も回帰テストへ追加。
- 操作案内の削除・チェック済み引継ぎ説明をPATCH 05の実UIへ追随。

実装本体・ログ形式・VERSION 1.055には変更ありません。
