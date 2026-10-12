# PSLog Ver1.16 FIX2

基準: `PSLog_1.16_FULL_SOURCE.zip` に `PSLog_1.16_FIX1_DIFF.zip` を適用した状態。

## 修正内容

無線機設定/接続を行っただけで送信状態(TX)が保持される可能性がある問題を修正しました。

### CI-V / pySerial

- 物理COMを開く前に DTR / RTS を明示的に OFF にします。
- RTS/CTS および DSR/DTR のハードウェアハンドシェイクを使用しません。
- AUTO接続探索、通常接続、接続テストで使用するCI-Vプローブをすべて同じ安全なCOMオープン処理へ統一しました。
- 仮想COM内部側も同じ安全なオープン処理を使用します。

### Hamlib

- `rigctld` 起動時に PTT方式を `NONE` とします。
- `dtr_state=OFF,rts_state=OFF` を明示して、PSLogの情報取得接続だけでDTR/RTSがPTTとして動作しないようにします。

PSLogはVer1.16時点では無線機のPTTを操作しません。

## 追加テスト

`test_radio_safety_fix2.py`

- DTR/RTSがCOM open前からOFFになっていること
- Hamlib起動引数でPTT NONE、DTR OFF、RTS OFFを指定していること

## Windows実機確認

1. 無線機側でRTS/DTRがSEND/PTTに割り当てられている環境でも、PSLogの「無線機接続を使用する」を有効にしただけでTXにならないこと。
2. 「接続テスト」を押してもTXにならないこと。
3. AUTO COM / AUTO baud探索中もTXにならないこと。
4. CI-Vで周波数取得が従来どおり行えること。
5. Hamlib機でも接続しただけでPTTが入らないこと。
6. 仮想COM中継ON時も、PSLog自身のポートオープンでPTTが入らないこと。
