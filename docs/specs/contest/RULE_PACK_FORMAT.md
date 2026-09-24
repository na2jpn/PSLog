# PSLogルールパック形式 1

## 利用
コンテストルール管理・編集 → ルールパックを取り込む… → ZIP選択 → 一覧確認 → 追加・更新。
同じIDと年度で照合。過年度ファイルは残す。手動編集済み、配布履歴なし、同じ改訂の異なる内容、旧改訂は競合として表示。競合ごと「現在のものを残す／配布版に更新」。取り込みエラーはZIP全体を反映しない。
更新途中の失敗後は画面を閉じ再読込する。未知の外部変更で復旧が止まった場合はconfig/rules/historyと.pack-pending.jsonを保持して確認する。復旧記録を削除して強行しない。

## ZIP内容
ルートmanifest.jsonとrules/<id>_<year>.txtのみ。ディレクトリエントリ不要。実行プログラム、任意フォルダ、リンク、暗号化ファイルは不可。最大500ルール、各1MiB、展開合計32MiB。

manifest.json例（sha256は実際のバイト列から計算）:

```json
{"schema":1,"pack_id":"pslog-20260914","rules":[{"file":"rules/example_2026.txt","id":"example","year":2026,"revision":1,"minimum_version":"1.01","sha256":"実際の64桁のハッシュ"}]}
```

ルール本文は既存のPSLog JSONルール形式。schema=1/2のいずれか。配布改訂番号は正整数。ルール本文とは別にmanifestで管理する。必要バージョンは1.01のような二桁小数表記。SHA-256は誤破損検出であり作者認証・署名ではない。

配布者向けCLI:

```bash
python publish_rule_pack.py rules-20260914.zip config/rules/example_2026.txt --pack-id pslog-20260914 --revision 1 --minimum-version 1.01
```

既存の同名ZIPを上書きしない。複数ルールで異なる改訂を持つ場合はrule_pack.build(path, [(rule, revision, minimum_version), ...], pack_id)を使用する。
旧本体1.01でもschema=2未対応ビルドでは読み込めない。現行は同じ1.01開発途中のため、公開時は実際の機能を備える配布バージョンをminimum_versionに設定する必要がある。

## 拡張ルール形式2
旧ルールのschemaを2にし、multi1.kindをoffにする。scoringを追加:

```json
{"eligible":{"all":[]},"multipliers":[{"id":"region","source":"exchange","kind":"whole","start":0,"length":2,"per_band":true,"when":{"all":[]}}],"bonus":0}
```

eligibleは交信の採点対象条件。multiplier.whenは個々の集合の条件で、交信点0でも数える。DUPと対象外は数えない。sourceはexchange/area/prefix/country/continent。kindはwhole/digits/slice。識別子は集合ごと異なるものを使う。
formula=totalでは全交信点×全マルチ数×第二マルチ＋bonus。band_sumではバンド別積を合計後に第二マルチを掛け、bonusを加算する。band_sumの全集合はper_band=true必須。
bonusは固定申告値。移動資格・参加条件を自動検証するものではない。大会別の条件付き加点は別の実装が必要。
