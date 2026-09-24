# PSLog Ver1.075 PATCH05 FIX1

## 対象

Ver1.075 PATCH05 適用済み環境。

## 修正内容

Windows/PySide6で `test_patch05_1075.py` のGUI回帰テストが、存在しない `main.Main` をimportしてエラーになる問題を修正しました。

PSLog本体のメインウィンドウクラスは従来どおり `main.Window` です。PATCH05のテストだけが誤って `Main` を参照していました。

- `from main import Main` → `from main import Window`
- `Main(self.repo)` → `Window(self.tmp.name)`

PATCH05本体の機能、VERSION、JCC/JCG集計、相手コールサイン太字化の実装内容には変更ありません。

## VERSION

`1.075` のままです。

## Windows確認

```powershell
python -m unittest discover -v
```

今回エラーになった `test_standard_and_contest_callsign_labels_and_inputs_are_bold` が通ることを確認してください。
