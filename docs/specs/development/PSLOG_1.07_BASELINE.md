# PSLog Ver1.07 Baseline

Ver1.07 canonical baseline is `PSLog_1.07_CANONICAL_SOURCE.zip`.
It supersedes the Ver1.06 canonical source, the Ver1.061–1.070 PATCH/FIX overlays, and the Ver1.069 contest-rule Work/handoff snapshots.

## Integrated Ver1.06 development line

- 1.061–1.068: existing amateur-radio UI/storage/export/rule-view improvements and compatibility fixes.
- 1.069: contest rule-view separation and large-scale display audit/cleanup for the registered 87-rule catalog.
- 1.070 PATCH10: contest-manager start-month labels and a standard submission-time band-order option.
- 1.070 FIX2: source/frozen-aware bundled-rule origin classification plus regression-test repair.
- 1.07 release: version/package canonicalization and history cleanup only; no additional functional rule was introduced after the accepted 1.070 + FIX2 behavior.

## Canonical invariants

- PSLog TXT remains 11 fixed fields.
- New TXT files are UTF-8 BOM + CRLF; compatible existing files may omit BOM.
- Dates/times in the PSLog master log are JST.
- RMKS2 remains encoded inside RMKS and does not create a 12th TXT field.
- Contest display information and scoring/submission enforcement are separate concerns.
- Registered rules: 86 contests + 1 QSO Party = 87.
- User data and backups must remain readable across normal upgrades.

## Ver1.07 release behavior

- Rule manager labels include contest start year/month.
- Submission page offers optional band/time sorting as a standard function.
- `event.submission.order=band_time` selects the initial checkbox state; it does not remove user control.
- 愛・地球博記念コンテスト uses the default-ON setting.
- Bundled-rule origin handling differentiates unmanaged source-mode same-name rules from modified bundled rules in distribution/frozen mode.

## Verification note

The user confirmed successful Windows build and startup for Ver1.070 PATCH10 + FIX2 on 2026-09-24. Canonicalization to 1.07 changes release/version metadata and documentation, while keeping that accepted functional state. See `VALIDATION.md`.
