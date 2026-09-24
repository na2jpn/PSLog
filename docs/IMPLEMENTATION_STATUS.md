# PSLog Ver1.14 — 現在の実装状況

更新: **2026-09-25**（Ver1.14正本化。コンテスト86件＋QSOパーティ1件の87ルールを継承）

この文書は、調査メモに残る過去の「未実装」表記と現在の実装状態を混同しないための入口です。
現行状態を判断するときは **コード＋回帰テスト → この一覧 → 個別調査メモの現在状態欄 → 調査履歴** の順で参照します。

## 現在の結論

- 管理項目: **87 / 87 実装定義済み**、未定義 **0**。内訳はコンテスト86件＋QSOパーティ1件。
- Ver1.069までに87ルールの人間向け表示監査を完了し、CQ・交信対象・大区分出力制限・得点等の表示情報を整備。表示情報は提出拒否条件や採点条件を自動的に増やすものではない。
- Ver1.14はVer1.13までのフリラタブ・フリラ原本保存・横断LogSearch・専用検索編集を継承し、初回起動からフリラだけで開始できる切替を統合。
- アマチュアログは`logbook/`、フリラログは`logbook_flr/`として取得経路を分離。フリラタブは同時最大4枚。
- EASYタブは最大2枚で、標準PSLog原本を共用し別ログ形式を作らない。
- 同梱ルールの出自判定はソース実行とfrozen配布実行を区別して扱う。
- 2026-09-25、利用者がVer1.14初回起動差分をWindows側で問題なしと確認し、Ver1.14正本化を指示。
- 大会ごとの主催者受付・実提出受理等は、各項目の監査欄どおり別確認。
- 個別調査メモ本文中の古い「未実装」「未検証」等は調査時点の履歴で、現状を表さない場合がある。

## 状態の読み方

**実装済み**は、その管理項目に実行定義が存在し、現行監査で未定義扱いではないことを示します。
『主催者受付未検証』『Windows実機未検証』等は、実装の有無ではなく外部・実機での最終確認状態です。
規約に明記されない条件を勝手に補完しない方針もそのまま維持します。

## 管理項目一覧

|No.|ID|大会|現在状態|実行定義|実装・確認メモ|調査メモ|
|---:|---|---|---|---|---|---|
|1|`all_kanagawa`|オール神奈川|**実装済み**|`config/rules/all_kanagawa_2026.txt`|大会定義・全部門採点/出力の自動試験済み。原案の未記載事項、主催受付・Windows実機は別途確認。|`docs/contest-research/001_all_kanagawa_2026.md`|
|2|`miyazaki`|宮崎|**実装済み**|`config/rules/miyazaki_2026.txt`|29種目。利用者確定の県人国外1点/マルチなし、県内国外6大陸、市郡KJ統合、手動重複採用、新人と混合最低条件、JARL本文1MB。MKJの追加モード構成は原典未明示のため独自条件なし。 主催受付・Windows実機未検証。|`docs/contest-research/002_miyazaki_2026.md`|
|3|`ishikari`|石狩後志支部|**実装済み**|`config/rules/ishikari_2026.txt`|採点・全種目JARL出力の自動試験済み。01006は郡番号だけでは所属を断定せず、該当局・町村・後志所属の確認を追加申告。関連の過年度画像等は読了扱いにしない。 主催受付・Windows実機未検証。|`docs/contest-research/003_ishikari_2026.md`|
|4|`all_kushiro`|オール釧根|**実装済み**|`config/rules/all_kushiro_2026.txt`|全16部門・採点/出力試験済み。混合構成・全帯以外の最低帯数・提出本文/添付は原典未明示。主催受付・Windows実機未検証。|`docs/contest-research/004_all_kushiro_2026.md`|
|5|`yamagata_sakuranbo`|山形さくらんぼQSO|**実装済み**|`config/rules/yamagata_sakuranbo_2026.txt`|採点・全種目JARL出力の自動試験済み。通常全帯はHF2＋VU1。YCの同条件適用は原典未明示で独自強制しない。学年・YL・登録クラブは本人申告。 主催受付・Windows実機未検証。|`docs/contest-research/005_yamagata_sakuranbo_2026.md`|
|6|`all_gifu`|オール岐阜|**実装済み**|`config/rules/all_gifu_2026.txt`|添付PDF全4ページ画像照合済み。ジュニア担当数は本人申告、原ログ件数照合や80%判定で出力を止めない。|`docs/contest-research/006_all_gifu_2026.md`|
|7|`oita`|大分|**実装済み**|`config/rules/oita_2026.txt`|地域・県人資格は本人選択。判定根拠の記入を必須としない。|`docs/contest-research/007_oita_2026.md`|
|8|`yamanashi`|山梨|**実装済み**|`config/rules/yamanashi_2026.txt`|採点・全種目JARL出力の自動試験済み。県内外とも山梨1局以上。新人社団局の資格は原典未明示で参加根拠を申告。 主催受付・Windows実機未検証。|`docs/contest-research/008_yamanashi_2026.md`|
|9|`niigata_low_band`|新潟1.9/3.5MHz|**実装済み**|`config/rules/niigata_low_band_2026.txt`|No.9ローバンド独立選択・18種目。No.73とは別の実行定義。|`docs/contest-research/009_niigata_2026.md`|
|10|`all_asian_dx_cw`|ALL ASIAN DX (CW)|**実装済み**|`config/rules/all_asian_dx_cw_2026.txt`|2026 CW22種目。AS entity/非AS WPX・帯域別点・MM例外、最初24運用時間・MS系列別10分/新マルチ、UTC Cabrillo3と全帯出力。 主催受付・Windows実機未検証。|`docs/contest-research/010_026_all_asian_dx_2026.md`|
|11|`shimane`|島根対全日本|**実装済み**|`config/rules/shimane_2026.txt`|14部門、通常モード別重複、HF資格別最終1000加算、AJD最速10局と完成時刻別保持。 主催受付・Windows実機未検証。|`docs/contest-research/011_shimane_2026.md`|
|12|`all_ja8`|ALL JA8|**実装済み**|`config/rules/all_ja8_2026.txt`|採点・全種目JARL出力の自動試験済み。受信年代別得点・地域のみマルチ。R2.1のみ対応。MOのM/X等は実交換と原典を本人確認、年齢公開を推定しない。 主催受付・Windows実機未検証。|`docs/contest-research/012_all_ja8_2026.md`|
|13|`tochigi`|栃木|**実装済み**|`config/rules/tochigi_2026.txt`|大会定義・全部門採点/出力の自動試験済み。原案の未記載事項、主催受付・Windows実機は別途確認。|`docs/contest-research/013_tochigi_2026.md`|
|14|`six_meter_and_down`|6m AND DOWN|**実装済み**|`config/rules/six_meter_and_down_2026.txt`|北海道の親地域は本人確認。全体CHECKLOG・移動/ゲスト条件付き必須化は共通処理で対応済み。Windows実機・受付未検証|`docs/contest-research/014_six_meter_and_down_2026.md`|
|15|`okhotsk`|オホーツク|**実装済み**|`config/rules/okhotsk_2026.txt`|採点・全種目JARL出力の自動試験済み。2026第50回最終回を保存。2027へ継承しない。未記載の最低帯数・混合構成を加えない。 主催受付・Windows実機未検証。|`docs/contest-research/015_okhotsk_2026.md`|
|16|`all_ja5`|オールJA5|**実装済み**|`config/rules/all_ja5_2026.txt`|大会定義・全部門採点/出力の自動試験済み。原案の未記載事項、主催受付・Windows実機は別途確認。|`docs/contest-research/016_all_ja5_2026.md`|
|17|`shiga`|ALL滋賀|**実装済み**|`config/rules/shiga_2026.txt`|採点・全種目JARL出力の自動試験済み。管外同士も得点、滋賀交信バンド係数0を許容。3バンド選択/実績とスプリント窓。係数はFDCOEFFに出さない。 主催受付・Windows実機未検証。|`docs/contest-research/017_shiga_2026.md`|
|18|`iburi_hidaka`|胆振日高支部|**実装済み**|`config/rules/iburi_hidaka_2026.txt`|8部門、日本語コード/名称、自局常置と/8統合・地点別点/共通マルチ、OG/MT別集計。 主催受付・Windows実機未検証。|`docs/contest-research/018_iburi_hidaka_2026.md`|
|19|`all_aomori`|オール青森|**実装済み**|`config/rules/all_aomori_2026.txt`|大会定義・全部門採点/出力の自動試験済み。原案の未記載事項、主催受付・Windows実機は別途確認。|`docs/contest-research/019_all_aomori_2026.md`|
|20|`kagoshima`|鹿児島|**実装済み**|`config/rules/kagoshima_2026.txt`|大会定義・全部門採点/出力の自動試験済み。原案の未記載事項、主催受付・Windows実機は別途確認。|`docs/contest-research/020_kagoshima_2026.md`|
|21|`field_day`|フィールドデー|**実装済み**|`config/rules/field_day_2026.txt`|Windows実機/主催受付未検証。北海道の親地域・実設備等は本人確認。PN/CS/XSはR2.1のみ|`docs/contest-research/021_field_day_2026.md`|
|22|`nara_vuhf`|奈良県V・UHF|**実装済み**|`config/rules/nara_vuhf_2026.txt`|24種目、バンド別2窓、末尾英字と開局年の独立積、最大5単帯排他、専用Multi1/Multi2実値列。公式2026PDFのNX28を画像照合。 主催受付・Windows実機未検証。|`docs/contest-research/022_nara_vuhf_2026.md`|
|23|`ja9_vu`|JA9コンテストVU|**実装済み**|`config/rules/ja9_vu_2026.txt`|9種目。SM/MMは1200MHz以上の上限を10GHzへ制限しない。10.1/10.4はS10G対象。明示SM2帯・MM2OP条件は維持。|`docs/contest-research/023_ja9_vu_2026.md`|
|24|`kamikawa_souya`|上川宗谷支部|**実装済み**|`config/rules/kamikawa_souya_2026.txt`|大会定義・全部門採点/出力の自動試験済み。原案の未記載事項、主催受付・Windows実機は別途確認。|`docs/contest-research/024_kamikawa_soya_2026.md`|
|25|`all_saga`|オール佐賀コンテスト|**実装済み**|`config/rules/all_saga_2026.txt`|県内外42種目・番号80件・採点・JARL R1.0/R2.1出力・r1→r2更新試験済み。主催受付実機未検証。|`docs/contest-research/025_all_saga_2026.md`|
|26|`all_asian_dx_phone`|ALL ASIAN DX (PH)|**実装済み**|`config/rules/all_asian_dx_phone_2026.txt`|2026 Phone22種目。CWと独立日程、実RS・年齢交換、SOJR/SOSV資格、CONTEST=AADX-SSB。 主催受付・Windows実機未検証。|`docs/contest-research/010_026_all_asian_dx_2026.md`|
|27|`oshima_hiyama`|渡島檜山支部|**実装済み**|`config/rules/oshima_hiyama_2026.txt`|大会定義・全部門採点/出力の自動試験済み。原案の未記載事項、主催受付・Windows実機は別途確認。|`docs/contest-research/027_oshima_hiyama_2026.md`|
|28|`all_okayama_ft`|オール岡山FT8/FT4|**実装済み**|`config/rules/all_okayama_ft_2026.txt`|12種目L/H/V。レポートなしGL4、FT4/FT8共通重複、QRP5W、部門別出力。公式案内WSJT-XのWW-DIGI形式でCabrillo3 UTCを生成し専用フォームで部門選択。受付パーサーはサーバー側のため独立検証未了。 主催受付・Windows実機未検証。|`docs/contest-research/028_okayama_ft8_ft4_2026.md`|
|29|`gigahertz`|ギガヘルツ|**実装済み**|`config/rules/gigahertz_2026.txt`|Windows実機・主催受付は未検証。詳細はCHECKPOINT_PSLOG101_BATCH20_TOTTORI_GIGAHERTZ.md。最低帯数・休止中移動・複数提出・電子提出方法は確認事項を保持。|`docs/contest-research/029_gigahertz_2026.md`|
|30|`all_akita`|オール秋田|**実装済み**|`config/rules/all_akita_2026.txt`|原典の2種目上限・禁止3条件は維持。未明示の集合判定根拠を必須にしない。|`docs/contest-research/030_all_akita_2026.md`|
|31|`fukuoka`|福岡|**実装済み**|`config/rules/fukuoka_2026.txt`|Windows実機・主催者受付未検証。移動有無・免許範囲・全員コール・共通運用規程は本人確認。|`docs/contest-research/031_fukuoka_2026.md`|
|32|`all_okayama`|オール岡山|**実装済み**|`config/rules/all_okayama_2026.txt`|JARL R1.0を採用。Cabrillo追加は現版の範囲外。|`docs/contest-research/032_all_okayama_2026.md`|
|33|`xpo`|XPO記念|**実装済み**|`config/rules/xpo_2026.txt`|Windows実機・主催受付未検証。XPO全28種目。10GHz統合、全帯の構成条件、ゲストMO、2026記念局1点。実周波数・設備・運用人数等は本人確認。|`docs/contest-research/033_xpo_2026.md`|
|34|`ai_chikyu`|愛・地球博記念|**実装済み**|`config/rules/ai_chikyu_2026.txt`|Windows実機・主催受付未検証。受付再取得タイムアウト。全体の担当数は重複等含む開催中全行で照合、主催者の別解釈が示された場合は変更。実設備等は本人確認。|`docs/contest-research/034_ai_chikyuhaku_2026.md`|
|35|`all_ja_cg`|全市全郡|**実装済み**|`config/rules/all_ja_cg_2026.txt`|Windows実機・主催受付未検証。ACAG全80種目。市郡区・電力文字・全帯域送信地域を検査。PN/CS/XSはPSLogでR2.1のみ。|`docs/contest-research/035_all_city_county_2026.md`|
|36|`all_tottori`|オール鳥取|**実装済み**|`config/rules/all_tottori_2026.txt`|Windows実機・主催受付は未検証。詳細はCHECKPOINT_PSLOG101_BATCH20_TOTTORI_GIGAHERTZ.md。紙出力は未実装、電子R1.0/R2.1のみ。|`docs/contest-research/036_all_tottori_2026.md`|
|37|`jarl_world_wide_rtty`|JARL World Wide RTTY|**実装済み**|`config/rules/jarl_world_wide_rtty_2026.txt`|Cabrillo3追加、未指定ヘッダーは暫定編集可、MHz帯域出力。JARLも維持。公海MMは得点掲載・表彰外。|`docs/contest-research/037_jarl_ww_rtty_2026.md`|
|38|`all_chiba`|オール千葉|**実装済み**|`config/rules/all_chiba_2026.txt`|Windows実機・主催者受付未検証。実際の免許・初開局・全運用者の姓名と資格・運用条件は本人確認。|`docs/contest-research/038_all_chiba_2026.md`|
|39|`tokyo_cw`|東京CW|**実装済み**|`config/rules/tokyo_cw_2026.txt`|Windows実機・主催受付未検証。東京CW全18種目。局種は免許に基づく本人申告、ゲスト不可。相手社団は得点可。任意3賞の判定と申請文、R1.0のみ。|`docs/contest-research/039_tokyo_cw_2026.md`|
|40|`all_osaka`|オール大阪|**実装済み**|`config/rules/all_osaka_2026.txt`|Windows実機・主催者受付未検証。R1.0対応。R2.1受理は未確認。実際の同一運用地・資格・OP情報は本人申告。|`docs/contest-research/040_all_osaka_2026.md`|
|41|`ja9_hf_phone`|JA9コンテストHF (PH)|**実装済み**|`config/rules/ja9_hf_phone_2026.txt`|大会定義・全部門採点/出力の自動試験済み。原案の未記載事項、主催受付・Windows実機は別途確認。|`docs/contest-research/041_042_ja9_hf_2026.md`|
|42|`ja9_hf_cw`|JA9コンテストHF (CW)|**実装済み**|`config/rules/ja9_hf_cw_2026.txt`|大会定義・全部門採点/出力の自動試験済み。原案の未記載事項、主催受付・Windows実機は別途確認。|`docs/contest-research/041_042_ja9_hf_2026.md`|
|43|`all_kyushu`|オール九州|**実装済み**|`config/rules/all_kyushu_2026.txt`|大会定義・全部門採点/出力の自動試験済み。原案の未記載事項、主催受付・Windows実機は別途確認。|`docs/contest-research/043_all_kyushu_2026.md`|
|44|`tokyo_uhf`|東京UHF|**実装済み**|`config/rules/tokyo_uhf_2026.txt`|Windows実機・主催者受付未検証。免許・実運用条件は本人確認。東京UHFの曖昧10Gは作業用実バンド指定必須。春は2024改訂規約に基づく2026定義、2027変更未適用。|`docs/contest-research/044_tokyo_uhf_2026.md`|
|45|`kcwa_cw`|KCWA CW|**実装済み**|`config/rules/kcwa_cw_2025.txt`|2025が最新と利用者確認。現版採用、次年未発表を完成条件にしない。|`docs/contest-research/045_kcwa_2025_reference.md`|
|46|`all_ja0_160m`|ALL JA0 1.8MHz|**実装済み**|`config/rules/all_ja0_160m_2025.txt`|2025が最新と利用者確認。現版採用。|`docs/contest-research/046_all_ja0_18_2025_reference.md`|
|47|`qso_party`|QSOパーティ|**実装済み**|`config/rules/qso_party_2026.txt`|2026部門30、名前交換・20異局・数値点0・JARL電子ログ。 主催受付・Windows実機未検証。|`docs/contest-research/047_qso_party_deferred.md`|
|48|`all_hyogo`|オール兵庫|**実装済み**|`config/rules/all_hyogo_2026.txt`|54部門。国外と2701、2部門目CALLSIGN -2、帯域重複排他。 主催受付・Windows実機未検証。|`docs/contest-research/048_all_hyogo_2026_reference.md`|
|49|`toyama_emergency`|富山県非常無線通信訓練|**実装済み**|`config/rules/toyama_emergency_2026.txt`|11種目、自由交換/所在地別集計、支部様式PDF・赤枠・全帯資料・50局超チェック表。日本語フォントと画面操作を試験。 主催受付・Windows実機未検証。|`docs/contest-research/049_toyama_emergency_2026_reference.md`|
|50|`all_kumamoto`|オール熊本|**実装済み**|`config/rules/all_kumamoto_2026.txt`|大会定義・全部門採点/出力の自動試験済み。原案の未記載事項、主催受付・Windows実機は別途確認。|`docs/contest-research/050_all_kumamoto_2026_reference.md`|
|51|`all_saitama`|オール埼玉|**実装済み**|`config/rules/all_saitama_2026.txt`|県内外28種目、相手通信方式を別入力してクロスモードの点と重複を電話扱い。市区町村72コードは保存原典から抽出。JARL R1.0/R2.1出力。 主催受付・Windows実機未検証。|`docs/contest-research/051_all_saitama_2026_reference.md`|
|52|`all_miyagi`|オール宮城|**実装済み**|`config/rules/all_miyagi_2026.txt`|採点・全種目JARL出力の自動試験済み。通常単帯1＋1200UP1のみ例外併願。高帯域は実バンド別、終了12:59を含む。 主催受付・Windows実機未検証。|`docs/contest-research/052_all_miyagi_2026_reference.md`|
|53|`kyoto`|京都|**実装済み**|`config/rules/kyoto_2026.txt`|32種目、8時間窓、地域＋3桁番号を独立加算しニューカマー係数を最後に切上げ。単帯2又はマルチ1、R1.0マルチ欄も整数和。 主催受付・Windows実機未検証。|`docs/contest-research/053_kyoto_2026_reference.md`|
|54|`iwate_winter`|いわてWINTER|**実装済み**|`config/rules/iwate_winter_2026.txt`|大会定義・全部門採点/出力の自動試験済み。原案の未記載事項、主催受付・Windows実機は別途確認。|`docs/contest-research/054_iwate_winter_2026_reference.md`|
|55|`hiroshima_was`|広島WAS|**実装済み**|`config/rules/hiroshima_was_2026.txt`|25部門。帯域時間窓、実レポート、通信区分、2サマリーを1本文へ結合。 主催受付・Windows実機未検証。|`docs/contest-research/055_hiroshima_was_2026_reference.md`|
|56|`all_ja0_80m_40m`|ALL JA0 3.5MHz/7MHz|**実装済み**|`config/rules/all_ja0_35_2026.txt`<br>`config/rules/all_ja0_7_2026.txt`|採点・全種目JARL出力の自動試験済み。台帳1項目に対し3.5/7の別大会2ファイル。専用列順・別提出、相手ログ照合後の減点は未反映。 主催受付・Windows実機未検証。|`docs/contest-research/056_all_ja0_35_7_2026_reference.md`|
|57|`all_ja4`|オールJA4|**実装済み**|`config/rules/all_ja4_2026.txt`|大会定義・全部門採点/出力の自動試験済み。原案の未記載事項、主催受付・Windows実機は別途確認。|`docs/contest-research/057_all_ja4_2026_reference.md`|
|58|`tokai_qso`|東海QSO|**実装済み**|`config/rules/tokai_qso_2026.txt`|採点・全種目JARL出力の自動試験済み。担当割合と全QSO担当を照合。D-STAR直接通信・SPA4アマ・実出力/資格は本人確認。R1.0をWeb提出用に作成。 主催受付・Windows実機未検証。|`docs/contest-research/058_tokai_qso_2026_reference.md`|
|59|`nagasaki`|長崎県|**実装済み**|`config/rules/nagasaki_2026.txt`|締切曜日不一致は操作・提出を制限する残件から除外。|`docs/contest-research/059_nagasaki_2026_reference.md`|
|60|`kanagawa_emergency`|神奈川県非常通信訓練|**実装済み**|`config/rules/kanagawa_emergency_2026.txt`|採点・全種目JARL出力の自動試験済み。7桁郵便番号と県外市郡区を区別。未収録郵便番号は確認根拠入力で保持。AとHL/V/Uの実バンド条件、対象外も0点出力。 主催受付・Windows実機未検証。|`docs/contest-research/060_kanagawa_emergency_2026_reference.md`|
|61|`wakayama`|和歌山|**実装済み**|`config/rules/wakayama_2026.txt`|大会定義・全部門採点/出力の自動試験済み。原案の未記載事項、主催受付・Windows実機は別途確認。|`docs/contest-research/061_wakayama_2026_reference.md`|
|62|`all_tohoku`|オール東北|**実装済み**|`config/rules/all_tohoku_2026.txt`|大会定義・全部門採点/出力の自動試験済み。原案の未記載事項、主催受付・Windows実機は別途確認。|`docs/contest-research/062_all_tohoku_2026_reference.md`|
|63|`all_ja`|ALL JA|**実装済み**|`config/rules/all_ja_2026.txt`|Windows実機・主催受付未検証。PN/CS/XSはPSLogでR2.1のみ。|`docs/contest-research/063_all_ja_2026.md`|
|64|`tokyo`|東京|**実装済み**|`config/rules/tokyo_2026.txt`|現在の2026採用で利用者確定、次回2027発表待ちは将来更新。|`docs/contest-research/064_tokyo_2026_reference.md`|
|65|`shizuoka`|静岡|**実装済み**|`config/rules/shizuoka_2026.txt`|54部門。地域略符号、QRP全対象交信判定、10GHz共通、対象外帯域0点。 主催受付・Windows実機未検証。|`docs/contest-research/065_shizuoka_2026_reference.md`|
|66|`all_mie_33`|オール三重33|**実装済み**|`config/rules/all_mie_33_2026.txt`|採点・全種目JARL出力の自動試験済み。年齢/ME/MEJを分離し53種目。県人/JLとOP年齢の事実は申告、国外も対象。実交換年齢を生年月日で書換えない。 主催受付・Windows実機未検証。|`docs/contest-research/066_all_mie33_2026_reference.md`|
|67|`tsugaru_kaikyo`|津軽海峡|**実装済み**|`config/rules/tsugaru_kaikyo_2026.txt`|採点・全種目JARL出力の自動試験済み。3区域点と移動範囲を区別。任意採用は他候補を作業上のチェック行へ、元ログは消さない。 主催受付・Windows実機未検証。|`docs/contest-research/067_tsugarukaikyou_2026_reference.md`|
|68|`oidemase_yamaguchi_hf`|おいでませオール山口 (HF)|**実装済み**|`config/rules/oidemase_yamaguchi_2026.txt`|採点・全種目JARL出力の自動試験済み。No68/71は同じ実行定義を共有しOM/MOを一度だけ定義。両週の実バンド別窓・通常部門の交信再使用禁止・OM/MO排他。 主催受付・Windows実機未検証。|`docs/contest-research/068_071_all_yamaguchi_2026_reference.md`|
|69|`ja0_vhf`|JA0-VHF|**実装済み**|`config/rules/ja0_vhf_2026.txt`|大会定義・全部門採点/出力の自動試験済み。原案の未記載事項、主催受付・Windows実機は別途確認。|`docs/contest-research/069_ja0_vhf_2026_reference.md`|
|70|`kansai_vus`|関西V・U・S|**実装済み**|`config/rules/kansai_vus_2026.txt`|採点・全種目JARL出力の自動試験済み。全交信を出力し種目で採点。CWのみは電信へ案内。10.1/10.4GHz共通、24GHz等は別。 主催受付・Windows実機未検証。|`docs/contest-research/070_kansai_vus_2026_reference.md`|
|71|`oidemase_yamaguchi_vushf`|おいでませオール山口 (V/UHF、SHF)|**実装済み**|`config/rules/oidemase_yamaguchi_2026.txt`|採点・全種目JARL出力の自動試験済み。No68/71共有定義のVU/SHF日程。OM年齢は5月31日基準。申告県と実運用場所の同一性は本人確認。 主催受付・Windows実機未検証。|`docs/contest-research/068_071_all_yamaguchi_2026_reference.md`|
|72|`all_gunma`|オール群馬|**実装済み**|`config/rules/all_gunma_2026.txt`|採点・全種目JARL出力の自動試験済み。104種目、実績による部門候補を表示して本人が変更。自動採用は先頭、無断CW優先なし。学年・運用制限は本人確認。 主催受付・Windows実機未検証。|`docs/contest-research/072_all_gunma_2026_reference.md`|
|73|`niigata_branch`|新潟県支部大会記念コンテスト|**実装済み**|`config/rules/niigata_branch_2026.txt`|No.73 7MHz・ハイバンド独立選択・30種目。共通規約でもNo.9へ統合しない。|`docs/contest-research/009_niigata_2026.md`|
|—|`scalg-6m-cw`|SCALG 6m CWコンテスト|**実装済み**|`config/rules/scalg-6m-cw_2026.txt`|採点・全種目JARL出力の自動試験済み。6競技区分＋チェック8。無効取得年でも交信点維持。初取得年・電鍵・必要写真・固定移動の事実は本人申告、認定/写真審査は主催。 主催受付・Windows実機未検証。|`docs/contest-research/extra_scalg_6m_cw_2026_reference.md`|
|—|`kcj`|KCJコンテスト|**実装済み**|`config/rules/kcj_2026.txt`|JARL R1.0/R2.1を採用。Cabrillo・主催結果取り込みは現版の必須残件から除外。|`docs/contest-research/extra_kcj_2026_reference.md`|
|—|`kcj-topband`|KCJトップバンドコンテスト|**実装済み**|`config/rules/kcj-topband_2026.txt`|JARL R1.0/R2.1を採用。Cabrillo追加は現版の範囲外。|`docs/contest-research/extra_kcj_topband_2026_reference.md`|
|—|`cq-ww-ssb`|CQ WW DX SSB|**実装済み**|`config/rules/cq-ww-ssb_2025.txt`|当面2025採用で利用者確定。|`docs/contest-research/extra_cqww_dx_2025_reference.md`|
|—|`cq-ww-cw`|CQ WW DX CW|**実装済み**|`config/rules/cq-ww-cw_2025.txt`|当面2025採用で利用者確定。|`docs/contest-research/extra_cqww_dx_2025_reference.md`|
|—|`cq-ww-rtty`|CQ WW RTTY|**実装済み**|`config/rules/cq-ww-rtty_2026.txt`|保存規約による全種目・CQカントリー別得点と独立マルチ・Cabrillo出力・Overlay資格と別集計を試験済み。 主催受付・Windows実機未検証。|`docs/contest-research/extra_cqww_rtty_2026_reference.md`|
|—|`cq-wpx-ssb`|CQ WPX SSB|**実装済み**|`config/rules/cq-wpx-ssb_2026.txt`|保存規約による全種目・CQカントリー別得点と独立マルチ・Cabrillo出力・Overlay資格と別集計を試験済み。 主催受付・Windows実機未検証。|`docs/contest-research/extra_wpx_2026_reference.md`|
|—|`cq-wpx-cw`|CQ WPX CW|**実装済み**|`config/rules/cq-wpx-cw_2026.txt`|保存規約による全種目・CQカントリー別得点と独立マルチ・Cabrillo出力・Overlay資格と別集計を試験済み。 主催受付・Windows実機未検証。|`docs/contest-research/extra_wpx_2026_reference.md`|
|—|`cq-wpx-rtty`|CQ WPX RTTY|**実装済み**|`config/rules/cq-wpx-rtty_2026.txt`|保存規約による全種目・CQカントリー別得点と独立マルチ・Cabrillo出力・Overlay資格と別集計を試験済み。 主催受付・Windows実機未検証。|`docs/contest-research/extra_wpx_2026_reference.md`|
|—|`cq-160-cw`|CQ 160 CW|**実装済み**|`config/rules/cq-160-cw_2026.txt`|6種目、米州・加14地域・CQカントリーを分離、2/5/10点とMM5点マルチなし。Cabrillo3実周波数、SO30h/MO40h・休止30分。 主催受付・Windows実機未検証。|`docs/contest-research/extra_cq160_2026_reference.md`|
|—|`cq-160-ssb`|CQ 160 SSB|**実装済み**|`config/rules/cq-160-ssb_2026.txt`|CWと別日程・RS/PH、6種目。CQゾーンはマルチなし。CQ専用カントリー欄は実運用地を手動確認。 主催受付・Windows実機未検証。|`docs/contest-research/extra_cq160_2026_reference.md`|
|—|`cq-vhf-ssbcw`|CQ VHF SSB/CW/FM|**実装済み**|`config/rules/cq-vhf-ssbcw_2026.txt`|12種目、GL4・Roverグリッド別の重複/マルチ、レポートなしCabrillo3。相手Roverは/R表記を必要とする。 主催受付・Windows実機未検証。|`docs/contest-research/extra_cqvhf_2026_reference.md`|
|—|`cq-vhf-digi`|CQ VHF Digital|**実装済み**|`config/rules/cq-vhf-digi_2026.txt`|既知モードに加え任意入力を処理。原モード保持、CabrilloではDG。主催判断。|`docs/contest-research/extra_cqvhf_2026_reference.md`|
|—|`ww-digi`|WW DIGI|**実装済み**|`config/rules/ww-digi_2026.txt`|28種目。GL4中心間距離点/GL2マルチ・FT4/FT8共通重複・系列別毎時8変更。ZZ00は総得点未確定でCLAIMED-SCORE省略。Cabrillo3・全帯保持。 主催受付・Windows実機未検証。|`docs/contest-research/extra_wwdigi_2026_reference.md`|

## 元データ

- `docs/contest-research/PSLOG101_CURRENT_AUDIT.json` — 87項目の機械可読な最終監査。
- `docs/contest-research/PSLOG101_CURRENT_AUDIT.md` — 方針再確認と全体試験の説明。
- `docs/CONTEST_RESEARCH_ALL.md` — 調査履歴を含む累積資料。本文中の古い状態表記より本書を優先。

この一覧は `python devtools/refresh_implementation_status.py` で監査JSONから再生成できます。
