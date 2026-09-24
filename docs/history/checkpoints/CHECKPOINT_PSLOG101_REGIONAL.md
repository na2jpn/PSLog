# PSLOG101 PSLOG101_remaining50

未作成・未検証の管理項目: **50 / 87**。異なる大会数や実装ステップ数ではありません。
今回の対象は71項目から50項目へ進める作業です。今回 21 管理項目・598 部門を実装・自動試験しました。
原案を一つに集めたファイルは pslog-1.01/docs/CONTEST_RESEARCH_ALL.md です。
定義作成済みと、全条件の主催確認・実機検証完了は別です。

## 今回の実装済み対象
- all_kushiro
- all_aomori
- ja9_hf_phone
- ja9_hf_cw
- ja9_vu
- all_ja5
- kamikawa_souya
- oshima_hiyama
- all_kumamoto
- iwate_winter
- nagasaki
- wakayama
- all_ja4
- all_tohoku
- niigata_low_band
- tochigi
- all_kyushu
- kagoshima
- all_kanagawa
- ja0_vhf
- oita

## 保持したもの

- PSLOG100からの原案・大会調査メモ・利用者確認・取得原典を保持。
- PSLog 1.01の11列TXT原本を変更せず、追加申告は提出作業データ。
- 元のOkayama時点ZIPも同梱し、すべての旧ファイルの存在を照合。
- 2026年版を2027へ自動更新しない。

## 検証と限界

----------------------------------------------------------------------
Ran 485 tests in 15.713s

OK


JARL出力はローカル自動試験です。主催者への送信・受付試験、Windows実機とEXE作成は行っていません。
地方規約で未記載の最低帯数、混合構成、本文/添付の指定等は、原案の保留記録を保持し独自に補っていません。
全体チェックログの受付可否も大会別の原典に従います。

## 再開箇所

台帳: docs/CONTEST_IMPLEMENTATION_TRACKER.json
原案: docs/contest-research/（各末尾の利用者確定事項を優先）
再生成: devtools/build_regional_2026.py
追加試験: test_regional_2026.py
共通処理: contest_regional.py
