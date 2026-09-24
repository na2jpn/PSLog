# 紙カードのADIF出力（1.00）

| RMKS | 標準項目 |
| --- | --- |
| BURO | QSL_SENT=Y / QSL_SENT_VIA=B |
| CARD または my1way | QSL_SENT=Y |
| BURO.R | QSL_RCVD=Y / QSL_RCVD_VIA=B |
| Direct.R | QSL_RCVD=Y / QSL_RCVD_VIA=D |
| CARD.R または 1way.R | QSL_RCVD=Y |
| Direct、1way | 今回は標準項目を追加しない |

BURO.Rは一括受領処理で未発送でも付与されうるため、単独ではQSL_SENTを出さない。
明示的なBURO/CARD/my1wayが残っている場合だけ発送済みを出す。
受領・発送日、未受領、発送不要、アワード審査済みは推定しない。

BURO.RとDirect.Rの併用では受領経路を一つにできないため経路項目を省略し注意を表示する。
CARD.Rは補助記号として扱い、BURO.RまたはDirect.Rの経路を妨げない。
BUROとCARD/my1way併用時は発送経路を省略する。

RMKS全文はCOMMENTに保持。電子サービスの確認を一般の紙カード項目へ混ぜない。
ADI/ADX共通。POTA提出ファイルは従来どおり提出用項目だけを出力し、これらのQSL項目は含めない。
取り込みの紙カード記号への逆変換は未実装。標準項目はADIF_EXTRAに保持する。

参照: ADIF 3.1.7 QSL Sent / QSL Rcvd / QSL Via
https://adif.org/317/ADIF_317.htm
今回のPSLog記号への対応はユーザーと合意した意味に基づく。
検証: 200テスト成功（Linux Qt offscreen）。Windows実機未検証。


2026-09-12: ビューロ標準項目の取り込みを実装。経路Bかつ状態YをBURO/BURO.Rへ反映し、元項目保持。発送不明は返送要否の確認、曖昧な経路は推測変換しない。従来の紙カード逆変換未実装の記載を部分的に更新。詳細ADIF_BUREAU_IMPORT.md。204テスト成功、Windows実機未検証。
