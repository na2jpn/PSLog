# PSLog Ver1.10 — Next Development Plan

## Baseline

Always start from `PSLog_1.10_CANONICAL_SOURCE.zip`. Do not replay Ver1.07-series patches.

## Version flow

- first normal patch: Ver1.101
- continue Ver1.10x as needed
- next canonical version: follow the user's explicit instruction (normally Ver1.11)

## Workflow rule

Collect requested changes first. Do not implement while the user is still listing requirements. Implement only after an explicit instruction such as `実装`. `まとめ` means summarize/confirm only. Deliver only changed files as a differential ZIP until the next canonicalization.

## Major carried-forward theme

Full free-radio support is still deferred. `logbook_flr/` and logbook routing infrastructure are groundwork only. Do not mix free-radio records into amateur `logbook/` or the amateur 11-field PSLog master format without an explicit agreed design.
