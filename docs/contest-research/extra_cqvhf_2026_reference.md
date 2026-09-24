# CQ VHF アナログ／デジタル（2026）

<!-- CURRENT_IMPLEMENTATION_STATUS_START -->
> **現在の実装状態（Ver1.02 文書整理 / 2026-09-16）: 実装済み**
>
> - CQ VHF SSB/CW/FM (`cq-vhf-ssbcw`, 2026)
>   - 実行定義: `config/rules/cq-vhf-ssbcw_2026.txt`
>   - 現行監査: 12種目、GL4・Roverグリッド別の重複/マルチ、レポートなしCabrillo3。相手Roverは/R表記を必要とする。 主催受付・Windows実機未検証。
> - CQ VHF Digital (`cq-vhf-digi`, 2026)
>   - 実行定義: `config/rules/cq-vhf-digi_2026.txt`
>   - 現行監査: 既知モードに加え任意入力を処理。原モード保持、CabrilloではDG。主催判断。
> - PSLOG101最終監査: **定義済み87 / 未定義0、全体回帰554件合格**。
> - Ver1.01正本はWindows上の全unittestがOKになった状態で受領済み。大会ごとのWindows実機操作・EXE・主催者受付確認は、監査記載どおり別確認です。
>
> **この下に残る「未実装」「未検証」「本体未対応」等は、調査・設計開始時点の履歴です。現在状態の判定には使用しません。**
> 現在状態はこの欄と [`docs/IMPLEMENTATION_STATUS.md`](../IMPLEMENTATION_STATUS.md)、および現行コード・回帰テストを優先してください。
<!-- CURRENT_IMPLEMENTATION_STATUS_END -->
調査台帳登録済・未実装。主催：CQ WW VHF Contest Committee。
規約：https://cqww-vhf.com/rules/
形式：https://cqww-vhf.com/cabrillo.htm
保存：sources/cqvhf_rules_2026.*、cqvhf_cabrillo.*。

## 規約の中核
アナログ7/4 14:00～7/5 14:00UTC、デジタル7/18 14:00～7/19 14:00UTC。50/144MHz。前者SSB/CW/FM、後者FT4/FT8/MSK144/Q65等。
4桁GL交換。レポート不要・提出ログにも入れない。50MHz1点、144MHz2点。バンドごとの相手GL数合計×交信点合計。
Roverの新GL移動で交信・マルチが新しくなる。相手RoverもGL移動後再交信可。Roverは各運用GLの点とマルチをそれぞれ合計して最後に掛ける。
SO1500/100/10W（QRPは10W）。HilltopperはSO移動、ALL、連続6時間、100W以下。Roverは最大2名、複数GL、/R等。MOあり。各部門とも両バンド同時送信可・同一バンド1信号。
締切アナログ7/10、デジタル7/24。衛星・中継・航空移動交信は無効。GL変更には全設備100m以上移動。境界では1GL選択。

## 出力と設計
CONTEST=CQ-VHF-SSBCW又はCQ-VHF-DIGI。ヘッダーMODEはSSB/CW/FM/MIXED/DG、行はPH/CW/FM又はDG。RST欄のない専用行。QSOごと送受GL。周波数欄はVHF帯番号50/144を扱う。EMAIL必須。
重複キーは相手コール＋実バンドに加え、相手RoverのGL、自局RoverのGLを条件付きで含める。モードが変わっただけで再得点しない。GL6桁入力は原値保持し交換・集計4桁へ。先頭2字マルチのWW DIGIと混同しない。
Rover集計を運用地別(points×multis)の合計にすると誤り。確認画面に自局GL別内訳と総積を表示する。100m移動は4桁GLだけでは判定できず本人確認が必要。同じGLへ戻っただけで新マルチを生成しない設計。
補助使用・完了通知の扱いは規約固有でありCQWWの禁止設定を流用しない。主催ADIF変換は固定局向けと記載され、Rover対応の根拠にしない。
公開前残件：期限の時刻・期間終了端の扱いを形式検証時に照合。推測時刻を確定規約として格納しない。

## PSLOG101 残り9目標・途中実装記録

12種目、GL4・Roverグリッド別の重複/マルチ、レポートなしCabrillo3。相手Roverは/R表記を必要とする。 全体514試験合格。原ログ11列・原案・原典不変。主催受付とWindows実機未検証。

## PSLOG101 残り9目標・途中実装記録 cq-vhf-ssbcw

12種目、GL4・Roverグリッド別の重複/マルチ、レポートなしCabrillo3。相手Roverは/R表記を必要とする。 全体525試験合格。原ログ11列・原案・原典不変。主催受付とWindows実機未検証。

## PSLOG101 残り9目標・途中実装記録 cq-vhf-digi

12種目、GL4・Rover・レポートなしCabrillo3。FT4/FT8/MSK144/Q65対応、他のデジタル型式は追加検証待ち。 全体525試験合格。原ログ11列・原案・原典不変。主催受付とWindows実機未検証。
