# PSLog 1.19 FIX3 検証

## 実装範囲

累積差分（FIX1とFIX2を包含）。版番号1.19を維持。ツール3項目、総務省参照、5分間隔の国内クラスタ監視と任意のRBN対応接続。
HTTPは既存Chrome形式UAを共通化。総務省の取得処理は既存HIS QTH作成と共通化し、拒否・サイズ上限・タイムアウト・通信例外・JSON解析の詳細を表示する。局情報を閲覧する機能でありログへの書込なし。
国内スポットは公開XMLのSpotStationから運用局の所在地を取得。ReportStationの所在地は流用しない。RBNは地域条件へ算入せず、コール一致のみ。接続先はRBN対応リレーを指定でき、既定はarc.jg1vgx.net:7000。任意有効化・明示開始。
国内取得はアプリ起動中共通のゲートで最短300秒。失敗時は600～4800秒へ延長しHTTP Retry-Afterの秒指定も考慮。画面を閉じると新規取得と通知を停止し、取得中のHTTPは最大15秒で終了する。RBNソケットは停止時にshutdown。再接続の最短間隔300秒、自動連続再接続なし。
条件・音・任意接続設定はconfig/cluster_monitor.json。Snapshotと既存の原子保存・外部変更検知を使用。次回自動接続なし。設定破損時は元データを保護。交信ログ・申請済情報・無線機制御へ変更なし。

## 検証結果

- 全167モジュール・1,041テストのunittest検証項目がOK。160モジュールは終了コード0。7モジュールはOK後に既知のQt終了異常（下記）。
- 新規12コア＋7GUI検証：Shift_JIS XML、運用局と報告局の分離、JCG末尾文字一致、誤った前方一致の排除、RBNのUTC日跨ぎ、通知重複抑止、タグ入力・削除、音OFF、初期未接続、条件保持・自動開始なし、停止後の結果破棄とソケット終了、メニュー配置を確認。
- 最終の画面高さ・新着順整形と、実際の取得スレッド動作中に閉じる検証を追加した後、関連48件の検証項目OK（同一プロセス終了時にQt異常）。新規GUI7件とコア12件を別プロセスで再実行し終了コード0。GUIテストはDeferredDeleteを処理してQApplication終了前に確実に破棄するよう整備。
- 全Pythonの構文確認。画面をoffscreen描画して、下端ボタン、タグ、通知設定、詳細表示と新着順を確認。
- 国内公開XMLの実通信1回でHTTP 200、取得した991スポットを解析成功（追加の定期アクセスは行わず、以後この取得バイトをQAに使用）。この実データはZIPに含めない。
- 総務省APIはJH1HSTを1回照会してHTTP 403を確認。番号・URL・理由・応答HTML冒頭を取得できることを確認。実際の局情報取得成功は本環境では未確認。
- RBNは接続・ログイン・受信・停止を偽ソケットで検証。外部リレーへの実接続は未実施。接続先の配信設定に依存する。
- Windows GUI・システム通知音・PyInstaller・実機は未確認。依存追加なし（標準ライブラリと既存PySide6）。

## 全体実行でOK後に終了異常

- test_final9：exit -7
- test_final9_completion：exit -11
- test_log_merge_gui：exit -6
- test_pota_gui：exit -11
- test_regional_2026：exit -11
- test_remaining9：exit -7
- test_search_special_handoff_gui：exit -11

## 参照資料

- 国内公開XML構造 https://qrv.jp/help/xml.html
- 公開配信 https://qrv.jp/xml/All100.xml
- RBN接続説明 https://www.reversebeacon.net/pages/Telnet%2Bservers%2B30
- RBN対応リレー設定例 https://use.zlog.org/manual/Packet-Cluster%E9%80%A3%E6%90%BA.html

API自体を修復・再開したという意味ではない。403時は診断情報でWindows環境からの接続結果を確認できる。
