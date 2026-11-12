# PSLog 1.23 — 共通ライセンスへの切り替え

2026-11-12 / 対象: https://github.com/na2jpn/PSLog

基準コミット: `e9bd2753f61e25d9b6ead31e2f71b32e2966a449`

## GitHub Desktopで適用

1. GitHub DesktopでPSLogを選び、Fetch origin / Pull originで最新の状態にしてください。未コミットの作業がある場合は、この差分と同じファイルの変更を先に確認してください。
2. Repository → Show in Explorerで作業フォルダーを開きます。
3. 差分ZIP内のファイル・フォルダーを、`main.py`と`README.md`がある場所へ上書きコピーします。Git管理情報や利用者のログ・設定はZIPに含みません。
4. GitHub DesktopのChangesで確認し、コミットしてください。例: `Adopt GPL-3.0-or-later and update author/license notices`。
5. Push originでGitHubへ反映します。必要に応じて公式サイトの旧配布条件も新しい説明にそろえてください。

基準コミット以降に同じファイルを変更している場合は、上書き前に差分を照合してください。

## 変更内容

- リポジトリ直下に、改変していないGNU GPL v3本文の`LICENSE.md`と、共通の適用宣言・日英説明の`LICENSING.md`を追加。
- 作者表示を`Hiroshi Tanaka (JH1HST)`、本体ライセンスを`GPL-3.0-or-later`に統一。
- README、AUTHOR_NOTICE、およびアプリ内の旧「無改変版の再配布禁止」「改変版の必須通知」を整理。公開連絡は任意。
- 「PSLogについて」にライセンス案内を設け、全文と共通説明をオフラインで開くボタンを追加。
- Windowsビルドにライセンス文書を含め、通常の配布ZIPでは`docs`に3文書を同梱。古いビルド済みフォルダーに残るライセンスのコピーは、現行のソース文書に置き換えてからハッシュを記録。
- 旧版更新用の互換ZIPでも、管理対象の`_internal/licenses`にライセンスを保持。
- 第三者ライブラリやCTY等の既存表示・資料は変更しません。ソース内の`docs/history`は旧版の記録として保持し、現行のライセンス条件にはしません。

ソフトウェアのバージョンは1.23を維持しています。このZIPはソースの差分で、署名済みEXEやビルド済みEXEを含みません。既存の配布済みEXEの画面表示は、ソースを更新するだけでは変わりません。

## 確認

- `python -m unittest -v test_windows_package test_update_package` — 19件成功。
- `python -m unittest -v test_patch07_1077.Patch071077CoreTests` — 5件成功。
- Qtオフスクリーン確認: 「PSLogについて」の作者・GPL表示、旧再配布禁止文がないこと、GPL全文と共通説明の両ボタンの表示を確認。
- 共通の2文書が原本と一致すること、更新マニフェストに同梱文書が含まれることを確認。
- WindowsでのEXEビルド・実機確認、全テストの再実行、第三者資料すべての権利監査は実施していません。

`SOURCE_MANIFEST.json`の元のverification値は、基準正本の記録を継承しています。今回の確認範囲は追加した`license_update_20261112`を参照してください。
