# ADIFインポート 1.00 開発版

参照基準：[ADIF 3.1.4](https://adif.org/314/ADIF_314.htm)。これは全ADIF項目対応・外部ソフト互換性の完成宣言ではない。

## この版の実装判断

| 入力 | PSログへの扱い |
| --- | --- |
| .adi / .adif | ASCII。長さ指定に従い解析。EOH省略可、各交信のEOR必須 |
| .adx | UTF-8 XML。DTD・独自エンティティを拒否 |
| QSO_DATE / TIME_ON | UTCから9時間進めたJST。変換後DATEの年へ振り分け |
| 秒 | 非ゼロ秒はADIF_TIME_ON:HHMMSSUTCとしてRMKSにも保持。日時列は分精度 |
| STATION_CALLSIGN | 指定自局と不一致なら要確認交信。明示上書き時は元値をRMKSへ保持 |
| 自局項目なし | 画面指定の自局を採用。OWNER_CALLSIGNやOPERATORは自動的に運用自局に使わない |
| BAND | 対応表からPS BANDへ変換。BANDがあれば優先 |
| FREQ | BANDがなければ帯域表から判定。元周波数はRMKSへ保持 |
| MODE | PSLOG独自MODE、SUBMODE、MODEの順で採用。未知モードも取り込める |
| RST | 欠落は空欄。FT8/FT4/FT2/FreeDV系のゼロを+00へ正規化 |
| HIS QTH | QTH_INTLまたはQTH。GRIDSQUAREがあれば追加 |
| MY QTH | PSLOG独自値、MY_CITY_INTL、MY_CITY、MY_GRIDSQUAREの順 |
| JCCJCG | APP_PSLOG_JCCJCGのみ。CNTYからの自動変換は未実装 |
| RMKS | COMMENT_INTLまたはCOMMENT。未使用項目はADIF_EXTRAのJSONへ保持 |

この秒・自局競合の扱いは、未決事項に対する今回の開発実装。変換内容を画面表示し、明示チェック後のみ保存できる。

OPERATOR/NAME、QSLフラグ等も追加項目として保持する。名前のOP:表記や.Rへの意味変換は未実装。MODEとSUBMODEの組合せの全列挙検証も未実装。BANDとFREQが両方ある場合の矛盾検査はまだなく、BAND優先で元FREQを残す。国名の自動補完・所在地DBによる日本語ローマ字化も未実装で、所在地は入力表記を保持する。

パイプは全角縦線、改行・タブは可視のバックスラッシュ表記へ置換して11項目構造を守る。変換の詳細と解析した元ADIF全項目は取り込み結果JSONにも保存する。原本の入力ADIFは変更しない。

重複は変換後のDATE・TIME・CALL・BAND・MODEで判定するため、同じ分内に複数交信があれば重複候補となり得る。「全て追加」の選択は可能。秒を使う別の重複判定へ無断変更しない。

## 停止と除外

文字コード・タグ長・EOR欠落・XML破損・重複フィールドなど構造上の問題はファイル全体を停止。交信単位の日付・時刻・CALL・BAND不足・自局不一致などは番号と理由を表示し、除外チェックがなければ保存できない。ADIFの番号はテキスト行番号ではなく交信レコード番号。

年別保存、バックアップ、外部変更検知、途中停止結果はPSログTXTインポートと共通。複数ファイルの自動巻き戻しは未実装。

## 最新追補: 国名補助
所在地補助ON時、QTHが空なら入力COUNTRY_INTL/COUNTRYを優先し、それもなければCTY候補を使用。既存QTHとGLを保持。元の国名項目はADIF_EXTRAにも保持します。OFFならこの補完を行いません。日本語QTHのローマ字変換は未接続。

## 最新追補: 日本語所在地
補助ON時、非ASCIIのQTHは元文をRMKSのQTH:へ保持し、日本と判定できる局のみ確認済み所在地DBへ完全一致照合します。提供済み確認表記と利用者確認表記を使用。コードがあれば種別・番号も一致必須。例: JCG 37002C。未確認の読みを推定採用しません。未一致は国名/GL補助へ進み、曖昧運用は国名を断定しません。補助OFFは元QTHを保持。標準JCC関連フィールドの追加マッピングは今回行っておらず、APP_PSLOG_JCCJCGを利用します。日本語ADIは引き続き非対応でADXを使用してください。


2026-09-11: ADIF QSL取り込み更新
LoTW/eQSL標準項目の限定的な逆変換を実装。送信・受領が両方Yの場合に.R化、eQSL送信済みはeQSLへ。元項目保持、矛盾時の確認表示。詳細ADIF_QSL_IMPORT.md。上記の逆変換未実装との記載は本更新で部分的に解消。紙カード系・受領情報のみの自動判定等は対象外。Linuxオフスクリーン184テスト成功、Windows EXE・実機未検証。


## 2026-09-11更新: 相手名と自局オペレーター

NAME_INTL（非空の場合を優先）、NAMEは相手の名前としてRMKSへOP:名前の形で追記する。元フィールドもADIF_EXTRAに保持する。既存のOP:（小文字も認識）があれば、その内容を保持して自動追記しない。取り込み時の確認事項に表示する。日本語・区切り文字は従来の構造保護処理を適用する。

OPERATORは自局側のオペレーターのコールサインであり、相手名には使用しない。STATION_CALLSIGNが存在しない場合は、ADIF仕様に従いOPERATORを自局の照合に使用する。画面で指定した自局と異なる場合、既存の自局上書き指定がなければその交信をエラーとする。上書き指定を選んだ場合も元のOPERATORを保持する。STATION_CALLSIGNが存在する場合は同項目を優先する。

MY_NAME、CONTACTED_OPは引き続きADIF_EXTRAに保持する。自由記述OP:からADIF NAMEへの逆変換は未実装。

参考: ADIF 3.1.4、NAME / NAME_INTL / OPERATOR / STATION_CALLSIGN（2026-09-11確認）
https://adif.org/314/ADIF_314.htm

検証: 相手名と自局名の区別、既存OP保持、日本語と構造保護、自局の不一致と上書き。Linuxオフスクリーン全188テスト成功。Windows実機・EXEは未検証。


2026-09-11: ADIFバンド整合チェック
BANDとFREQを併記した入力でもFREQの数値・有限性・対応帯域を検査し、不一致は交信単位のエラーとして表示。BANDを黙って優先しない。正常な実周波数はADIF_EXTRAへ保持。判定帯域は既存のRANGESを使用し、帯域の追加や国内運用可否の判定を行う変更ではない。ADI/ADX、矛盾、不正数値、片方のみの入力を確認。全192テスト成功（Linux offscreen）。Windows EXE・実機未検証。残作業の最新情報はREMAINING_1.00.txt統合版を参照。


2026-09-11: ADIFモード対応更新
FT2等を追加。通常ADI/ADXとPOTAはADIF_VER 3.1.7。既知MODE/SUBMODE矛盾を検出、未知入力は保持。詳細ADIF_MODES.md。196テスト成功、Windows実機未検証。


2026-09-12: ビューロ標準項目の取り込みを実装。経路Bかつ状態YをBURO/BURO.Rへ反映し、元項目保持。発送不明は返送要否の確認、曖昧な経路は推測変換しない。従来の紙カード逆変換未実装の記載を部分的に更新。詳細ADIF_BUREAU_IMPORT.md。204テスト成功、Windows実機未検証。
