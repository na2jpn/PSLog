# zLog令和版コンテストCSVの列対応

参照コミット：a078794a53df62d9fed756ebd4e205be372597ed、2026-09-11確認。

| 列 | 現行ヘッダー | PSLogからの内容 |
| --- | --- | --- |
| 1 | Date | 選択時刻基準のyyyy/mm/dd |
| 2 | Time | HH:MM:SS（PSログの秒は00） |
| 3 | TimeZone | JSTまたはUTC |
| 4 | CallSign | 相手コール |
| 5 | RSTSent | 補完値または元の送信RSTを整数化 |
| 6 | NrSent | 送信番号（電力分離ONなら末尾コードを除く） |
| 7 | RSTRcvd | 補完値または元の受信RSTを整数化 |
| 8 | NrRcvd | 受信番号 |
| 9 | Serial | 出力順1起点、交換番号とは別 |
| 10 | Mode | 対応表にあるzLog MODE |
| 11 | Band | 対応表のMHzString |
| 12 | Power | 指定のP/L/M/H、または分離した送信コード |
| 13 | Multi1 | 抽出した第一マルチ |
| 14 | Multi2 | 空欄、zLog側で再計算 |
| 15 | NewMulti1 | PSLogのマルチ区分で初出ならTrue |
| 16 | NewMulti2 | False |
| 17 | Points | 確定交信得点、整数のみ |
| 18 | Operator | 入力された運用者 |
| 19 | Memo | 任意で元のRMKS |
| 20 | CQ | False（元ログから判定しない） |
| 21 | Dupe | PSLogの重複判定結果 |
| 22 | Reserve | 0 |
| 23 | TX | 補完した0/1、未設定0 |
| 24 | Power2 | 0（数値電力を推定しない） |
| 25 | Reserve2 | 0 |
| 26 | Reserve3 | 0 |
| 27 | Freq | 補完した実周波数、kHz。未設定空欄 |
| 28 | QsyViolation | False |
| 29 | PCName | 空欄 |
| 30 | Forced | False |
| 31 | QslState | 0（RMKSのQSL状態を推測しない） |
| 32 | Invalid | False |
| 33 | Area | 空欄（確認した読込処理も未代入） |
| 34 | RBN Verified | False |

標準CSV引用符で全フィールドを囲みます。zLogは先頭行をヘッダーとして飛ばし、時刻基準は先頭データ行を使います。全行を同一基準にしています。zLog側で同一QSOと判定された行は重複排除される場合があります。

標準対応MODEはCW/SSB/FM/AM/RTTY/FT4/FT8/DV等。PSLogのFT8 ASなどは勝手に別MODEへ縮退させず停止します。未知MODEを主ログへ記録する機能は制限しません。10000MHzはzLogの10.1G/10.4Gを特定できないため本版では停止します。

[公式保存・読込実装](https://github.com/jr8ppg/zLog/blob/a078794a53df62d9fed756ebd4e205be372597ed/zlog/UzLogQSO.pas)・[公式MODE/BAND表](https://github.com/jr8ppg/zLog/blob/a078794a53df62d9fed756ebd4e205be372597ed/zlog/UzlogConst.pas)。実機相互運用は未検証です。
