# PSLog Ver1.076 PATCH06

## 基準

Ver1.075 PATCH05 + FIX1 + FIX2 適用済みソース。

## 実装内容

### 1. EASYタブ 第1段階

- `＋タブ` メニューへ **「EASYタブを追加」** を追加。
- EASYタブは同時に **最大2枚**。2枚開いている場合は追加メニューを無効化する。
- 今回はEASY専用の簡略画面へ進む前段として、**標準タブと同じ交信画面・同じログ保存処理**を使用する。
- EASYタブの自局コール未設定時の表示名は `EASYタブ`。
- 自局コール設定後は `JH1HST` → `[E]JH1HST` の形式で表示する。ログファイル付与文字がある場合は標準タブと同様に末尾へ付与する。
- EASYタブもセッション保存、再起動後の復元、最近閉じたタブからの再表示に対応する。
- 標準タブ最大5枚、コンテストタブ最大6枚の既存制限は変更しない。

### 2. JCGの郡名ローマ字表記

- HIS QTH所在地補助やJCC/JCGコードからの所在地反映で、JCGの郡名を `Ina gun` のように分離せず **`Inagun`** のように連結して表示する。
- 例: `16001` → `Agatsumagun Gumma Japan`、`16001H` → `Nakanojo Agatsumagun Gumma Japan`。
- 配布参照DB内部の機械生成値は互換性維持のため変更せず、人間向けの候補・反映時に正規化する。

### 3. 標準系QSO記録後の相手所在地クリア

- 標準タブでQSOを正常保存した直後、前QSOの **HIS QTH** と **JCC/JCG** を入力欄から消去する。
- **MY QTHは保持**する。
- EASYタブは今回標準画面を共用するため、同じ安全動作になる。

## VERSION

`1.076`

Windows配布名は `PSLog_1.076_Windows_YYYYMMDD-HHMMSS.zip`。

## テスト

- Linux/非GUIの関連回帰 68件: OK。
- `python -m unittest discover -v`: 484件検出、assertion FAIL 0。69 ERRORはこの確認環境にPySide6が無いことによるGUI系ImportError、6件SKIP。
- Windowsでは `python -m unittest discover -v` を完走させた後、EASYタブ追加・2枚制限・タブ名、JCG補助表記、QSO記録後のHIS QTH/JCCJCG消去をGUI確認すること。
