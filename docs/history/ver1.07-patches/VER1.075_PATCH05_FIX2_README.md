# PSLog Ver1.075 PATCH05 FIX2

## 対象

Ver1.075 PATCH05 + FIX1 適用済み環境。

## 修正内容

Windows/PySide6で `test_patch05_1075.py` のGUI回帰テストが停止する問題を修正しました。

FIX1で正しい `main.Window` を生成するようにした結果、テスト用の空ディレクトリには自局コール設定がないため、PSLog本体の正常な初回起動処理が働きました。

`Window.__init__()` は自局コール未設定時に `QTimer.singleShot(0, self.first_start)` を予約します。Qtのoffscreenテスト環境では、その後に開く初回起動 `QInputDialog` が画面上で確認できないままモーダル待ちとなり、時計用QTimerだけが動き続けるため、テストが止まったように見えていました。

今回の修正ではGUIテストの開始前に

```python
save_settings(self.tmp.name, {'own':'JH1HST'})
```

を保存してから `Window` を生成します。これにより実運用の初回起動処理には一切変更を加えず、テストでは対象の太字UIだけを検証します。

`This plugin does not support propagateSizeHints()` はQt offscreenプラグイン由来のメッセージで、今回の停止原因そのものではありません。

## VERSION

`1.075` のままです。

## Windows確認

```powershell
python -m unittest discover -v
```

`test_standard_and_contest_callsign_labels_and_inputs_are_bold` を含め最後まで完走することを確認してください。
