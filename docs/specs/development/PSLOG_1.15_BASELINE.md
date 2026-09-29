# PSLog Ver1.15 Baseline

Ver1.15 full-source baseline is `PSLog_1.15_FULL_SOURCE.zip`. It supersedes the Ver1.14 canonical source for future development.

## Ver1.15 integrated changes

### Update architecture

- The user still selects **one Windows ZIP only** from `ヘルプ → PSLogをバージョンアップ`.
- The distribution root remains intentionally clean: direct files are EXEs; all other managed content belongs in folders.
- `meta/versionup.json` is the Ver1.15+ forward-looking update manifest.
- The manifest can name additional application-managed top-level folders or root EXEs, so future releases may add DLL folders, helper EXEs, or other application files without redesigning the updater.
- `config/`, `logbook/`, `logbook_flr/`, `bak/`, and `output/` remain protected user-data roots and cannot be managed or removed by the update manifest.
- `remove_roots` is available for an explicitly retired application-managed root. Removal participates in the same rollback transaction as replacement.
- Update files are staged and hash-checked before install. Replaced/removed roots are moved to a same-volume rollback directory; a failed post-install check restores the previous state.
- The external updater is copied to a temporary folder before PSLog exits, so the installed updater itself can be replaced.
- The Ver1.15 Windows package also carries the legacy `meta/PSLOG_UPDATE_INFO.json` compatibility manifest so an installed Ver1.14 updater can install Ver1.15. Ver1.15+ prefers `meta/versionup.json` when present.
- `meta/UPDATE_HISTORY.txt` is packaged with the application and provides the in-app release history.

### Update history / version display

- `ヘルプ → PSLogの更新履歴` is placed immediately above `PSLogについて`.
- The release history covers Ver1.01 through Ver1.15; Ver1.00 is folded into the Ver1.01 initial-release entry.
- Application-visible current version text uses the shared `storage.VERSION` value. The user guide heading was also changed to use the shared version instead of a release literal.

### QSL quick workbench

- The compact QSL screen remains intentionally smaller than the full edit screen.
- In addition to QSL receipt buttons it now provides editable `JCC / JCG` and `HIS QTH` fields plus `HIS QTHへ反映`.
- QSL button presses, JCC/JCG edits, and HIS QTH edits change an in-memory draft only.
- `保存` writes RMKS/QSL marks, JCC/JCG, and HIS QTH together to the selected source QSO and then closes the dialog.
- `閉じる` closes without writing the draft; when the draft has changes it asks 「変更内容を保存せず閉じますか？」 first.
- Existing shared JCC/JCG → HIS QTH resolution is reused; no duplicate location-resolution implementation is introduced.

## Canonical invariants

- PSLog TXT remains 11 fixed fields; new files use UTF-8 BOM + CRLF and log time remains JST.
- RMKS2 remains inside RMKS; no 12th master-log field.
- `logbook/` is amateur-radio master-log storage; `logbook_flr/` is free-radio master-log storage.
- Amateur and free-radio discovery/search/edit paths remain separate.
- Free-radio-only startup must not overwrite the amateur `own` setting.
- Contest display information and scoring/submission enforcement remain separate.
- Registered rule catalog remains 86 contests + 1 QSO Party = 87.
- User data/backups remain update-safe.

See also `docs/specs/data/FREE_RADIO_LOGGING.md`, `meta/UPDATE_HISTORY.txt`, and `docs/specs/development/VALIDATION.md`.
