# PSLog Ver1.10 Baseline

Ver1.10 canonical baseline is `PSLog_1.10_CANONICAL_SOURCE.zip`. It supersedes the Ver1.07 canonical source and all Ver1.071–1.078 PATCH/FIX overlays.

## Integrated development line

- 1.071: contest submission required email, Ai-Chikyu JST regression, layout tightening, contest power display correction.
- 1.072: safe RMKS1 parsing for JCC/JCG batch processing and optional JCC/JCG in QSL batch TXT.
- 1.073: JCG code-only county-level location support.
- 1.074: QSL quick processing, QRZ.R/CARD.R, JCC/JCG award-check view, centralized amateur-log discovery, `logbook_flr` reservation; FIX1/FIX2 added async loading/lazy tree rendering and corrected Qt6 API usage.
- 1.075: award-check CFM remaining counts and callsign emphasis; FIX1/FIX2 repaired GUI regression tests without changing runtime behavior.
- 1.076: EASY tab foundation, JCG `gun` joining, post-save HIS QTH/JCCJCG clear.
- 1.077: dedicated two-page EASY input and renewed About screen.
- 1.078: EASY `バンド（MHz）` label and green group-box accent.
- 1.10 release: version/package/document canonicalization; no new business logic beyond accepted 1.078 state.

## Canonical invariants

- PSLog TXT remains 11 fixed fields, UTF-8 BOM + CRLF for new files, JST master time.
- RMKS2 remains within RMKS; no 12th master-log field.
- `logbook/` is amateur-radio master-log storage. `logbook_flr/` is reserved for future free-radio and is excluded from amateur-only aggregation.
- Contest display information and scoring/submission enforcement remain separate.
- Registered rule catalog remains 86 contests + 1 QSO Party = 87.
- User data/backups remain upgrade-safe.

## EASY baseline

- EASY tabs: max 2, `[E]CALL`, no separate log format.
- Same PSLog storage engine as standard tabs.
- Right-side LogSearch retained; left side has 1/2 and 2/2 pages.
- Register-time 5-minute time-difference decision is explicit.
- On successful register, Band/Mode/Sub/My QTH persist; other-station fields clear.

See `VALIDATION.md` for release verification.
