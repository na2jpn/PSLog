# PSLog Ver1.070 PATCH10 FIX2

## 対象

`PSLog_1.070_PATCH10.zip` 適用後の Ver1.070 に上書きしてください。
FIX2 は FIX1 を包含しています。FIX1 を未適用でも、このZIPだけを PATCH10 の上へ上書きできます。
VERSION の変更はありません。

## 修正内容

### 1. 同名ルールの出自判定をソース実行と配布版で分離

`bundled_sync.bundled_status()` の判定を整理しました。

- ローカル内容と同梱内容が一致: `official`
- `.pslog-bundled-state.json` に PSLog 管理履歴がある同名ファイルが相違: `user_modified`
- frozen / 配布版で、管理履歴がなくても同梱ルールと同名で内容が相違: 旧版互換のため `user_modified`
- ソース実行で、管理履歴がなく、別ルートに偶然同名のユーザールールがある: `user_defined`

これにより Windows EXE の従来互換を維持しつつ、Linux/macOSを含むソース実行・将来のマルチプラットフォーム開発で、ファイル名だけを理由にユーザー定義ルールを「ユーザー変更」と誤判定しません。

### 2. 回帰テスト追加

`test_patch01_1061.py` に以下を明示するテストを追加しました。

- source mode の同名新規ルール → `user_defined`
- source mode でも管理履歴あり → `user_modified`
- frozen mode で管理履歴のない旧版由来同名編集 → `user_modified`
- 既存の同梱同期・ユーザー編集保持 → 維持

### 3. FIX1を包含

`test_patch10_1070.py` の開催月表示テストについて、存在しない一時ディレクトリ内の同梱ルールを読みに行かず、実際のソースツリーの同梱ルールを読む修正を含みます。

## 確認結果（Linux / source mode）

- `python -m unittest -v test_patch01_1061` : 11件 OK
- `test_full_restore + test_patch01_1061 + test_patch10_1070_core` : 21件 OK
- `test_patch10_1070.py` は PySide6 がこの検証環境にないため GUI 実行不可。Windows/PySide6 環境で全テストを再実行してください。

## 上書きファイル

- `bundled_sync.py`
- `test_patch01_1061.py`
- `test_patch10_1070.py`（FIX1包含）
- `VER1.070_PATCH10_FIX2_README.md`
- `PATCH10_FIX2_MANIFEST.json`
