# PSLog Ver1.13 Baseline

Ver1.13 canonical baseline is `PSLog_1.13_CANONICAL_SOURCE.zip`. It supersedes the Ver1.10 canonical source and the Ver1.11/1.12 PATCH/FIX overlays.

## Integrated development line

- Ver1.10: QSL/JCC-JCG extensions, JCC/JCG award-check, centralized amateur log discovery, EASY two-page workflow.
- Ver1.11 PATCH01: first free-radio implementation: tabs, `logbook_flr`, type/model/year identity, type-driven BAND/MODE, cross-type LogSearch, free-radio search/edit, free menu, whole-backup/restore integration.
- Ver1.11 PATCH01 FIX1: stale regression-test expectations corrected; no runtime feature change.
- Ver1.12 PATCH01 FIX2: release version updated and Windows release filename made dynamic from `storage.VERSION`.
- Ver1.12 FIX1: free-radio create-dialog validation keeps the dialog open; model name is optional.
- Ver1.13 release: canonicalization of the accepted state; no additional business/UI feature beyond the accepted Ver1.12 FIX1 state.

## Canonical invariants

- PSLog TXT remains 11 fixed fields, UTF-8 BOM + CRLF for new files, JST master time.
- RMKS2 remains within RMKS; no 12th master-log field.
- `logbook/` is amateur-radio master-log storage; `logbook_flr/` is free-radio master-log storage.
- Amateur and free-radio discovery/search/edit paths remain separate.
- Contest display information and scoring/submission enforcement remain separate.
- Registered rule catalog remains 86 contests + 1 QSO Party = 87.
- User data/backups remain upgrade-safe.

## Free-radio baseline

- Free-radio tabs: max 4 simultaneously; unlimited logbook creation.
- Tab title: `[F]CALL TYPE`; selected accent is light blue.
- Identity: call + type + optional model; year is encoded by the log filename and follows QSO date.
- Calls: hiragana + ASCII letters/digits; Katakana normalized to hiragana.
- Types: CB, LCR, DCR, UHFCB, 特小, BLU, ETC.
- BAND/MODE are stored automatically per type and are not presented as primary free-radio search columns.
- Right-side LogSearch crosses all types for the same own call.
- Dedicated free-radio search/edit uses `logbook_flr/` only and requires an own-station selection.
- Whole-backup/restore includes free-radio logs.

See `docs/specs/data/FREE_RADIO_LOGGING.md` and `VALIDATION.md` for details.
