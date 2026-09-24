# 通常エクスポート 1.00 開発版

2026-09-11。出力互換性の完成宣言ではない。

## 共通の実装判断

自局候補は部分一致で検索、ログは明示チェック。日時はJSTの14桁、秒00として元ログを比較し両端を含む。最新N件は範囲適用後に選ぶ。出力順は日時・絶対パス・原本行番号の昇順。同一時刻の最新N件ではこの順の末尾を選ぶ。選択ログの問題行は黙って除外せず出力を停止。

出力名はPSLog_自局_処理日時.拡張子。複数自局はmulti。重複名には_001以降を付ける。原本スナップショットを再確認し、新規ファイルのみ排他的に作成する。

## ADIF

[ADIF 3.1.4仕様](https://adif.org/314/ADIF_314.htm)を今回の実装基準とした。最新仕様全体の実装ではない。

| 原本 | 出力 |
| --- | --- |
| DATE・TIME JST | UTCへ9時間戻してQSO_DATE・TIME_ON |
| CALL・ファイル由来の自局 | CALL・STATION_CALLSIGN |
| BAND | 明示対応表のBAND。実周波数FREQは作らない |
| FT4 | MODE=MFSK、SUBMODE=FT4 |
| FreeDV | MODE=DIGITALVOICE、SUBMODE=FREEDV |
| HIS QTH・RMKS | QTH・COMMENT。日本語ADXでは各_INTL |
| MY QTH・JCCJCG・元MODE・元BAND | PSLOG独自APP項目で保持 |

ADIはASCIIのみ。日本語を含む場合は停止してADXを案内する。ADXはUTF-8 XML。正確にGLのみのHIS QTHはGRIDSQUAREにも出す。未知・未対応MODEやBANDは原本入力を禁止せず、出力時に停止する。FT2は今回のADIF対応表未登録。QSLマークはRMKSに保持し、送受状態フラグへ自動変換しない。PSLOG独自項目は他ソフトで無視され得る。ADXスキーマ検証と他ソフトでの再読込は未実施。

## HAMLOG CSV（暫定）

[公式インポート説明](https://hamlog.xii.jp/html/HID00079.html)でCSV引用符・レコード番号の扱いを確認。[公式項目幅説明](https://hamlog.xii.jp/html/HID00035.html)に従い、初期幅超過を警告、最大幅超過は切り捨てず停止する。

列順・末尾フラグ・CP932・日付書式は今回の暫定マッピングであり、公式説明のみで全列の互換性を確定したものではない。HAMLOG実機のCSV往復試験が必要。出力画面でも毎回確認を求める。

| 列 | 値 |
| --- | --- |
| 1–3 | 相手コール、YYYY/MM/DD、hh:mmJ |
| 4–7 | 送信RST、受信RST、原本BAND、MODE |
| 8–10 | JCCJCG、GLのみと識別できた所在地、空のQSL欄 |
| 11–12 | 空のName欄、HIS QTH |
| 13–15 | RMKS、MYCALL:自局 MYQTH:当該交信のMY QTH、空のフラグ |

ヘッダー・レコード番号なし、15列、全項目を引用符で囲み、CP932・CRLF。RMKS中のOPなどはまだ自動抽出しない。原本BANDは実周波数とは限らないことを警告する。文字化けする文字は置換せず停止。QSL情報の意味を勝手に推定しない。
