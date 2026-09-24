# PSLog Ver1.14 — Next Chat Plan

## Baseline

Use `PSLog_1.14_CANONICAL_SOURCE.zip` only. Do not replay the Ver1.14 diff or older PATCH/FIX artifacts.

## Numbering

The next ordinary development patch is expected to begin at **1.141** unless the user explicitly chooses another number.

## Development rules

- Accumulate requirements first.
- Do not implement until the user explicitly says `実装` or otherwise clearly requests implementation.
- `まとめ` means summarize/confirm only.
- Deliver changed files only as a diff ZIP for development patches.
- Keep PSLog TXT at 11 fixed fields and preserve old logs/backups.
- Keep `logbook/` and `logbook_flr/` routing separate.
- Reuse common storage/edit logic where safe rather than duplicating equivalent behavior per screen.
- Windows full tests, GUI checks, and PyInstaller build are performed by the user; GPT performs available non-GUI regression, compile, overlay, and manifest checks.
- If an older regression test fails, classify product defect vs stale test before changing it. Do not delete tests merely to make the suite pass.

## Free-radio continuation

Ver1.14 supports free-radio-only first startup. Continue free-radio work incrementally without forcing amateur-specific QSL/contest/award workflows into free-radio screens unless explicitly requested.
