# CQ WPX SSB・CW・RTTY（2026）

<!-- CURRENT_IMPLEMENTATION_STATUS_START -->
> **現在の実装状態（Ver1.02 文書整理 / 2026-09-16）: 実装済み**
>
> - CQ WPX SSB (`cq-wpx-ssb`, 2026)
>   - 実行定義: `config/rules/cq-wpx-ssb_2026.txt`
>   - 現行監査: 保存規約による全種目・CQカントリー別得点と独立マルチ・Cabrillo出力・Overlay資格と別集計を試験済み。 主催受付・Windows実機未検証。
> - CQ WPX CW (`cq-wpx-cw`, 2026)
>   - 実行定義: `config/rules/cq-wpx-cw_2026.txt`
>   - 現行監査: 保存規約による全種目・CQカントリー別得点と独立マルチ・Cabrillo出力・Overlay資格と別集計を試験済み。 主催受付・Windows実機未検証。
> - CQ WPX RTTY (`cq-wpx-rtty`, 2026)
>   - 実行定義: `config/rules/cq-wpx-rtty_2026.txt`
>   - 現行監査: 保存規約による全種目・CQカントリー別得点と独立マルチ・Cabrillo出力・Overlay資格と別集計を試験済み。 主催受付・Windows実機未検証。
> - PSLOG101最終監査: **定義済み87 / 未定義0、全体回帰554件合格**。
> - Ver1.01正本はWindows上の全unittestがOKになった状態で受領済み。大会ごとのWindows実機操作・EXE・主催者受付確認は、監査記載どおり別確認です。
>
> **この下に残る「未実装」「未検証」「本体未対応」等は、調査・設計開始時点の履歴です。現在状態の判定には使用しません。**
> 現在状態はこの欄と [`docs/IMPLEMENTATION_STATUS.md`](../IMPLEMENTATION_STATUS.md)、および現行コード・回帰テストを優先してください。
<!-- CURRENT_IMPLEMENTATION_STATUS_END -->
調査台帳登録済・本体／実行用定義は未実装。確認日2026-09-14。
資料：https://cqwpx.com/rules/ 、https://cqwpxrtty.com/rules.htm
形式：https://cqwpx.com/cabrillo.htm 、https://cqwpxrtty.com/cabrillo.htm
保存本文はsources/wpx*。主催はCQ WPX Contest Committee／CQ WPX RTTY Contest Committee。

## 規約の中核
RS(T)＋001開始連番。各相手はバンドごと1回得点、プリフィックスは全バンド通算で1回。得点合計×プリフィックス数。
SSB/CW：1.8～28の6バンド、SO36/48時間。RTTY：3.5～28の5バンド、SO30/48時間。休止最低60分、MO48時間。
ハイ=14/21/28、ロー=残り。SSB/CW：異大陸3/6、同大陸異国1/2（北米内2/4）、同国1/1。RTTY：異大陸3/6、同大陸異国2/4、同国1/2。
Multi-Oneは共通連番・毎時10変更。Twoはバンド別連番・送信機別毎時8変更。Unlimited/Distributedもバンド別連番。Classicを除き補助使用可。SO出力1500/100/5W。OverlayはTB-WIRES、Rookie、Classic、Youth。
2026本文のCW5/30–31、RTTY2/14–15。SSB3/28–29だが本文年が2025と誤記疑い。締切はSSB3/31、CW6/2、RTTY2/17各23:59UTC。

## プリフィックス・出力
HG19、LY1000等を短縮しない。移動指定を優先、数字なし指定は規則により0を補う（PA/N8BJQ→PA0、XEFTJW→XE0）。/P等を独立マルチにしない。
CONTESTはCQ-WPX-SSB/CW/RTTY、年度なし。QSOモードPH/CW/RY。実送受信連番を出力し、絞込・並べ替え後に再採番しない。Multi-Twoは0/1送信機識別。単一バンド提出でも他バンド交信保持。RTTY形式説明は時系列順、OPERATORSはスペース区切り。

## 設計・残件
- 現行の全バンドmulti1集計は再利用候補だが、コールからWPXプリフィックスを得る例外処理と版付きテストが必要。国判定用prefixと別フィールド。
- 自局／相手国・大陸とバンドを比較する条件。片側のcontinentだけでは一般の運用地に対応できない。
- 送信機別とバンド別の連番系列を混同しない。欠番を埋めず、実際の送信値優先。
- SSB/CW規約SSB年の誤記疑いは台帳2026・本文2025の差として保存。実行時日付確定前に公式日程/PDFと照合。
- RTTY形式説明にQRP欠落、SWL残存、Distributedキー誤記疑い。規約優先、SWL追加しない。ヘッダーの正式マッピングは公開前検証。
- Rookieは3年以下。CQWWの3年未満と同一条件にしない。
- 一般条件・採点外審査条項も公開前に保存原文と突合する。現時点で完成ルールとしない。

## PSLOG101 残り9目標・途中実装記録 cq-wpx-ssb

保存規約による全種目・CQカントリー別得点と独立マルチ・Cabrillo出力・Overlay資格と別集計を試験済み。 全体525試験合格。原ログ11列・原案・原典不変。主催受付とWindows実機未検証。

## PSLOG101 残り9目標・途中実装記録 cq-wpx-cw

保存規約による全種目・CQカントリー別得点と独立マルチ・Cabrillo出力・Overlay資格と別集計を試験済み。 全体525試験合格。原ログ11列・原案・原典不変。主催受付とWindows実機未検証。

## PSLOG101 残り9目標・途中実装記録 cq-wpx-rtty

保存規約による全種目・CQカントリー別得点と独立マルチ・Cabrillo出力・Overlay資格と別集計を試験済み。 全体525試験合格。原ログ11列・原案・原典不変。主催受付とWindows実機未検証。
