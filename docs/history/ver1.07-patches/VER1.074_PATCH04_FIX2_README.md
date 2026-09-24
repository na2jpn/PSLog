# PSLog Ver1.074 PATCH04 FIX2

## 対象

Ver1.074 PATCH04 + FIX1 適用済み環境。

## 修正内容

Windows/PySide6でJCC/JCG交信チェックの集計結果を描画する際、都道府県の親行を全列スパン表示するために使用した `QTreeWidget.setFirstItemColumnSpanned(...)` がPySide6 Qt6には存在せず、次の例外で停止する問題を修正しました。

```text
AttributeError: 'PySide6.QtWidgets.QTreeWidget' object has no attribute 'setFirstItemColumnSpanned'
```

Qt6/PySide6で提供されている `QTreeWidgetItem.setFirstColumnSpanned(True)` を使用するよう変更しています。

## 変更しないもの

- VERSIONは1.074のままです。
- 集計ロジックは変更しません。
- ワーカースレッドによる非同期集計は維持します。
- Loading表示は維持します。
- 都道府県だけを先に描画し、JCC/JCG詳細を展開時に生成する遅延表示も維持します。

## Windows確認

```powershell
python -m unittest discover -v
```

特に `test_patch04_1074.Patch041074GuiTests.test_award_tree_builds_prefecture_children_only_when_expanded` が通ることを確認してください。

その後、JCC/JCG交信チェックで「集計」を押し、Loading後に都道府県一覧が表示され、県を展開するとJCC/JCG詳細が生成されることを確認してください。
