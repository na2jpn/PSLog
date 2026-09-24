# PSLog ログ保管先とログ種別の分離

## 目的

アマチュア無線ログとフリラログを、画面ごとのフォルダー走査で混在させないための基盤仕様。

## 保管先

- `logbook/` : アマチュア無線ログ
- `logbook_flr/` : フリラ専用ログ

PSLog起動時、上記2フォルダーが存在しなければ生成する。

## アマチュア取得経路

アマチュア無線ログを取得する場合、直接 `logbook/*.txt` を走査せず、`logbook_sources.py` の共通取得関数を使用する。

- `amateur_log_files(repo)` : 有効なPSLogアマチュアログファイルのみ
- `amateur_station_calls(repo)` : アマチュアログに実在する自局ベースコール一覧
- `file_identity(path)` : PSLogアマチュアログファイル名の解析
- `base_station_call(value)` : `/1`、`/P` 等を除いたベースコール

JCC/JCG交信チェック、アマチュア検索・集計等はこの系統だけを使用し、`logbook_flr/` を対象にしない。

## フリラ取得経路

フリラは `free_radio.py` の `free_files()` / `free_station_calls()` / `free_profiles()` 等を使用して `logbook_flr/` を取得する。アマチュア `logbook/` を対象にしない。

フリラファイル名は `YYYY_CALL_種類[_機種名].txt`。機種名は任意。詳細は `FREE_RADIO_LOGGING.md` を参照。

## 更新時の保護

`logbook_flr/` は `config/`、`logbook/`、`bak/`、`output/` と同様に更新パッケージの利用者データ領域として保護する。更新ZIPへ同領域の利用者ファイルを含めてはならない。

## バックアップ

Ver1.13では全体バックアップ/復元が `logbook/` と `logbook_flr/` の双方を対象とする。アマチュアログとフリラログの復元先を入れ替えない。
