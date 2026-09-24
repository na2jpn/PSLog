# PSLog Ver1.064 PATCH 04

## 適用元
Ver1.063 PATCH03適用済みソースへ上書きしてください。

## 実装内容
1. コンテスト提出最終ページの「次へ」を非表示にしました。
2. 「ログ一括処理 JCC/JCG」で明確な海外QSOを処理対象から除外します。HIS QTHが空欄でもCTY.DATで海外局と判定できる場合は除外します。
3. 処理方法を [A]〜[E] 表示へ整理しました。
4. [A][B] 専用の「HIS QTHがJapanまたは空欄でなくても強制」チェックを追加しました。強制ONでも明確な海外QSOは対象にしません。
5. [C]「RMKSを参考に都道府県までを上書き」を追加しました。RMKS1全体が2桁都道府県番号、またはJCC/JCGとして解釈できるコードの場合、その先頭2桁から都道府県を求め、HIS QTHを `Saitama Japan` 等へ変更します。JCC/JCG欄は変更しません。
6. VERSIONを1.064へ更新しました。

## 安全側の国判定
- CTY.DATで相手コールが日本以外と判定できる場合は対象外です。
- HIS QTHが明確に `Japan` / `... Japan` または所在地DBの国内所在地として確認できる場合を国内候補とします。
- HIS QTH空欄は、相手コールをJapanと判定できる場合のみ自動処理対象です。
- JD1等で国判定が曖昧かつHIS QTHも空欄の場合は自動処理しません。

## [C] 都道府県補完
JARL都道府県番号は所在地DBから自動構築します。例：
- 10 → Tokyo Japan
- 11 → Kanagawa Japan
- 12 → Chiba Japan
- 13 → Saitama Japan

## Linux側確認
- PATCH04専用: 6件 OK
- PATCH02/03回帰を含む重点試験: 21件 OK
- Windowsパッケージ・復元・Ver1.06回帰を含む重点試験: 51件 OK
- `python -m unittest discover -v`: 390件中 FAIL 0。ERROR 67件はLinux環境にPySide6がないGUI試験のみ。

## Windows側確認
1. `python -m unittest discover -v` を実行して全件PASSを確認。
2. タイトル等が `PSLog Ver1.064` になること。
3. コンテスト提出の最終ページで「次へ」が表示されないこと。
4. JCC/JCG一括処理が [A]〜[E] の5項目になっていること。
5. 強制チェックが[A][B]でのみ有効になること。
6. [C]でRMKS=`13`、HIS QTH=`Japan` の国内QSOが `Saitama Japan` になること。
7. 海外コールでHIS QTH空欄またはJapanでも、一括補完対象にならないこと。
