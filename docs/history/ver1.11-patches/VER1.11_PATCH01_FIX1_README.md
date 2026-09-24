# PSLog Ver1.11 PATCH01 FIX1

Base: PSLog Ver1.10 canonical source + PSLog_1.11_PATCH01.zip

This FIX only corrects two stale regression-test expectations found by the Windows full test suite.
No application/runtime source code is changed.

## Changes

- `test_patch10_1070.py`
  - Update the expected application version from `1.10` to `1.11`.
  - Reason: PATCH01 intentionally advances `storage.VERSION` to Ver1.11.

- `test_v101.py`
  - Update the contest wizard expected label to `（ユーザー定義）滋賀コンテスト（2026）`.
  - Reason: the current `RuleStore.display_label()` specification explicitly prefixes source-tree temporary/user rules as `（ユーザー定義）`; newer regression coverage already asserts this behavior.

## Classification

Both failures are stale tests, not runtime feature defects. Existing tests are preserved and updated to the current accepted specification; no test is removed or disabled.
