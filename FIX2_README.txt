PSLog 1.19 FIX2（FIX1含む累積差分）2026-10-20

ZIP内のファイル・devtools・docsを、既存PSLog_1.19フォルダーへ上書きしてください。
FIX1の未適用・適用済みのどちらにも使用できます。
EXEで使用する場合は上書きしたソースから通常の手順で再ビルドしてください。

修正内容と検証結果：docs/VALIDATION_1.19_FIX2.md
版番号は1.19を維持。申請済設定・交信TXTは上書きしません。
DXCCチェックを開き直して「表示」で再集計してください。
C7Aは未確定として要確認に残ります。

確認：python -m unittest test_v119 test_v119_fix2
全体確認：python -m unittest discover
