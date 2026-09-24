PSLog Ver1.04 PATCH 02 FIX2

対象:
  PATCH 01 + PATCH 02 + FIX1 適用済みソース

修正:
  build-windows.ps1 から
    python tools/package_windows.py ...
  と直接実行した場合、Pythonのモジュール検索パスが tools/ から始まり
  storage.py / update_package.py を見つけられず Packaging failed になる問題を修正。

内容:
  - tools/package_windows.py が実行時にPSLogソースルートを sys.path へ追加
  - 実際に tools/package_windows.py を別作業ディレクトリから直接起動して
    更新ZIPを生成する回帰テストを追加

確認:
  test_windows_package.py + test_update_package.py: 8 tests OK
  python tools/package_windows.py --help: OK
