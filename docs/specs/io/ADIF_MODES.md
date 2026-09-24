# ADIFモード対応（1.00）

通常ADI/ADXとPOTA ADIのADIF_VERを3.1.7へ更新。アプリ版は1.00のまま。
FT2はMODE=MFSK、SUBMODE=FT2で出力する。FT2 ASのような補足表記は通常出力のAPP_PSLOG_MODEに保持する。POTA提出用は標準モードへ変換し、補足表記を出力しない。

対応モード一覧はadif_modes.pyのMODESに集約。今回FT2、JS8、Q65、FST4/FST4W、M17、JT65サブモード、PSK63/125、FREEDATAとVARA系を追加。
FT8/FT4/FT2/FreeDVを含む補足付き表記は既存の入力補助方針に合わせる。ただし複数の異なる基本モードが含まれ、出力を確定できない場合は停止する。

取り込みでは、対応表で既知のMODE/SUBMODE同士が矛盾すると交信単位でエラーにする。未知のモードは拒否せず、組み合わせ未検証の確認事項を表示し、元MODE/SUBMODEをADIF_EXTRAに保持する。出力対応表にないモードの出力は引き続き停止する。ADIF全モードの網羅を意味しない。

参照: ADIF 3.1.7（2026-03-22更新、2026-09-11確認）
https://adif.org/317/ADIF_317.htm
FT2追加、Mode/Submode列挙を確認。
新しい版の全フィールドを取り扱う実装ではない。RST初期値や入力の未知モード許可方針は変更していない。

検証: FT2補足付きのADI/ADX再取り込み、追加モード、既知組み合わせ矛盾、未知モードの保持、POTAヘッダーとFT2。Linux Qt offscreen全196テスト成功。Windows実機・外部提出先での受入は未検証。
