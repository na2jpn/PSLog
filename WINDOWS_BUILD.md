# Windows配布準備 — PSLog 1.24

Python 64bit / PySide6 6.8.3 / PyInstaller 6.16.0。必要な依存関係は事前に `pip install -r requirements.txt` で揃えてください。ビルドスクリプトは自動インストールしません。

## 署名なしでビルドする場合

証明書を設定していない環境では、従来どおりビルドできます。

```powershell
powershell -ExecutionPolicy Bypass -File .\build-windows.ps1
```

環境変数に証明書が設定されている場合も、次の指定で署名を省略できます。

```powershell
powershell -ExecutionPolicy Bypass -File .\build-windows.ps1 -NoSign
```

この場合は未署名の開発用ビルドであることを画面に表示します。公開版の署名は次の方法で行ってください。

## 証明書で署名する場合

PSRTTYと同じWindows証明書ストア方式です。コードサイニング証明書と秘密鍵にアクセスできるWindows環境（Certum等のトークンや署名サービスを含む）およびWindows SDKのSignToolが必要です。秘密鍵やPIN・パスワードはソースに保存しません。証明書側でPIN等が求められる場合は、その署名サービスの画面で入力してください。

```powershell
powershell -ExecutionPolicy Bypass -File .\build-windows.ps1 -Sign -CertificateThumbprint "証明書の40桁の拇印"
```

- `-CertificateThumbprint` または環境変数 `PSLOG_SIGN_CERT_THUMBPRINT` に40桁の拇印を指定すると署名します。設定なしでは署名を省略します。
- `-Sign` を明示して拇印が未指定なら、未署名へ切り替えずエラーで停止します。証明書・秘密鍵へのアクセスや署名検証で失敗した場合も停止します。
- `-NoSign` は環境変数より優先します。`-Sign` と `-NoSign` の同時指定はエラーです。
- `-SignToolPath` / `PSLOG_SIGNTOOL` でSignToolのフルパスを指定できます。省略時はPATH、次いでWindows SDKの新しいx64版から検索します。
- `-TimestampUrl` / `PSLOG_TIMESTAMP_URL` でRFC 3161サーバーを指定できます。初期値は `https://timestamp.digicert.com`。
- ローカルコンピューターの証明書ストアを使う場合は `-MachineCertificateStore` を指定します（通常は現在のユーザー）。

署名対象は配布する `pslog.exe` と `exec/PSLogUpdater.exe`。SHA-256で署名し、SHA-256タイムスタンプを付け、`signtool verify /pa /all /tw /v` で検証します。失敗・警告があればZIP作成を止めます。署名した後にハッシュと更新マニフェストを生成するため、作成済みZIPの中のEXEだけを差し替えないでください。

本体と更新用EXEには共通のバージョン・著作権表示をWindowsファイル情報として付与します。著作権表示は `Copyright (c) 2026 Hiroshi Tanaka (JH1HST)` です。ライセンス文書は従来の配布用docsと内部リソースへ同梱します。

## 出力と確認

スクリプトは依存関係確認、全テスト、EXE生成、実EXEの自己確認、署名（指定時）・検証、配布ZIP作成の順で実行します。

出力: `release/PSLog_1.24_Windows_<timestamp>.zip`

既存のreleaseや個人データは消去しません。Windowsのファイルプロパティで本体・更新用EXEのデジタル署名と詳細情報を確認してください。署名なしの開発ビルドと、証明書を使う公開ビルドの両方をWindowsで確認する必要があります。

SignToolの仕様: https://learn.microsoft.com/en-us/windows/win32/seccrypto/signtool

---

以下は旧版から継承する実機確認項目です。

# Windows配布準備 — PSLog 1.17

## ビルド前

1. `pip install -r requirements.txt` を実行し、PySide6 / PyInstaller / pyserial等を揃える。
2. `storage.VERSION` が `1.17` であることを確認。
3. `meta/UPDATE_HISTORY.txt` の先頭がVer1.17であることを確認。
4. `python -m unittest discover` を実行し、Windows GUIテストを含め確認。
5. `powershell -ExecutionPolicy Bypass -File .\build-windows.ps1` でビルド。

配布ZIP名は `storage.VERSION` から自動取得し、`PSLog_1.17_Windows_<timestamp>.zip` となります。

## Ver1.16追加依存

- `pyserial` はCI-V直接接続とCOM列挙に使用し、PyInstallerへ同梱。
- Hamlib方式は利用者環境の `rigctld.exe` を使用。PSLog配布物へHamlibを同梱しない。
- 仮想COM試験機能はWindowsへ既に導入済みのcom0com `setupc.exe` を使用。PSLog配布物へcom0comカーネルドライバを同梱/自動導入しない。

## Windows実機重点

- CI-V: 接続/切断、起動時自動接続、周波数追従、無線機未接続時もPSLog継続。
- Hamlib: rigctld起動/終了、Model ID、周波数追従。
- 自動セット: 標準/EASY/コンテスト、RMKS1/RMKS2/Band、MODE不変、フリラ非適用。
- 仮想COM: OFF初期値。物理COM8なら外部COM208/内部COM209、競合時COM308/309等。作成/削除時だけUAC、通常終了では常設ペアを削除しない。外部ソフト双方向CI-Vと中継中の周波数追従を確認する。
- コンテスト非数値RST: 編集およびQSL簡易処理後に元値を保持して保存できる。

Ver1.15の1-ZIP updater構造と利用者データ保護も従来どおり確認します。

## Ver1.17のWindows確認

- コンテスト欄が左：自分／右：相手になり、記録後も自分の番号を保持。複数コンテストタブ、並べ替え、再起動で混在しない。
- 周波数RMKS2自動セットON/OFFで自分の番号を消さず、相手の番号へ周波数を書かない。
- JH1HST/1から全件表示を開くとJH1HSTを選択し、そのコンテストの移動先TXTが表示される。
- テスト用の別フォルダーで、記録中にTXTへ正規行を手動追加。次の記録が止まり、入力が残り、再読込後に再度記録すると全件残る。
- 同様にTXT置換・削除・形式不正・新規追加を試す。SETやタブ切替だけではログの内容を書き換えない。
- bakに置換前の全体があり、Windowsの一時ロックでも再試行中の外部変更を無視しない。
- 旧データフォルダーへの更新でlogbook/logbook_flr/config/bakを保持。配布ZIP直下はEXEとフォルダーだけ。
