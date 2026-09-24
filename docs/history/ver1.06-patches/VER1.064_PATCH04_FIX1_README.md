# PSLog Ver1.064 PATCH 04 FIX1

## 適用先

`PSLog_Ver1.064_PATCH04.zip` 適用済みの Ver1.064 ソースへ上書きしてください。

## 修正内容

「編集 → ログ一括処理 → JCC/JCG」の [C]

> HIS QTHがJapanまたは空欄の場合、RMKSを参考に都道府県までを上書き

で、北海道のJARL地域番号 `101`～`114` が候補にならない問題を修正しました。

- `101`～`114` → `Hokkaido Japan`
- `01` → `Hokkaido Japan`（従来どおり）
- 北海道地域番号から市区町村までは推測しません。
- JCC/JCG欄は変更しません。

## GPT側テスト

- PATCH04専用: 7/7 OK
- PATCH02～04重点回帰: 22/22 OK
- 全テスト探索: 391件、FAIL 0。Linux環境にPySide6がないためGUI系67件のみERROR。

## Windows側確認

1. `python -m unittest discover -v`
2. [C] で RMKS `101`～`114` の任意値を持つ国内QSOが候補に出ること
3. 実行予定が `Hokkaido Japan` になること
4. JCC/JCG欄が勝手に変更されないこと
