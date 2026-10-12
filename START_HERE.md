# PSLog Ver1.16 — Canonical Source

基準ZIP: `PSLog_1.16_CANONICAL_SOURCE.zip`  
正本化日: 2026-10-13 / VERSION: **1.16**

このZIPがVer1.16の唯一の正本です。Ver1.16初期全装へFIX1～FIX9を積み直さず、今後は必ずこのZIPから開始してください。

## 読む順序

1. `START_HERE.md`
2. `HANDOFF.md`
3. `NEXT_CHAT_PROMPT.md`
4. `docs/specs/development/PSLOG_1.16_BASELINE.md`
5. `docs/specs/data/FREE_RADIO_LOGGING.md`
6. 必要に応じて `docs/INDEX.md`

## Ver1.16で確定した主な内容

- 1台分の無線機情報取得を追加。通常は機種名、COMポート、通信速度を選択し、ICOMはCI-V、対応Yaesu/Kenwood等はHamlib (`rigctld`) を内部で選択する。
- 設定済みなら起動時自動接続。失敗してもPSLog本体は通常利用可能。接続テスト、通常接続/切断、メイン画面からの接続/切断に対応。
- `＋タブ`右に周波数表示。接続時は `7.012MHz` 等を緑・ボールド・従来比+2pt、未接続は `-.--MHz` を薄灰で表示。
- HIS CALLSIGN RETURN時の自動セット: RMKS1 / RMKS2 / Band（初期OFF）。MODEは変更しない。コンテストではRMKS1を保護し、フリラでは自動セットを使わない。
- CI-V用の1系統仮想COM中継を追加。外部ソフト → 常設仮想COM → PSLog → 物理COM → 無線機。Ver1.16ではHamlib経由の仮想中継は行わない。
- 仮想COMは既に導入済みのcom0comを使用。例: 物理COM8なら外部 `COM208` / PSLog内部 `COM209`、競合時は `COM308/309` のように+100。
- 仮想COMは**常設方式**。作成/削除時だけUACを要求し、通常の接続/切断やPSLog終了ではCOMデバイス自体を削除しない。
- `setupc.exe` はProgram Files / Program Files (x86) / PATH等から検出し、管理者実行時も必ずsetupc.exeのフォルダーを作業ディレクトリにしてcom0com INFを正しく参照する。
- COMオープンではDTR/RTSを事前にOFF、ハンドシェイクも無効にし、情報取得だけで意図せず送信状態へ入らないよう安全化。
- Windowsの一時的なファイルロックに対し、原本更新の `os.replace` を短いバックオフ付きで再試行する。永続権限エラーや外部変更は握りつぶさない。
- コンテスト由来の既存交信編集では、RST欄相当へ非数値の交換情報が入るケースを保持して保存可能。通常QSOの入力検証は維持。

FIX1～FIX9の履歴は `docs/history/ver1.16-fixes/` に保存しています。適用済みであり、今後の再適用対象ではありません。
