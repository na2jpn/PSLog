# PSLog Ver1.073 PATCH 03

基準: Ver1.072 PATCH02 適用済みソース

## 変更内容

### 1. JCG 5桁コードだけでも郡までHIS QTHへ反映

JCGの5桁コードは郡を表す情報として扱います。町村識別英字がない場合、所在地DBに同じJCGの町村が複数あっても、全該当行から共通する郡名を安全に確定できれば郡まで反映します。

例:

- `11002` → `Ashigarakami gun Kanagawa Japan`
- `16001` → `Agatsuma gun Gumma Japan`
- `16001H` → `Nakanojo Agatsuma gun Gumma Japan`（町村識別ありなので従来どおり詳細）

5桁だけの状態から特定の町・村を選ぶことはありません。現在の所在地DBから郡・支庁単位を安全に導けない例外は従来どおり自動確定しません。

この考え方は、過去ログに郡までしか記録されていないQSOが存在すること、およびJARLや多くのアワードでJCGは郡単位の情報が実用上の基準となることを踏まえたPSLogの所在地解釈方針です。町村名は詳細ログ用の追加情報とします。

対象:

- 交信編集 `JCC / JCG` → `HIS QTHへ反映`
- ログ一括処理JCC/JCG [A] `JCC/JCG → HIS QTH`
- ログ一括処理JCC/JCG [B] `RMKS → JCC/JCG + HIS QTH`

### 2. PATCH02適用後に表面化した4件の回帰テストFAILを修正

PATCH01でJARL R1.0/R2.1のメールアドレスをPSLog標準必須にしたため、古いGUIワークフローテストがメール未入力の状態で止まり、従事者資格・保存・衝突処理など本来確認したい後段へ到達できなくなっていました。

報告された以下の系統を現仕様へ合わせ、テスト入力へメールアドレスを追加しました。

- `test_contest_export.ExportTests.test_stage5_file_save_profile_and_invalidation`
- `test_contest_workflow.ContestWorkflowTests.test_all_formats_prepare_invalidate_save_and_collision` の JARL R1.0 / R2.1
- `test_contest_workflow.ContestWorkflowTests.test_jarl_r10_requires_licenseclass_in_ui_but_r21_does_not`

メール必須化そのものはPATCH01の仕様どおり維持し、機能側を任意へ戻してはいません。

## VERSION

- `storage.VERSION = 1.073`
- Windows配布ZIP: `PSLog_1.073_Windows_<timestamp>.zip`

## この環境での確認

- `python -m compileall -q .` : OK
- JCC/JCG / QSL / バックアップ / Windowsパッケージ関連 47件: OK
- `python -m unittest discover -v`: 464件を検出し、PySide6未導入によるGUI系69 ERRORのみ。assertion FAILは0件。

PySide6を使う今回修正対象のGUIワークフローテストは、このLinux環境では実行できないためWindows側の全テストで最終確認してください。

## Windows確認

Ver1.072へこの差分ZIPを上書きしてから:

```powershell
python -m unittest discover -v
.\build-windows.ps1
```

全テスト成功後、起動確認してください。
