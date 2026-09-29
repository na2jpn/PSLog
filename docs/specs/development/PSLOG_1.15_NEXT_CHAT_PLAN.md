# PSLog Ver1.15 — Next Chat Plan

Use `PSLog_1.15_FULL_SOURCE.zip` only. Do not reconstruct Ver1.15 by replaying older canonical sources, patches, or the Ver1.14 source.

## Development workflow

- Collect requirements first.
- Do not implement until the user explicitly requests implementation.
- `まとめ` means summarize/confirm only.
- Normal development after Ver1.15 begins with **1.151** unless the user explicitly chooses another version line.
- Deliver change-only ZIPs during development; create a new canonical source only when the user requests canonicalization.

## Preserve these Ver1.15 decisions

- One selected update ZIP only.
- Distribution root: EXEs and folders only; management metadata belongs under `meta/`.
- Ver1.15+ updater prefers `meta/versionup.json` and may manage future application folders/root EXEs while protected user-data roots stay untouchable.
- `meta/PSLOG_UPDATE_INFO.json` remains transition compatibility for older installed updater versions; do not casually remove it without planning the oldest supported upgrade path.
- In-app update history is maintained at `meta/UPDATE_HISTORY.txt`.
- Current-version UI must derive from `storage.VERSION`; avoid hard-coded current release numbers.
- QSL quick processing is a draft workbench: QSL marks/JCC/JCG/HIS QTH are written only by `保存`; `閉じる` discards the draft after the confirmation 「変更内容を保存せず閉じますか？」 when changes exist.
- Full edit remains available separately; do not expand the quick QSL workbench into a duplicate full editor.

All Ver1.14 amateur/free-radio compatibility invariants continue to apply.
