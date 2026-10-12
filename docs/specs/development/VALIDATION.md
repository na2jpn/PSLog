# 検証範囲 — PSLog 1.16 正本

## 系譜
- `PSLog_1.16_FULL_SOURCE.zip` を基準にFIX1～FIX9を順に統合。
- 利用者のWindows実機でFIX9のcom0com仮想COM作成成功を確認し、正本化を指示。
- FIX1～FIX9は `docs/history/ver1.16-fixes/` に履歴保存し、今後は再適用しない。

## GPT側確認
- canonicalization時の `compileall`: OK。
- PySide6不要の無線機/仮想COM/保存リトライ関連回帰を実行。
- ZIP作成後にCRCを全件確認。
- `SOURCE_MANIFEST.json` にソースツリーhashと適用FIXのSHA-256を記録。

## Windows実機で確認された重要点
- CI-V物理接続と周波数取得。
- DTR/RTS安全化後、接続によるTX張り付き対策を実装。
- com0com作成時のUACとsetupc作業ディレクトリ問題をFIX9で解消。
- 利用者よりFIX9適用後「うまくいきました」と報告され、仮想COM作成成功を確認。

## 継続確認
- WSJT-X等の外部ソフトから仮想COM経由の長時間双方向運用。
- Hamlib各機種の実機差。
- Windows 10/11や異なるcom0com版での導入差。
