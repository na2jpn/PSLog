# CQ WW RTTY（2026）調査

<!-- CURRENT_IMPLEMENTATION_STATUS_START -->
> **現在の実装状態（Ver1.02 文書整理 / 2026-09-16）: 実装済み**
>
> - CQ WW RTTY (`cq-ww-rtty`, 2026)
>   - 実行定義: `config/rules/cq-ww-rtty_2026.txt`
>   - 現行監査: 保存規約による全種目・CQカントリー別得点と独立マルチ・Cabrillo出力・Overlay資格と別集計を試験済み。 主催受付・Windows実機未検証。
> - PSLOG101最終監査: **定義済み87 / 未定義0、全体回帰554件合格**。
> - Ver1.01正本はWindows上の全unittestがOKになった状態で受領済み。大会ごとのWindows実機操作・EXE・主催者受付確認は、監査記載どおり別確認です。
>
> **この下に残る「未実装」「未検証」「本体未対応」等は、調査・設計開始時点の履歴です。現在状態の判定には使用しません。**
> 現在状態はこの欄と [`docs/IMPLEMENTATION_STATUS.md`](../IMPLEMENTATION_STATUS.md)、および現行コード・回帰テストを優先してください。
<!-- CURRENT_IMPLEMENTATION_STATUS_END -->
出典：https://cqwwrtty.com/rules.htm
形式：https://cqwwrtty.com/cabrillo.htm
保存：sources/cqww_rtty_rules_2026.html・txt、cqww_rtty_cabrillo.html・txt。
状態：規約調査済、未実装。共通実装メモも参照。

## 規約要点
9月26–27日UTC00:00:00～23:59:59。3.5/7/14/21/28MHz。交換はRST＋CQゾーン、米本土・カナダは地域も送る。異大陸3点、同大陸異国2点、同国1点。
各バンドのzone＋country＋W/VE QTH数を合計し交信点に掛ける。米48州＋DC、カナダ14区域。Alaska/Hawaiiは州マルチにならない。/MMはゾーンのみ。カントリー基準はDXCC/WAE/IG9・IH9等。
SOの出力・Assisted・バンド区分、Classic/Rookie/YouthとMOのSingle/Two/Multi/Distributedを持つ。Multi-SingleはRUN/MULT各時計時の8変更までで、10分制ではない。MULTは別バンドの新マルチのみ。Twoも各毎時8変更。CLASSICは24時間、60分以上休止。
45.45baud、170Hz shift、ITA2。単一バンド提出にも他バンド交信を含む。Web提出のみ、48時間以内、9月29日23:59UTC締切。

## Cabrillo
CONTEST=CQ-WW-RTTY、CATEGORY-MODE=RTTY、QSO行=RY。3.0推奨、2.0も受付。送受各々RST＋ゾーン＋地域の2交換欄。米加以外は地域欄DX。地域コードの欠損を無条件DXに置換しない。カナダの規約表はNB NS QC ON MB SK AB BC NWT NF LB NU YT PEI。現代の郵便表記に勝手に統一しない。
Multi-One/Twoは送信機番号0/1。X-QSOと通常のQSOを分ける。日本運用のLOCATIONはDX。フォームでは住所所在地と実際の運用地を混同しない。YOUTH/Distributed等の規約と形式案内の更新差は共通メモに記録。

その他の一般条件・クラブ・録音・主催審査条項は保存本文を参照。完成テンプレート公開前に全条項との突合が必要。

## PSLOG101 残り9目標・途中実装記録 cq-ww-rtty

保存規約による全種目・CQカントリー別得点と独立マルチ・Cabrillo出力・Overlay資格と別集計を試験済み。 全体525試験合格。原ログ11列・原案・原典不変。主催受付とWindows実機未検証。
