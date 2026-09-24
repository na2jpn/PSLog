# PSLog Ver1.07 — Development Plan to Ver1.08

## Baseline

Always start from `PSLog_1.07_CANONICAL_SOURCE.zip`. Do not replay Ver1.06-series patches.

## Version flow

- first normal patch: Ver1.071
- continue Ver1.07x as needed
- final target in this development cycle: Ver1.08 canonical source

## Workflow rule

Collect requested changes first. Do not implement while the user is still listing requirements. Implement only after an explicit instruction such as `実装`. Deliver only changed files as a differential ZIP until the next canonicalization.

## Major carried-forward theme

Full free-radio (フリラ) support remains a major candidate for the Ver1.07 development line. Existing amateur-radio behavior is the compatibility baseline. Do not force free-radio data into the 11-field amateur PSLog TXT format without an explicit, agreed storage design.

Existing groundwork/preferences from earlier planning may be reused only after checking the current user request; do not silently implement deferred items.
