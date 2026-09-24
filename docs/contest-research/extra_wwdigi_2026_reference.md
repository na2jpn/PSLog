# WW DIGI（2026）

<!-- CURRENT_IMPLEMENTATION_STATUS_START -->
> **現在の実装状態（Ver1.02 文書整理 / 2026-09-16）: 実装済み**
>
> - WW DIGI (`ww-digi`, 2026)
>   - 実行定義: `config/rules/ww-digi_2026.txt`
>   - 現行監査: 28種目。GL4中心間距離点/GL2マルチ・FT4/FT8共通重複・系列別毎時8変更。ZZ00は総得点未確定でCLAIMED-SCORE省略。Cabrillo3・全帯保持。 主催受付・Windows実機未検証。
> - PSLOG101最終監査: **定義済み87 / 未定義0、全体回帰554件合格**。
> - Ver1.01正本はWindows上の全unittestがOKになった状態で受領済み。大会ごとのWindows実機操作・EXE・主催者受付確認は、監査記載どおり別確認です。
>
> **この下に残る「未実装」「未検証」「本体未対応」等は、調査・設計開始時点の履歴です。現在状態の判定には使用しません。**
> 現在状態はこの欄と [`docs/IMPLEMENTATION_STATUS.md`](../IMPLEMENTATION_STATUS.md)、および現行コード・回帰テストを優先してください。
<!-- CURRENT_IMPLEMENTATION_STATUS_END -->
調査台帳登録済・未実装。主催表示：WW Digi DX Contest Committee。
規約：https://ww-digi.com/rules/
FAQ：https://ww-digi.com/rules_faq
形式：https://ww-digi.com/cabrillo.htm
直接取得403のため、sources/wwdigi_*_web*.txtはWeb抽出結果であり原HTMLではない。

## 規約の中核
8/29 12:00:00～8/30 11:59:59UTC。1.8/3.5/7/14/21/28MHz、FT4/FT8。交換4桁GL。同一局同一バンドはモードを変えても1回得点。
交信点=1＋floor(4桁GL中心間の短経路距離km/3000)。例5541km=2点。マルチはバンド別の先頭2英字Grid Field数。全バンド得点合計×マルチ合計。
SO ONEはALL/SINGLE、UNLIMITEDはALL、各HIGH/LOW/QRP。MO ONEはHIGH/LOW、TWO/UNLIMITEDはHIGH。MO ONE毎時8変更、TWO各送信機毎時8変更。出力1500/100/5W。補助使用可。FT4/FT8のみ。
締切本文は48時間以内と9/1 23:59UTCを併記。終了からの48時間と一致しない点を記録。

## FAQ・形式と設計
相手GL未受信はZZ00。これは未知の専用値で、通常のGL検証・距離計算に通さない。DUP含め記録を消さない。採点辞退はX-QSO。FAQ旧記述の5日締切・10分ルールを現行本文へ適用しない。
Cabrillo3推奨、CONTEST=WW-DIGI、ヘッダーMODE=DIGI、行DG。送受GLのみ、レポート欄なし。FAQ内の旧SNR付き例ではなく現行形式説明を優先。TWOの送信機番号0/1。帯域代表値1800/3500/7000/14000/21000/28000又は実kHz周波数。
距離は実QTH緯度経度や6桁GL中心ではなく交換した4桁中心から計算する。地球モデル・距離丸めの詳細は未確定。3000km境界付近は主催算出と照合してから確定する。対蹠点・日付変更線等を含む検証が必要。
ZZ00の採点内訳はここで推測しない。出力可否と申告点計算可否を分離し、値不明を通常1点と決めつけない。自局GL欠損も距離0扱いしない。
原本のFT4/FT8と送受レポートはそのまま、提出時だけDG行へ変換。ALL/SINGLE出力範囲と得点範囲を分離する。
公開前残件：ZZ00の具体的採点、距離計算境界、締切文の不整合。現状ユーザーへの追加質問はなしだが「全仕様確定」とはしない。

## PSLOG101 残り9目標・途中実装記録 ww-digi

28種目。GL4中心間距離点/GL2マルチ・FT4/FT8共通重複・系列別毎時8変更。ZZ00は総得点未確定でCLAIMED-SCORE省略。Cabrillo3・全帯保持。 全体533試験合格。原ログ11列・原案・原典不変。主催受付とWindows実機未検証。
