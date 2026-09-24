# ADIF QSL出力（1.00）

通常のADI・ADX出力で、RMKSの独立したQSL記号を大文字小文字を区別せず判定します。COMMENT（日本語ADXはCOMMENT_INTL）にはRMKS全体をそのまま保持します。原本の変更はありません。

| RMKS記号 | 追加するADIF項目 |
| --- | --- |
| LoTW.R | LOTW_QSL_SENT=Y、LOTW_QSL_RCVD=Y |
| eQSL | EQSL_QSL_SENT=Y |
| eQSL.R | EQSL_QSL_SENT=Y、EQSL_QSL_RCVD=Y |
| LoTW | 追加なし（約束だけではアップロード済みか分からない） |

複数サービスはそれぞれ出力します。LoTW.R/eQSL.Rの送信済み判定は、PSLogで決定した「相互Confirm」の意味に基づきます。

hQSL、QRZ、Otherや紙カード系記号は今回の標準項目変換対象外で、COMMENTに保持します。一般のQSL_RCVDに電子確認を混ぜません。記号がない場合も明示的なNを生成せず、送受領日やアワードの審査済み状態を推定しません。ADIFの既定値や受け入れ先の動作によって、省略項目が未受領として表示される可能性はあります。

参考: ADIF 3.1.4（2022-12-06更新、2026-09-11確認）
https://adif.org/314/ADIF_314.htm
対象定義: LOTW_QSL_SENT / LOTW_QSL_RCVD / EQSL_QSL_SENT / EQSL_QSL_RCVD。
ADIF全体の最新版への移行を行った変更ではありません。

この変更は出力側です。標準QSL項目からPSLog記号への逆変換は未実装です。従来のADIF_EXTRAによる追加項目保持とは別の課題です。


2026-09-11: ADIF QSL取り込み更新
LoTW/eQSL標準項目の限定的な逆変換を実装。送信・受領が両方Yの場合に.R化、eQSL送信済みはeQSLへ。元項目保持、矛盾時の確認表示。詳細ADIF_QSL_IMPORT.md。上記の逆変換未実装との記載は本更新で部分的に解消。紙カード系・受領情報のみの自動判定等は対象外。Linuxオフスクリーン184テスト成功、Windows EXE・実機未検証。


紙カードADIF出力更新: BURO/CARD/my1wayの発送、BURO.R/CARD.R/1way.R/Direct.Rの受領を標準項目へ反映。受領だけでは発送済みとしない。従来の紙カード出力対象外という記載を本更新で置き換える。詳細ADIF_PAPER_QSL.md。200テスト成功、Windows実機未検証。
