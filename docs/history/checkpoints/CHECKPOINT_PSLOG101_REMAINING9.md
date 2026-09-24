# PSLOG101 定義上残り9・保存版

2026-09-15。依頼「定義残り9まで」の到達版です。アプリはPSLog 1.01のままです。
**開始28 → 今回19項目追加 → 残り9 / 87管理項目（定義あり78）。** 今回448競技種目。
管理項目数を実装工程数、ファイル数、全製品の残作業数とは混同しません。
全体533自動試験合格（Linux / Qt offscreen）。実行ルール作成済みは主催審査・全規約解釈の確認完了を意味しません。

## 再開入口

- 全ソース: pslog-1.01/。起動・Windowsビルドの案内は既存README.md、WINDOWS_BUILD.md。
- 現在の台帳: docs/CONTEST_IMPLEMENTATION_TRACKER.json。
- 原案の累積まとめ: docs/CONTEST_RESEARCH_ALL.md（別添MDも同内容）。
- 元の原案・利用者の確定事項: docs/contest-research/。末尾の利用者確定を優先。
- 取得した原典: docs/contest-research/sources/。出典・保存版・SHAはまとめに収録。
- 追加実装詳細と境界: docs/PSLOG101_REMAINING9_NOTES.md。
- 生成コード: devtools/build_remaining9.py / build_last6.py。
- 追加試験: test_remaining9.py / test_last6.py。
- 最新試験結果・全ソースSHA: このZIPのhandoff/tests.log / MANIFEST.json。

## 今回の19管理項目

- all_saitama: 県内外28種目、相手通信方式を別入力してクロスモードの点と重複を電話扱い。市区町村72コードは保存原典から抽出。JARL R1.0/R2.1出力。
- cq-vhf-ssbcw: 12種目、GL4・Roverグリッド別の重複/マルチ、レポートなしCabrillo3。相手Roverは/R表記を必要とする。
- cq-vhf-digi: 12種目、GL4・Rover・レポートなしCabrillo3。FT4/FT8/MSK144/Q65対応、他のデジタル型式は追加検証待ち。
- cq-160-cw: 6種目、米州・加14地域・CQカントリーを分離、2/5/10点とMM5点マルチなし。Cabrillo3実周波数、SO30h/MO40h・休止30分。
- cq-160-ssb: CWと別日程・RS/PH、6種目。CQゾーンはマルチなし。CQ専用カントリー欄は実運用地を手動確認。
- nara_vuhf: 24種目、バンド別2窓、末尾英字と開局年の独立積、最大5単帯排他、専用Multi1/Multi2実値列。公式2026PDFのNX28を画像照合。
- kyoto: 32種目、8時間窓、地域＋3桁番号を独立加算しニューカマー係数を最後に切上げ。単帯2又はマルチ1、R1.0マルチ欄も整数和。
- cq-ww-cw: 保存規約による全種目・CQカントリー別得点と独立マルチ・Cabrillo出力・Overlay資格と別集計を試験済み。
- cq-ww-ssb: 保存規約による全種目・CQカントリー別得点と独立マルチ・Cabrillo出力・Overlay資格と別集計を試験済み。
- cq-ww-rtty: 保存規約による全種目・CQカントリー別得点と独立マルチ・Cabrillo出力・Overlay資格と別集計を試験済み。
- cq-wpx-cw: 保存規約による全種目・CQカントリー別得点と独立マルチ・Cabrillo出力・Overlay資格と別集計を試験済み。
- cq-wpx-ssb: 保存規約による全種目・CQカントリー別得点と独立マルチ・Cabrillo出力・Overlay資格と別集計を試験済み。
- cq-wpx-rtty: 保存規約による全種目・CQカントリー別得点と独立マルチ・Cabrillo出力・Overlay資格と別集計を試験済み。
- all_asian_dx_cw: 2026 CW22種目。AS entity/非AS WPX・帯域別点・MM例外、最初24運用時間・MS系列別10分/新マルチ、UTC Cabrillo3と全帯出力。
- all_asian_dx_phone: 2026 Phone22種目。CWと独立日程、実RS・年齢交換、SOJR/SOSV資格、CONTEST=AADX-SSB。
- jarl_world_wide_rtty: 2026の5種目。大陸2/3点、JA/K/VE/VK本土コールエリアと島嶼entity、MM2点/マルチなし、年齢代替とYOUTH、JARL R1.0/R2.1 UTC。Cabrillo専用テンプレートは未対応。
- ww-digi: 28種目。GL4中心間距離点/GL2マルチ・FT4/FT8共通重複・系列別毎時8変更。ZZ00は総得点未確定でCLAIMED-SCORE省略。Cabrillo3・全帯保持。
- all_okayama_ft: 12種目L/H/V。レポートなしGL4、FT4/FT8共通重複、QRP5W、部門別出力。公式案内WSJT-XのWW-DIGI形式でCabrillo3 UTCを生成し専用フォームで部門選択。受付パーサーはサーバー側のため独立検証未了。
- miyazaki: 29種目。利用者確定の県人国外1点/マルチなし、県内国外6大陸、市郡KJ統合、手動重複採用、新人と混合最低条件、JARL本文1MB。MKJの追加モード構成は原典未明示のため独自条件なし。

## 残る9管理項目

- 11 島根対全日本 (`shimane`)
- 18 胆振日高支部 (`iburi_hidaka`)
- 45 KCWA CW (`kcwa_cw`)
- 47 QSOパーティ (`qso_party`)
- 48 オール兵庫 (`all_hyogo`)
- 49 富山県非常無線通信訓練 (`toyama_emergency`)
- 55 広島WAS (`hiroshima_was`)
- 65 静岡 (`shizuoka`)
- 73 新潟県支部大会記念コンテスト (`niigata_branch`)

No.73新潟支部は同一性未確認のまま保持。QSOパーティを後回しにする方針も維持。
広島WASは調査原案を残し、今回の定義数には含めていません。

## 保全と復元

旧PSLOG100に相当する原案・取得原典を削除せず、PSLOG101へ累積継承しています。
原本TXTは11列、JST、UTF-8 BOM/CRLFを維持し、提出用追加情報だけ別管理。交換しなかったレポートを作りません。
原始版557ファイル、残り50版639ファイル、正常な残り28途中版709ファイルの全パス存在と取得原典バイト一致を照合しました。
破損した残り28最終ZIPから回収できた665個の完全なファイルも同様に照合しました。

PSLOG101_remaining28.zipは保存済みの再取得でもZIP終端欠損があり、復元元にしてはいけません。
正常な途中保存版と回収内容から復旧しました。大きいZIPでは再作成時にも欠損が再現したため、旧ZIPを入れ子にせず全ソースと資料を直接収める構成に変更しました。
残り25・残り15の保存版は再取得CRC/全体SHA一致を確認済みです。今回の最終版も保存後に同じ確認を行います。
旧の正常な原始ZIPは以前の保存物として保持され、このZIPにはその全ソース・原案が継承されています。

## 残る検証範囲

Windows実機・EXE作成・主催者受付は未検証。大会定義や提出形式の初期対応範囲、保存年、手動申告が必要な境界は原案と台帳を参照してください。
CQ WW CW/SSBは確認済み2025規約の保存版で、2026開催版として作っていません。その他今回追加は明示された2026版です。
岡山FTは公式のWSJT-X WW-DIGI形式に従うローカル生成試験済みですが、専用フォームのサーバー内パーサー受入は未検証です。
JARL RTTYはJARL電子形式を実装し、識別子未確認のCabrilloを推測生成しません。
