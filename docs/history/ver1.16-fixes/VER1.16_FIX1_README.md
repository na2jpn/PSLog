# PSLog Ver1.16 FIX1

基準: `PSLog_1.16_FULL_SOURCE.zip`

このZIPは **Ver1.16全装へ上書きする差分**です。Version番号は1.16のままです。

## 修正内容

- 「設定 → 無線機設定」を、機種名から選ぶ方式へ変更。
- 既知のICOM機は機種選択からCI-Vアドレスを自動設定。
- Yaesu / Kenwoodの対応機は機種選択からHamlib Model IDを自動設定。
- `その他ICOM` / `その他Hamlib対応機` の場合だけ、CI-Vアドレス / Hamlib Model IDを手入力可能。
- COMポートに `AUTO` を追加。検出ポートはデバイス名と説明を表示し、保存済みポートが見つからない場合も `（未検出）` として保持。
- 通信速度に `AUTO` を追加。
- `rigctld.exe` と `com0com setupc.exe` は空欄時に既知の場所やPATHから自動検出し、必要なら参照指定可能。
- 仮想COM中継を無線機設定内で独立して表示。CI-V時のみ有効。
- 「接続テスト」を追加。UIを止めず最大10秒で確認し、成功時はCOM・通信速度・周波数を表示。テスト終了後は保存済みの本接続へ戻す。
- AUTO指定時、CI-V / Hamlibとも検出済みCOMと候補速度から応答する組み合わせを探す処理を追加。
- 1.16旧設定（CI-Vアドレス / Hamlib Model ID直接指定）から、分かる機種は自動的に機種選択へ引き継ぐ。

## 仮想COMについて

仮想COMは従来のVer1.16仕様どおり、CI-V時のみ試験対応です。com0comドライバ自体はPSLogへ同梱・自動インストールしません。

## 適用方法

`PSLog_1.16_FULL_SOURCE.zip` を展開したフォルダーへ、このFIX1 ZIPの内容を上書きしてください。

## GPT側確認

- 変更Pythonファイルの構文確認 / compileall: OK
- FIX1追加テスト + 1.16無線機・Updater等の重点非GUIテスト: 35件 OK
- 全体 unittest discover: 527件実行、FAIL 0、69 ERROR、9 SKIP
- 69 ERRORはこのLinux検証環境にPySide6がないため読み込めないGUIテストのみ
- Windows実機のGUI表示、実無線機、AUTO接続、com0com中継は利用者側確認対象
