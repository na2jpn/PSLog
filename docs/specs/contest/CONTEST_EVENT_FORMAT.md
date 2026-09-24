# 大会条件 event（schema2拡張）

参照可能な実例：config/rules/all_saga_2026.txt。

- timezone: JST又はUTC。入力date/timeは原PSログのJST。コピー上でUTCへ変換する。
- windows: start/end（YYYY-MM-DD hh:mm）とbandsの配列。開始を含み終了は含まない。bandsが空なら区間内の全バンド、その後に参加部門を適用。
- categories: id/name/bands/modes/max_power/min_bands/max_bands/min_calls/required_flags。operatorは任意でSO/MO。max_power=nullは規約独自の上限指定なし（免許による上限を意味しない）。実際の最大電力は別途入力。
- required_flags: 共通の本人確認文。各カテゴリ固有条件と合わせて未確認があれば総点未確定。
- duplicate_fields: call/band必須、mode_family/my_grid/his_gridを追加可。GLは交信ごとの作業値。
- prefer: first又はcw。対象条件外のCWを優先しない。マルチや得点の規約が別の大会へ一律に適用しない。
- special: none/wpx_prefix/grid_distance。wpx_prefixは確認済み作業prefixがあれば保持。grid_distanceは4桁GL中心、球半径6371.0088kmで短距離を計算し、1+floor(km/3000)。ZZ00は距離未確定。主催の距離境界照合が未完了のためWW DIGI完成定義にはまだ用いない。
- submission（任意）: formats/zone/contest/instructions。JARLではこれと参加部門・電力の整合を出力時に再検査。

contextはcategory/power/flags/operating_blocks。提出作業内だけで保持。原本TXTを変更しない。対象ログを変えると確認をリセット。

対象外行も提出用の元の行列に残し得点0とする。大会ごとに採点対象外行の提出指定を確認すること。本拡張は全大会の出力仕様を自動的に満たすものではない。
佐賀県外では正本の20市町番号を完全一致で採用。誤入力を自動補正しない。利用者が受信番号を確認する前提であり、番号から実際の相手運用を認証したとは扱わない。

## 部門別の相手条件（2026-09-14追加）

categories内の任意のeligibleは既存のAND/OR条件形式。共通scoring.eligibleに加えて適用する。
佐賀2026の共通条件は佐賀20市町＋その他60地域。県外カテゴリーだけeligibleを佐賀20市町に限定する。
県内部門へ切り替えると県内運用の確認が必要。番号41を市町へ推定変換しない。
地域参照表はconfig/db/contest/jarl_area_2026.json。実行用TXTには年度の番号集合を埋め込み、DBの後日変更で採点を変えない。

## 部門別の時間条件

categories内の任意のtiming。空のtimingは禁止。制限がない部門には項目自体を設けない。

```json
{
  "operating": {"max_minutes": 2160, "min_off_minutes": 60},
  "band_change": {
    "kind": "hourly", "max_changes": 8,
    "tx_ids": ["0", "1"], "on_violation": "block"
  }
}
```

これは形式の説明用であり、特定大会の完成定義ではない。
operatingとband_changeはいずれか片方のみでもよい。
kind=stayの場合はmax_changesの代わりにmin_minutesを指定する。
stayは最初の交信／変更後の最初の交信から計時し、そのバンドでの後続交信では時計をリセットしない。10分設定なら9分は違反、10分ちょうどは可。
hourlyは大会のtimezoneの各正時からの1時間。直前の時間帯のバンドを引き継ぎ、次の時間帯の最初の交信も変更なら1回と数える。系列の初回は変更回数に数えない。
tx_idsが空なら全体共通。指定があれば交信作業データtxが必須。欠落・未登録IDでは総点未確定。重複判定はtxごとには分割しない。
同一分・同一系列に異なるバンドがあるときは、分精度で変更順を確定できないため出力を停止する。原本の時刻を推測で変更しない。

on_violation=blockは総点未確定・出力停止。hourlyはblockのみ対応。
stayのexcludeは違反行を0点・マルチなしとし、適法な系列の状態を進めず、重複の既交信集合にも入れない。後の適法な再交信を妨げない。
この方式は適用規約を確認して選択する。すべての10分規則へ一律採用しない。

### 運用区間入力

context.operating_blocksにstart/endの配列を保持。日時はYYYY-MM-DD hh:mm、基準はevent.timezone。
開始以上・終了未満。最後のQSOが12:00なら、その分を含めるには終了12:01以降。
重複区間、開催窓外、大会の休憩をまたぐ区間はエラー。
申告区間の長さを合計し、最低休止時間未満の隙間も運用時間に算入する。
前後の大会時間全体を運用とみなさず、逆にログの無交信時間を自動的に休止ともみなさない。
大会開催窓・対象バンドに該当する元の対象行をすべて確認する。参加種目外、重複、無得点の行も運用履歴から落とさない。
ただし対象ログの検索・絞込で除かれた交信は見えないため、参加区分の全運用履歴を対象に含めたことを本人確認必須とする。
機器の送信開始終了時刻や重なる送信、オペレーターの実働は分単位のQSOログだけから確定できない。

### 画面・出力

ルール編集の「部門別の相手条件・時間制限…」から、既存の各部門に対して設定可能。部門自体の新設・日時窓の編集は引き続きJSON。
提出時の「参加部門・運用条件…」は部門タブ／時間タブ。区間や部門・TXを変更すると履歴確認を解除する。
採点内訳に運用分数・バンド変更の違反候補数を表示。出力時に同じcontextで再検査する。
送信系列を必須とする部門は、TX列のないCabrilloテンプレートへの出力を停止する。
JARLの系列表記はsubmission.jarl_tx=trueで有効にする。指定がないtx_ids付き部門は出力を停止する。各行末尾に系列番号を記載する。
ALL JA2026の2波4種目は実行用定義を追加済み。他のJARL2波大会定義、Cabrillo大会別カテゴリとの対応、WPX等の連番系列・オフ時間の主催完全一致は未完了。


## JARL地域番号・2波提出（追加）

- categories.min_power_exclusive（任意）: 最大電力がこの値を超える区分。max_powerと組み合わせる。例Mは5超～100以下、Hは100超で上限は免許範囲。
- categories.required_mode_families（任意）: phone/cw/digitalの配列。必要な運用分類を検査。完全な重複交信は、そのモードで運用した事実に含める。時間違反・対象外・未確定の行で要件を充足させない。
- event.exchange（任意）: kind=jarl_region_power、regions=年度の地域番号配列、same_sent_region=bool。送受信番号を地域＋H/M/L/Pとして検査し、受信地域をareaマルチへ用いる。補助areaに矛盾があれば停止。原本・作業入力の生番号は変更しない。
- 交換の電力文字は最大電力との明白な矛盾を検出する。HFのMは10W超、50MHzは20W超、Lは5W超、Hは100W超。これは各QSOの実出力の測定・完全検証ではない。運用者による確認は必要。
- same_sent_regionは送信地域番号の一致条件。ALL JAでは許可されるSO移動も開始時のマルチ地域内なので適用する。物理的に同じ運用地点を意味しない。Rover等へ一律に適用しない。
- submission.jarl_tx（任意bool）: trueならJARL行末に送信系列を追加。PSLogの定義では1桁数字を最大2種類。ALL JA2波は1/2。物理リグ番号ではない。JARLが許可するTX#1等の任意表記への入力拡張は未対応。
- 系列必須の場合は、種目外・開催時間外・重複行も含め全出力行の系列を要求する。空欄を1などへ自動補完しない。
- submission.required_fields（任意）: email/opplace/multioplist/licensedate/age。大会固有の必須欄を提出画面に表示し、出力前に検査する。
- ALL JA2波: CM2H/CM2M/XM2H/XM2Mのみ。XMは電話による運用が必要。通常のSO/MOへ2波時間規則を拡張していない。
- R1.0合計SCORE欄もschema2の実マルチ数を出力。旧schema1で第一マルチoffの場合の表記は維持。

出典: https://www.jarl.org/Japanese/1_Tanoshimo/1-1_Contest/2tx_log.html
および保存済みjarl_2tx2.html、all_ja_2026.html。2026-09-14に公式ページを再確認。


## 参加資格・バンド別電力（2026-09-14追加）

- category.qualification（任意）：min_age/max_age、license_since/license_until（両方必要、YYYY-MM-DD、両端含む）、operators_max_age。年齢は0～150の整数。未知キーを拒否。
- context.ageは実運用者の運用時年齢。context.licensedateは個人局の最初の免許日。context.operatorsはname/ageの配列。全員の年齢条件を検査し、空欄・重複名を拒否。
- category.power_by_band：バンド→最大許容W。context.power_by_band：バンド→実際に使用した最大W。省略バンドはcontext.power（全体最大W）を使う。バンド最大が全体最大より大きい申告も拒否。ログから実際の送信電力は測れない。
- event.band_modes：バンド→許可モード配列。PSLogはBANDを持つため、周波数帯内の細かな周波数そのものは検証できない。
- GUI「参加資格・バンド別電力」で値を入力。年齢・免許日はサマリーへ、ジュニアの氏名/年齢はMULTIOPLISTへ連携。出力時に再照合し、編集による資格欄の欠落を防ぐ。
- PN/CS/XSの資格情報はR2.1のAGE/LICENSEDATEを用いる。PSLogでは当該種目のR1.0出力を止めるが、主催のR1.0禁止を意味しない。
- ALL JA実行用定義は現在68種目。10分規則はCM2H/CM2M/XM2H/XM2Mのみ。通常種目へ継承しない。XMJの電信のみ参加を許可。
- ルール自体の新規資格条件編集はJSON。RuleEditorで他の項目を編集しても追加フィールドを保持する。


## バンド別番号体系と大会別表記（2026-09-14）

### event.exchange.kind = jarl_band_power

same_sent_region（bool）、profiles（1～30個）を指定。従来のjarl_region_powerも維持。
各profileはid、bands、codes、code_lengths、m_threshold、pointsの全項目必須。
- idは重複のない小文字英数字/_。番号体系を識別する（例prefecture / municipality）。
- bandsは明示した正規表記。プロファイル間で重複不可。未知バンドを数値の大小だけで高域扱いしない。
- codesは確認済み年度辞書を埋め込む。1～10000件、2～6桁の数字文字列。先頭0を保持。code_lengthsは許容桁数の配列。未登録コードを勝手に補完しない。
- m_thresholdは10又は20W。送信番号のH/M/L/Pと申告最大電力の明白な矛盾を検出する。各交信の実出力を測定したことにはならない。
- pointsは0以上の有限数。このプロファイルのQSO得点となり、汎用得点条件より優先する（距離採点等との同時適用は大会定義で避ける）。重複・対象外は得点なし。
- 送受信番号を同じprofileで検査。areaは受信番号の数字部分へ設定。補助areaと矛盾すれば未確定。
- same_sent_region=trueでは同じprofile.id内の送信番号を比較。低域13と高域市郡区番号を異なる運用地と誤判定しない。ただし両者の親子関係/実所在地一致はまだ自動検証しない。実行用ルールでの接続時に対応が必要。

### event.normalization

bands、modes、mode_familiesの3つの対応表を指定。空表は許可。
例（設定機構の説明用、6D配布定義そのものではない）:
```json
{"bands":{"2.4G":"2400","10.1G":"10100","10.4G":"10400"},"modes":{"D-STAR":"DV","DSTAR":"DV"},"mode_families":{"DV":"phone"}}
```
- 前後空白除去/大文字化後に完全一致で変換。別名連鎖・循環は不可。
- 10Gのように10.1G/10.4Gが判別できない表記は自動推測しない。
- 変換は作業コピー上のみ。開催窓/部門/番号体系/重複/マルチ/必要モード/得点/JARL出力へ同じ値を使用する。
- DVを電話とする設定は当該大会のみ有効。FT8/DMR/C4FM等を自動的にD-STARへ含めない。シンプレックスかどうかは別途本人確認が必要。
- R1.0バンド集計とQSO行のBAND/MODEを同じ表記へ統一。種目外・重複行も残す。原本ファイルは不変。
- normalization付き大会のCabrillo/zLog出力接続は未実装のため停止する。新フィールド未対応の古い本体へ配布すると未知キーとして拒否される。
- 新フィールドの専用編集GUIは未追加。ルールのJSONで設定する。

原典再確認: https://www.jarl.org/Japanese/1_Tanoshimo/1-1_Contest/6d_rules.html （2026-09-14）。全文の保存済み資料はcontest-research/sourcesを参照。


## 地域体系間の照合・明示チェックログ（2026-09-14）

- jarl_band_powerにparent_regions（任意）：市郡区コード→低域地域コードの辞書。キー/値はprofilesのcodes内に存在する必要がある。送信番号が複数体系に現れるとき親地域の矛盾を検知する。北海道01から101～114を推測しない。6Dでは未自動化の北海道を含む実所在地一致を本人確認フラグで明示。
- 作業draft.checklogはbool。GUI「提出用の交信情報を補完」のチェック欄で入力。原本11項目に追加しない。
- event付きschema2で明示X行を採点対象外にし、重複既交信集合へ加えない。ただし開催内の運用履歴には残す（時間規則がある大会の場合）。番号の誤送信を遡って改変しない。
- JARL出力では明示checklog=trueに限り行頭を「X 」とする。種目外/重複で0点の行に自動付与しない。元送受信番号・RSTは保持し、バンド/モードの表記変換だけは通常行と同じ。
- 明示X付きのschema1、eventなしschema2、Cabrillo/zLog出力は未対応として停止する。全体CATEGORYCODE=CHECKLOGは別仕様で未実装。
- 資格、所在地、D-STAR等の6D用全体条件は本人確認を併用する。モード/番号の自動検査だけで免許・実運用遵守の保証としない。


## 提出目的とFD局種（2026-09-14）

- context.submission_modeはentry（既定）又はchecklog。checklogはevent付きschema2のJARL提出専用。prepareで作業行を全体チェックログとして除外し、競技資格/最低件数等の検査を省略。CATEGORYCODEと目的を出力時に照合。提出の形式・必要情報・原本外部変更検査は維持。
- JARL info.portable/guestはbool。移動または自局末尾/数字・/JD1・/Pならopplace必須、guestならopcall必須。任意の移動表記をすべて推測するのではなく本人申告を併用する。
- event.station_factor='jarl_fd'（任意）。context.fd_class='A'/'B'/'HOME'。Aはcontext.fd_confirmed=trueを要する。宣言した局種が途中で変わらないこと等を本人確認。採点は第二マルチ2/1/1。元ルールはmulti2.kind=off、formula=total、scoring.bonus=0に限定。
- FD提出はinfo.fd=trueを必須とし、計算済みresult.multi2からFDCOEFFを出す。Aでは移動表記・運用地・供給源の記載を検査。Bは運用地、ホームの電源欄は任意。全体CHECKLOGとFD得点係数申告は併用しない。
- jarl_band_powerの各profile.power_lettersは任意のH/M/L/P配列（既定4文字）。FDはM/L/Pのみ。送受信双方を検査し、受信Hを正しい受信番号に書き換えない。必要ならその行を明示チェックログにする。
- FDの実行用定義は現在CA/XAのみ。モーニング、2波、電話/特別種目を実装済みと誤認しない。devtools/build_field_day_2026.pyで再現可能。

根拠：保存済みfd_rules/FAQ/logformat資料。FD規約は2026-09-14再確認。所在地・電源・運用者情報の実際の正しさをソフトが保証するものではない。


## 種目の採点時間枠（2026-09-14）

category.scoring_windows（任意）にstart/endの配列を設定する。
例: [{"start":"2026-08-02 06:00","end":"2026-08-02 12:00"}]
- YYYY-MM-DD hh:mm、時刻基準はevent.timezone。開始を含み終了を含まない。
- 1～50件。個々の枠は大会の開催区間内、終了は開始より後。枠同士の重複を禁止。
- 部門の採点対象を限定するもので、運用そのものが時間外だった事実を消さない。大会の運用履歴（_timing_scope）は保持する。時間制限との併用時にも、採点外行を勝手に運用履歴から落とさない。
- 枠外は番号辞書/重複/マルチ計算へ加えず0点で提出に残す。夜間の同局交信がモーニング内の交信を重複として占有しない。枠外の電話で枠内の必要電話条件を充足させない。
- 枠外というだけで行頭Xを自動追加しない。本人が明示チェックログにした行は従来どおりX。
- 未設定の従来ルールは大会全体の開催窓のまま。全体CHECKLOGでは競技採点枠を適用しない。
- GUIで時間枠と終了非包含を表示。時間枠自体の編集はJSON。RuleEditorで他の属性を編集しても保持する。
- FD CAR/XARに接続。CM2/XM2にはこの時間枠を付けず、既存timing.band_changeの系列1/2・10分・違反除外を指定。JARL行末TXで出力。

FDの現在の実行用定義はSWL除外42種目。旧CA/XAのみのr1は配布履歴として保持し、r2で同じID/年を更新する。
根拠: https://www.jarl.org/Japanese/1_Tanoshimo/1-1_Contest/fd_rules.html と保存済みFAQ・2波資料。2026-09-14確認。

## 数字地域・構成条件・参加局種・大会内アワード（10ステップ版）

2026-09-14。新しい項目はいずれも省略時に従来動作を維持する。詳細な実例は同梱ACAG/XPO/東京CWルールを参照。

- exchange.kind=numbered_region：codes（重複なし2〜6桁の文字列、最大10,000件）、same_sent_region（bool）。送受番号を完全一致検査し、受信番号をareaへ、送信番号を作業用_sent_regionへ設定。電力文字を勝手に付加・切除しない。得点は通常points/conditionsで定義する。
- jarl_band_powerにsame_sent_region_across_profiles（bool）を追加。trueなら複数プロファイルをまたいで同じ送信番号を検査。ACAGのM境界だけ異なる市郡区体系に使用。FD/6Dの別番号体系は従来動作。
- category.sent_codes：numbered_region辞書の部分集合。東京CWの自局都内外区分を送信番号で検査。相手の地域点とは独立する。
- category.excluded_band_subsets：1〜50個のバンド配列。各配列は部門対象バンドの部分集合。有効交信バンド集合がそのいずれかに完全に収まる場合、参加部門を要確認とし出力を止める。例XPO全帯でHFだけを除く。勝手に部門コードを変更しない。
- event.entrant={station_types:[],guest_policy:"allowed"}。station_typesはindividual/club/specialの部分集合。空なら局種申告を要求しない。空でなければcontext.station_typeを運用条件画面で申告し検査する。全体CHECKLOGでも局種の提出資格を迂回しない。
- entrant.guest_policyはallowed/mo_only/forbidden。ゲストチェックまたはOPCALLSIGN入力がある場合、提出直前に検査する。既存ルールは省略でallowed。東京CWはforbidden、XPOはmo_only。
- event.awards：最大20件の{id,name,groups}配列。group={codes:[...],min_count:N}。各集合内の異なる番号数がN以上、全グループのANDで達成候補。番号はnumbered_region辞書の部分集合。コードの範囲から欠番を生成しない。
- アワードの対象は選択済みログに含まれる大会開催内の有効交信。大会対象の実バンド全体へ集計範囲を広げ、選択された提出種目の得点とは分離する。時間外・明示X・未確定情報を使わない。選択していない他ログは自動検索しない。
- info.award_requests=[id,...]をJARL出力へ渡した場合だけ、出力直前に再判定して意見のコピーへ「賞名を申請します。」を追加する。未達・未知ID・重複指定を拒否する。元info/ログ/通常採点値は不変。
- アワードの右側表示は180px以下のスクロール枠。未達は選択不可、既定はすべて未選択。対象ログ・年度・部門変更時に選択を引き継がない。

これらのルール定義編集はJSON、参加時の選択と結果確認はGUIに対応。定義ファイルだけでは旧本体に新機能を追加できない。

## モード分類と担当交信割合（愛・地球博10ステップ版）

- event.mode_groups={CW:"cw",SSB:"phone",AM:"phone",FM:"phone",DV:"dstar"}のように重複用分類を設定する。duplicate_fieldsへmode_groupを追加した場合、対応表を必須とする。点数のphone/cw/digital分類とは独立する。
- event.mode_confirmations={DV:"確認文"}。該当モードの有効候補がある時だけcontext.flags[確認文]=trueを要求する。画面には確認文を表示する。normalizationの別名処理後の基底モードを用いる。
- category.participation={max_age:20,min_percent:80,family_pair:false}。年齢・百分率は整数。全体との比較は整数演算。
- context.qso_operators=[{name,age,qsos,role},...]、1～1000人。nameは重複禁止、age=0～150整数、qsos=0～100000000整数、roleは空/子/父/母/祖父/祖母。SOでは1名のみ。
- 担当数合計は開催区間・対象バンド内の選択ログ全行数に一致させる。重複・明示X・モード外の無得点行も含む。全履歴を選択した確認を別途要求。詳細と解釈上の限界はCHECKPOINT_BATCH10_AI_CHIKYU.md。
- family_pair=trueは子1＋親又は祖父母1、子の年齢上限を検査。context.child_callが必要で、JARL出力直前に提出元自局と比較する。
- category.fallback_category="PMA"は存在する別種目IDを指定。運用条件画面のボタンでだけ変更し、変更先の条件を通常どおり検査する。
- participation付き種目では担当者の年齢・数・続柄をJARL意見のコピーへ追加。MOはMULTIOPLISTを担当表の名前一覧と整合させる。原入力のcommentsを書き換えない。
- event.submission.orderはtime（省略時）又はband_time。後者は定義の開催窓に登場するバンド順、バンド内時刻順。同じindicesで採点結果と元行を参照する。対象外バンドは末尾。元選択・PSログを並べ替えない。

旧ルールでこれらを省略した場合は既存動作のまま。新しい構造を古い本体が読めない場合は検証で拒否する。


## 2026-09-14 東京UHF／春の東京追加

- event.band_choices: 元の曖昧なバンド名をキー、2個以上の異なる実バンド名を配列値とする辞書。選択肢は開催帯域内。例 {"10G":["10100","10400"]}。元の名前自身を選択肢にしない。
- draft行のcontest_band: 提出作業用の明示選択。曖昧行の未指定・不正指定はエラー。確定帯域との矛盾も拒否。band_choicesを持たない他大会では残存指定を無視し、その大会の正規化を使う。原本不変。
- category.operation_bands: 得点帯域とは別の運用許可帯域。開催中の範囲外運用はX指定より先に検査。categoryの採点帯域はこの部分集合。開催時間外は運用条件に数えない。
- qualification.age_output: field（既定）又はcomments。年齢条件を伴う場合のみ指定。commentsは意見欄に年齢を追加し、年齢欄を理由にR2.1を要求しない。他のR2.1条件を緩和しない。
- category.modes=["*"]: 許可された電波型式を扱う大会専用。通常の電話・電信・デジタル得点が同一の場合のみ許可。mode_groups、mode_family重複条件、required_mode_familiesと併用不可。未知モードの分類を捏造せず共通点を用い、地域条件を適用する。
- 大会内アワード候補の帯域拡張はoperation_bandsとの共通部分に限定する。禁止帯域の実運用は引き続き検査する。


## 2026-09-14 オール千葉追加

- category.submission_code（任意）：公式提出コード。内部idは従来のASCII識別子。日本語・空白・小数点を含む公式コードを画面とJARLへ使用。未指定ならid。大会内重複、制御文字、タグ、CP932不可は拒否。
- category.station_types（任意）：大会entrant.station_typesの非空部分集合。採点前に自局申告と照合。operator省略ならSO/MOを固定しない（社団SOを個人SOへ変えない）。
- category.operators_in_comments（任意bool）：全運用者の姓名・従事者資格をinfo.multioplistに要求し意見欄へ追加。実在・免許照合は本人確認。
- qualification.license_output（field/comments、既定field）：license_since/license_untilと併用。commentsは参加条件で確認した日付を意見へ記載し、その条件を理由にR2.1を強制しない。従来のfield動作は維持。
- event.submission.club_entry（任意）：prefix（例12-）とstation_types。登録クラブ欄入力時に対象局種、NN-NN-NN番号、指定prefix、クラブ名を照合。空欄なら申請を強制しない。
- 上記は提出作業上の値。元TXT・既存意見・確認済み入力を上書きせず、繰返しプレビューでも追記が累積しない。


## 2026-09-14 オール大阪追加

- event.exchange.kind=tagged_region：codes/local_codes/same_sent_region/tag_points/operator_tag/special_tag/special_calls/young_below/reference_dateを指定。地域＋任意1文字の尾字を解析。地域辞書はnumbered_region同等。
- special_callsは基本コール→許可地域配列。Xは局名と所在地を照合。送信Xは選択ログの実際の自局コールで照合。受信番号の尾字得点処理はカテゴリ交信相手条件の後で適用する。
- 作業行operator_name/operator_birthdate/operator_yl：Y送信の実OP情報。出生からreference_date時点の満年齢でyoung_below未満を検査。YLなら生年月日は公開不要。入力は原本へ戻さない。
- qualification.yl_or_younger_thanとreference_date：context.qualification_basis=yl/young、young時はbirthdate必須。カテゴリ資格と送信Y行の情報を照合する。
- event.operating_locations={groups:{id:表示名},matches:{id:[一致候補id]}}、category.location_groupで提出ごとのグループを指定。context.operating_locationsで各運用地を申告し、提出OPPLACEを選択グループと照合する。
- category.mo_operators_in_comments：MO選択時に全運用者一覧を要求し意見欄へ。既存operators_in_commentsはSOでも必須という従来動作。
- 個々の提出の採点は独立。全交信の原本、送受ナンバー、MyQTHを変更しない。時刻枠と通常の重複処理は既存機能を利用する。


## 2026-09-14 福岡追加

- event.power_by_operation={stationary:100,portable:50}：正の有限電力。context.operation_kindを明示選択し、全体の最大電力を検査する。カテゴリー自身のmax_power等も従来通り検査。
- 運用形態未選択、上限超過で停止する。入力電力の自動修正・自動チェックログ変換なし。明示チェックログを選んでも本設定の検査を迂回しない。
- 提出info.portableとcontext.operation_kindを照合。移動運用のOPPLACEは必須。コールの移動表記と非移動申告が矛盾する場合は確認を求める。推測で申告を書き換えない。
- category.operator_list_format=full/calls（既定full）。operators_in_comments又はmo_operators_in_commentsと併用。callsは全員のコールを分離・形式検査し備考へ記載、不要な氏名・資格を要求しない。fullは既存の姓名・資格入力方式を維持。


## オール岡山対応の任意拡張（2026-09-14）

- `event.entrant.checklog_only_types`: station_typesの部分集合。該当局種は競技提出を停止し、利用者の明示的な全体チェックログ指定を求める。
- `event.newcomer_claim`: name, license_since, license_until, operators, station_types。両端を含む初開局日の範囲。contextのnewcomer_requested, newcomer_licensedate, newcomer_first_licenseで任意申告し、提出時に検証。点数・種目には影響しない。
- `event.submission.allowed_zones`: JST/UTCの許可リスト。省略時は既存zoneのみ。zoneを必ず含む。
- `event.submission.row_scope`: all（既定）またはcategory。category指定時だけ日時・バンド・モードで提出ビューを絞る。部門内の重複・無得点行は保持し、得点による行除外は行わない。全体チェックログでは元選択を保持する。

これらの拡張を含むパックは対応した本体が必要。元ログは変更しない。


## PSLOG101 鳥取・ギガヘルツ（2026-09-15）
- category.sent_codesは最大10,000、交換番号辞書の部分集合。その他の汎用配列上限は1,000のまま。
- submission.club_entry.prefix=nullは全国のNN-NN-NNを受け付ける。従来のNN-指定も維持。
- club_entry.regions={inside_prefixes:["08-","09-"],inside_label:"信越管内",outside_label:"信越管外"}は登録クラブ番号だけで区分を判定。自局の運用地や種目コードを変えない。prefix=null時のみ指定可。
- 登録申告は任意、入力時は番号と名称を必須検査。地域付き申告を意見のコピーへ追加し、R2.1でも名称を落とさない。
- submission.band_labelsは内部バンド→提出バンドの対応表。例{"24000":"24G"}。JARL帯域別集計ラベルとQSO行を同じ表で変換。採点・重複キー・原本は変えない。
- 異なる採点バンドを同一出力ラベルにする設定は拒否。10.1/10.4GHz統合はこのラベル機能ではなくevent.normalizationで採点前に行う。
- 新設定を含むパックは今回の本体を必要とする。旧1.01は未対応キーを検証で拒否し、パックだけで本体更新はされない。

## PSLOG101 地域大会拡張（2026・残り50チェックポイント）

`event.regional` と `category.regional` はデータのみであり、任意コードを実行しません。未対応キーは拒否します。古い1.01へ新ルールだけを導入せず、この累積ソースと組にしてください。

- `literal_region`: codes/same_sent_region/region_map。英字付き町番号やKJを送受信値のまま保持し、マルチ値だけ明示辞書で変換します。
- event: `base_call_duplicates` は基本コールによる大会専用重複判定。通常検索の一致条件は変更しません。
- event: `local_codes` は自局番号が管外なら管内相手のみ採用する条件。自局が管内なら国内全域を採点します。
- event: `sent_scope=window` は同一送信番号制限をステージごとに評価します。ステージ内の実際の移動は本人確認も必要です。
- event: `entry_set={max,kind}`。kind は disjoint（対象バンド非重複）、hf_vu（HF側1/VU側1）、sections（各提出区分1）。`context.entry_categories` で全提出種目を宣言し、現在の種目ごとに別ファイルを作ります。
- event: `declarations` は追加申告欄の対応表。category の `required_declarations` に指定した欄を画面・採点・出力で検査し、意見欄へ記載します。実在性・申告内容の正しさは本人確認です。
- category: `quotas=[{codes,min_calls,unless_sent_in?}]` は採点有効行から基本コールで異なる必要相手局数を確認。バンド違い・移動表記だけで局数を増やしません。
- category: `min_operators` は実交信担当者数。氏名登録だけでは不十分です。完全な種目内交信（重複を含む）の実担当を使い、QSO作業欄の `operator_name` へ入力します。
- category: `required_band_groups` は各帯域群で少なくとも1帯の有効交信。`multiplier_map` は受信原値を維持したマルチ変換、`multiplier_codes` は得点を残してマルチ対象だけ制限、`points_by_code` は地域別の点数です。
- `prefer=highest` は対象時刻・種目・交換・相手条件の確認後に同局同帯の最高得点行を採用。同点は先頭で安定化します。
- event: `checklog_code` は CHL/CHKLOG 等の公式コードを保持。`outside_category_checklog` は種目外をX行にし、サマリー局数から除外します。
- event: `club_sent_codes` はクラブ対抗に管内実運用が必要な場合の追加条件。通常参加資格とは別です。
- event: `cw_award` は個人の有効CW交信から電信部門の別内訳を再計算。category の `junior_since` は任意の `declarations.junior_birthdate` を検証し、同一提出のジュニア申告へ記載します。
- `power_by_operation` の null は運用形態による追加上限なし。免許範囲の確認は別です。
- qualification の `license_label` は再開局を認める大会の申告表示に対応。初開局限定を誤って強制しません。

原本TXTの11列・JST・元RST・所在地・備考は変更しません。`rst_sent` / `rst_received` も提出用の作業値です。実機受付互換性は、自動試験だけで確認済みとはしません。
