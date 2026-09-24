# PSLog Ver1.069 コンテストルール表示・先行15大会パッチ

## 適用元

`PSLog_1.069_WORK_HANDOFF_SOURCE` の現行フルソース（Ver1.069 PATCH09 + FIX1 + FIX3、現行の表示途中差分と文字コード修正を含む）へ、差分ZIPの相対パスを上書きします。古いパッチを再適用しません。VERSIONは1.069のままです。

## 内容

チェックリストの1～15番に対応する15大会の表示専用 `event.rule_view` を、公式2026年規約と確認済みのユーザー指示に基づいて更新しました。呼び出し、管内外の交信対象、ナンバー交換、得点とマルチ、提出時の注意を人間向けに表示します。ALL JA4の登録URLを公式PDFへ更新します。

- 大枠の出力上限が未登録の場合、共通欄は「制限なし」。移動運用の独自条件が未登録の場合、行を表示しません。
- JA8の得点は受信した年代別符号に従い、特殊なルール欄に対応表を記載。年代別符号はマルチとして数えません。
- 6m AND DOWNは2400MHz帯以上2点を表示。FDは1交信1点と局種Aの総得点係数2を分けて説明します。
- ALL JA5のCQ JA5は慣例と明示し、公式指定として扱いません。
- QSOパーティをコンテスト選択とコンテストルール表示の一覧から除外します。専用QSOパーティ画面とルールファイルはそのままです。
- 愛・地球博のR1.0ログ出力は既存の `band_time` により運用バンド順・バンド内時刻順で、追加修正は不要でした。

`devtools/contest_rule_view_verified_15.json` は15大会の表示生成元で、該当の既存ビルダーが再生成時に読み込みます。採点用の部門、条件、確認チェック、提出必須項目には手を加えていません。

## 検証

```
python -m unittest test_contest_rule_view_verified_15 test_contest_rule_view_audit_87 -v
python -m compileall -q contest_event.py rule_view_data.py contest_ui.py rule_view_ui.py devtools
```

Windowsでは `python -m unittest discover -v` を実行し、愛・地球博・JA8・JA9・JA0などのコンテストルール表示を確認してください。Linux環境にはPySide6がないためGUIの実機確認は行っていません。Windowsビルドはユーザー側で確認してください。

## 対象範囲

先行15大会のみの表示整備です。残り71大会の公式規約照合は継続中で、この差分ZIPでは確定しません。QSOパーティは登録87ファイル中の別枠です。
