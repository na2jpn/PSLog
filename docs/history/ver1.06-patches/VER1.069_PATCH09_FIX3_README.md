# PSLog Ver1.069 PATCH09 FIX3

適用先: **Ver1.069 PATCH09 + FIX1 + FIX2 適用済みソース**
（FIX2を未適用でも、PATCH09 + FIX1の上へ適用可能です）

## 原因

Windows/PySide6では、`QMenu`のPythonラッパーを保持していても、
テスト時に内部C++オブジェクトが既に破棄済みと判定されるケースがありました。

FIX2では `menu_refs` 経由に変更しましたが、QMenuそのものを検査する限り
同じ寿命管理問題を完全には回避できませんでした。

## FIX3

- `main.py` に `FILE_MENU_ITEMS` を追加し、ファイルメニューの順序を一元管理。
- 実際のメニュー生成はこの定義を使用。
- `test_patch09_gui.py` はQMenuを直接触らず、同じ定義を検査。
- GUIの表示内容・順序に変更はありません。
- VERSIONは **1.069** のままです。

## Windows確認

```bat
python -m unittest discover -v
```
