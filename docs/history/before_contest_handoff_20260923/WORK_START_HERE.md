# Work 引き継ぎ用 START HERE

このZIPは、PSLog Ver1.069 の現在の作業状態を Work へ引き継ぐためのフルソース・スナップショットです。

## 現在の基準

このZIPのソースツリー自体を唯一の基準として使用してください。

適用済み状態:
- Ver1.069 PATCH09
- Ver1.069 PATCH09 FIX1
- Ver1.069 PATCH09 FIX3

VERSION:
- 1.069

古い Ver1.05 / Ver1.06 初期正本や、1.061～1.068 のPATCH/FIXを再適用して再構成しないでください。
このZIPに含まれる過去PATCHのREADMEや履歴は参照用です。

`SOURCE_MANIFEST.json` は Ver1.06 正本作成時の歴史的記録であり、
今回の Work 作業の基準バージョンを示すものではありません。
今回の基準はこのファイルと `WORK_SOURCE_MANIFEST.json` です。

## 最初に読むもの

1. WORK_START_HERE.md
2. WORK_HANDOFF_PROMPT.md
3. START_HERE.md
4. HANDOFF.md
5. CHANGELOG.md
6. VER1.069_PATCH09_README.md
7. VER1.069_PATCH09_FIX1_README.md
8. VER1.069_PATCH09_FIX3_README.md
9. docs/development/contest_rule_display_audit_87/PSLog_1.069_CONTEST_RULE_DISPLAY_AUDIT_87.md
10. docs/development/contest_rule_display_audit_87/PSLog_1.069_CONTEST_RULE_DISPLAY_AUDIT_87.csv

## 今回の主作業

登録済み87大会の「コンテストルール表示」を公式規約ベースで総点検し、
愛・地球博記念コンテストの `rule_view` 表示品質を基準として整備すること。

重要:
- 提出時の機械判定と、人間向けルール表示を混同しない。
- 表示項目を増やしたことを理由に提出制限を増やさない。
- 公式規約に基づく正確な表示を優先する。
- 推測で規約を埋めない。
- フリラ本体は Ver1.07 へ持ち越し。今回追加しない。

詳細は `WORK_HANDOFF_PROMPT.md` を参照してください。
