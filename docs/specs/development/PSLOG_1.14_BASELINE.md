# PSLog Ver1.14 Baseline

Ver1.14 canonical baseline is `PSLog_1.14_CANONICAL_SOURCE.zip`. It supersedes the Ver1.13 canonical source and the Ver1.14 diff overlay.

## Integrated development line

- Ver1.13: first practical free-radio layer: tabs, `logbook_flr`, type/model/year identity, type-driven BAND/MODE, cross-type LogSearch, free-radio search/edit, free menu, backup/restore integration.
- Ver1.14 diff: first-launch selector for amateur-radio vs free-radio callsign, free-radio-only startup, free-only setting separation, blank-model session restore, and prevention of free callsign inheritance into amateur tabs.
- Ver1.14 release: canonicalization of the user-accepted Ver1.14 diff state; no additional runtime business/UI behavior added during canonicalization.

## Canonical invariants

- PSLog TXT remains 11 fixed fields, UTF-8 BOM + CRLF for new files, JST master time.
- RMKS2 remains within RMKS; no 12th master-log field.
- `logbook/` is amateur-radio master-log storage; `logbook_flr/` is free-radio master-log storage.
- Amateur and free-radio discovery/search/edit paths remain separate.
- Free-radio-only startup must not overwrite the amateur `own` setting.
- Contest display information and scoring/submission enforcement remain separate.
- Registered rule catalog remains 86 contests + 1 QSO Party = 87.
- User data/backups remain upgrade-safe.

## First-start baseline

- Initial prompt is 「アマチュア無線のコールサイン」.
- User can switch to 「フリラのコールサイン」 and back.
- Free-radio first start asks for callsign, type, optional model, and automatic year.
- Free-radio first start replaces the initial empty standard tab with a free-radio tab.
- An amateur callsign is not required to begin using PSLog in free-radio mode.

See `docs/specs/data/FREE_RADIO_LOGGING.md` and `VALIDATION.md` for details.
