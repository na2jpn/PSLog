# PSLog 1.19 FIX5

## 原因と変更

MicLookupDialog.finishedがQDialog.finished(int)と衝突し、w.finished.connect(self.finished)でRuntimeError: Failed to connect signal "finished()" to signal "finished(int)"。w.start()へ到達せず「照会中」のままになることを再現した。worker_finishedへ改名して解決。
提供index(9).phpのja_station_loc（2025-1新システム）を比較し、SK=2/DA=0、Referer、Content-Typeを共通API取得処理へ適用。User-Agentは依頼に従いChrome155。URL末尾の意味不明な&UTF-8は追加しない。tdfkCdの所在地文字列を、完全一致したコールのレコードから読み取り、既存所在地DBへ最長一致で対応する。既存詳細応答も扱う。海外や移動局の一括補完条件・レビュー前提は維持。
通信はdaemonスレッド内で行い呼出側のqueue待ちを15秒に制限。15秒後の応答は適用しない。通信実処理が残った場合はSemaphoreで多重呼出しを禁止。DNS等の基底処理の強制中断は行わない。Qt画面は通信処理を所有せず、待機終了後に入力と照会ボタンを復帰する。

## 検証

新規6件：提供PHPとのパラメーターとヘッダー比較、鴨川市→Kamogawa Chiba Japan/JCC1223、鶴居村→JCG01001B、誤ったコールと数字だけの都道府県の排除、総時間上限・遅着・重複リクエスト抑止、URL・経過・例外詳細、実QThreadを使った照会開始とタイムアウト・画面復帰。
既存関連37件OK。全体1,053件の判定OK（49.937秒）。判定表示後にLinux offscreenのQt終了異常SIGSEGV（exit139）が発生。新規6件は別プロセスで終了コード0。全体unittestの結果はdocs/validation/v1.19_fix5_unittest.txt参照。
提供PHPと同じFirefox75/Referer/Content-Type、SK=2/DA=0、URL末尾&UTF-8を含むJH1HSTの実通信を1回行ったがHTTP403（5.81秒）。この環境で取得成功は未確認。公式説明ページも403のため現在仕様の公式裏付けは取得できていない。
Windows実ビルド・実通信は未確認。新規の所在地テストは用意した応答によるもので実API応答ではない。
