# HAMLOG CSV出力 1.00

15列・ヘッダーなし・全項目引用符付き・CP932・CRLF。
列順: Call, Date, Time, His, My, Freq, Mode, Code, GL, QSL, Name, QTH, Remarks1, Remarks2, Flags。
日付はYYYY/MM/DD、時刻はJST末尾J。FreqはPSLogのBAND値であり実周波数ではない。

## 今回追加
Nameは明確なOP:から補完する。OP:Taro、OP:Taro BURO.R、OP:"Taro Yamada"など。
複数OPや自由メモとの境界が曖昧な場合は空欄と注意表示。複数語名は引用符で囲む。
ADIF_EXTRA/HAMLOG_EXTRA以降を名前抽出対象にしない。名前をRMKSから削除しない。
初期幅超過は既存の警告、最大幅超過・CP932非対応文字は切り捨てず停止する。

QSLは経由先/発行/受領の3文字。空白位置を保持し、発行・受領の肯定は*。
BUROは「B* 」/ BURO.Rは「B *」/ 両方明示は「B**」。
CARDは「 * 」/ CARD.Rと1way.Rは「  *」/ Direct.Rは「D *」。
Directリクエストだけ、電子サービス確認だけでは紙カード欄を設定しない。
送受領経路が競合する場合は経由先を空白にし、注意を表示する。
発行しないことを意味するNや、HAMLOG利用者が設定するWkd/Cfm除外文字は自動生成しない。
したがって電子QSLだけの交信の紙カード印刷方針は、利用者がHAMLOG側で確認する。

Remarks1はRMKS原文、Remarks2はMYCALL/MYQTH。Flagsは空欄。
QSL欄の空白位置はPSLogへ再取り込みする際もHAMLOG_EXTRAへ保持する。
NameがRemarks1の明確なOP:と同じなら、再取り込み時に重複するOP:を足さない。
MYQTHのRemarks2からの自動復元やHAMLOGの任意QSL文字の意味推定は対象外。

参考（2026-09-12確認）:
https://hamlog.xii.jp/html/HID00042.html
https://hamlog.xii.jp/html/HID00041.html
QSL欄は3バイトで後ろ2桁は記入の有無で判断される。経路のB/Dと確認の*はPSLogの出力規約。

検証: Linux Qt offscreen全207テスト成功。合成CSVの列位置、文字コード、名前、紙/電子分離、再取り込み。
HAMLOG実機での15列・幅設定・QSL運用との互換性は未検証。ユーザーが利用開始後に確認し、不具合があれば修正する合意。
