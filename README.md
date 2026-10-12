# PSLog Ver1.16 Canonical Source

このツリーはVer1.16初期全装へFIX1～FIX9を統合した**Ver1.16正本**です。今後の開発は `PSLog_1.16_CANONICAL_SOURCE.zip` から開始してください。過去FIXの再適用は不要です。

## 最初に読む

1. `START_HERE.md`
2. `HANDOFF.md`
3. `NEXT_CHAT_PROMPT.md`
4. `docs/specs/development/PSLOG_1.16_BASELINE.md`

## Ver1.16 highlights

- 1台分の無線機周波数情報取得（ICOM CI-V / Hamlib rigctld）。
- 機種選択、AUTO COM/baud、接続テスト、接続/切断、起動時自動接続。
- メイン画面にMHz小数3桁の周波数表示とRMKS1/RMKS2/Band自動セット。MODEは変更しない。
- CI-Vの1系統仮想COM中継。com0comで外部/内部とも通常COM番号を持つ常設ペアを作り、作成/削除だけUACを使用。
- 物理COM8ならCOM208/COM209、競合時はCOM308/309…と+100。
- DTR/RTSを安全側へ固定し、情報取得だけで意図せず送信状態へ入らないようにした。
- Windows一時ファイルロック時の原本置換リトライを追加。
- コンテスト既存交信編集で非数値RST/交換情報を保持可能。

仮想COMはVer1.16ではCI-Vのみです。PSLogはcom0comやHamlibを同梱しません。FIX1～FIX9の履歴は `docs/history/ver1.16-fixes/` を参照してください。
