# Source cleanup — 2026-09-16

The user supplied `PSLOG101(1).zip` as the latest source after the Windows test suite reported OK.
This cleanup created the canonical 1.01 source layout without changing application behavior.

## Removed generated material

- `build/`
- `dist/`
- `release/`
- all `__pycache__/` and `*.pyc`
- `windows-tests.txt`

These are regenerated and should not be used as source-of-truth inputs.

## Archived / reorganized

- old `README_WINDOWS_PATCH*.txt` -> `docs/history/windows-patches/`
- old `STATUS_1.00.txt`, `REMAINING_1.00.txt`, `CHANGES_1.01.md` -> `docs/history/development/`
- old checkpoint files -> `docs/history/checkpoints/`
- pre-Windows handoff material -> `docs/history/pre-windows-handoff/`
- current technical Markdown -> `docs/specs/<category>/`

Runtime/test-required source, config, templates, distribution rule packs, and regression tests remain in place.
