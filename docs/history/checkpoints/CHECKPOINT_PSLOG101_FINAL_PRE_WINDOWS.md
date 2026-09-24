# PSLog 1.01 — ステップ12 最終検証・引継ぎ

作成日：2026-09-15

## 結論

計画したステップ1～12のソース実装とLinux上の自動検証を完了した。
この保存版は、コンテスト、QSOパーティー、通常JARLアワード、AJA、100周年記念、
全日本・全世界10,000局系を含む。PSLog原本11列は変更しない。

## 最終ZIPの範囲

- 現在の全ソース、テスト、参照DB、帳票テンプレート
- 大会・パーティー・アワードの取得原典と調査記録
- ステップごとの仕様、判断、履歴、操作案内
- ファイル別のサイズ・SHA-256一覧（`handoff/MANIFEST.json`）
- 元ソースとZIP展開コピーの全テスト記録
- `START_HERE.md`と最終パッケージ検査記録

古い途中版ZIP、一時レンダー画像、利用者のログ・設定は重複または個人データなので入れない。
過去の判断資料はプロジェクト内のdocs以下に保全する。

## 検証

- `python -m compileall -q .`
- `QT_QPA_PLATFORM=offscreen python -m unittest discover -v`
- 最終ZIPのCRC検査
- ZIP展開後、MANIFEST.jsonの全ファイルをSHA-256で照合
- ZIP展開コピーでも同じ全テストを再実行

実行件数と結果はZIP内の`handoff/tests_source.log`、`handoff/tests_extracted.log`、
`handoff/FINAL_PACKAGE_CHECKS.json`を正とする。

## Windows工程

この環境はLinuxのためWindows EXEを偽装・同梱しない。次の作業だけが別工程として残る。

1. 64-bit Windows 10/11の既存開発環境で`build-windows.ps1`を実行する。
2. 生成したonedir版を`WINDOWS_CHECKLIST.txt`に沿って実機確認する。
3. Excel/PDFの印刷、HAMLOG/zLog、主催者受付など外部との受入を人が確認する。

ビルドスクリプトはAJA用`xlrd`、AJA地域DB、所在地・クラブ・CTY DB、PDF様式を配布対象に含める。
利用者のlogbook、bak、個人設定はクリーン配布へ含めない。

## 注意

JARL・コンテスト規約は改定される。保存済み原典と確認日を基準にし、提出前は当該年度の規約を
人が確認する。ライセンス本文は`LICENSE_DRAFT.md`の案であり、公開配布前に権利者が確定する。
