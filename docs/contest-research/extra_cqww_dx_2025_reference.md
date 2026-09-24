# CQ WW DX SSB / CW（2025）調査

<!-- CURRENT_IMPLEMENTATION_STATUS_START -->
> **現在の実装状態（Ver1.02 文書整理 / 2026-09-16）: 実装済み**
>
> - CQ WW DX SSB (`cq-ww-ssb`, 2025)
>   - 実行定義: `config/rules/cq-ww-ssb_2025.txt`
>   - 現行監査: 当面2025採用で利用者確定。
> - CQ WW DX CW (`cq-ww-cw`, 2025)
>   - 実行定義: `config/rules/cq-ww-cw_2025.txt`
>   - 現行監査: 当面2025採用で利用者確定。
> - PSLOG101最終監査: **定義済み87 / 未定義0、全体回帰554件合格**。
> - Ver1.01正本はWindows上の全unittestがOKになった状態で受領済み。大会ごとのWindows実機操作・EXE・主催者受付確認は、監査記載どおり別確認です。
>
> **この下に残る「未実装」「未検証」「本体未対応」等は、調査・設計開始時点の履歴です。現在状態の判定には使用しません。**
> 現在状態はこの欄と [`docs/IMPLEMENTATION_STATUS.md`](../IMPLEMENTATION_STATUS.md)、および現行コード・回帰テストを優先してください。
<!-- CURRENT_IMPLEMENTATION_STATUS_END -->
出典：https://cqww.com/rules.htm
形式：https://cqww.com/cabrillo.htm
保存：sources/cqww_rules_2025.html・txt、cqww_cabrillo.html・txt。
状態：規約調査済、FAQ未取得、未実装。共通実装メモも参照。

## 規約要点
2025 SSB=10月25–26日、CW=11月29–30日、UTC各土曜00:00:00～日曜23:59:59。1.8/3.5/7/14/21/28MHz。交換はRS又はRST＋CQゾーン。
交信点は異大陸3、同大陸異国1（北米内異国2）、同国0。同国もマルチ対象。各バンドのゾーン数とカントリー数を足し、全交信点に掛ける。カントリーはDXCC/WAE/IG9・IH9等、/MMはゾーンのみ。
SOはAssisted有無、ALL/SINGLE、HIGH≤1500W/LOW≤100W/QRP≤5W。MOはMulti-Single（HIGH/LOW）、Two、Multi、Distributed。OverlayはClassic/Rookie/Youth。CLASSICは24時間、休止60分以上。Multi-SingleはRUN/MULTそれぞれ10分、MULTは別バンド新マルチのみ。Twoは送信機ごと毎時8変更。
単一バンド提出にも他バンド交信を含める。Web提出、終了後5日以内。2025締切SSB10/31、CW12/5、各23:59UTC。

## Cabrillo
CONTEST=CQ-WW-SSB又はCQ-WW-CW、年度は付けない。3.0を採用し、2.0は非推奨だが受付可。ヘッダーのSSBとQSO行PHを区別。CW行はCW。RS/RSTとゾーンを送受それぞれ出す。Multi-One/Twoの送信機欄は0/1。スペース区切りで列揃え必須ではない。X-QSOは自局採点対象外だが相手に信用を与える行。通常の0点QSOを自動でX-QSOへ変えない。
住所、氏名、OPERATORS、CLUB、各CATEGORYを専用項目から出力。MOのOPERATORS欠落を確認。本文と形式説明のLOCATION差は共通メモに記録。

その他の一般運用条件・クラブ・録音・主催審査条項は保存した本文を参照。完成テンプレートを公開する前に全条項との突合が必要。

## PSLOG101 残り9目標・途中実装記録 cq-ww-ssb

保存規約による全種目・CQカントリー別得点と独立マルチ・Cabrillo出力・Overlay資格と別集計を試験済み。 全体525試験合格。原ログ11列・原案・原典不変。主催受付とWindows実機未検証。

## PSLOG101 残り9目標・途中実装記録 cq-ww-cw

保存規約による全種目・CQカントリー別得点と独立マルチ・Cabrillo出力・Overlay資格と別集計を試験済み。 全体525試験合格。原ログ11列・原案・原典不変。主催受付とWindows実機未検証。
