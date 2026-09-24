# PSLog Ver1.14 Canonical Source

This directory is the **final canonical source tree for PSLog Ver1.14**. It is based on the accepted Ver1.13 canonical source plus the accepted Ver1.14 initial-startup enhancement.

Future work must start from `PSLog_1.14_CANONICAL_SOURCE.zip` only. Do not reconstruct this tree by replaying Ver1.11/1.12/1.14 PATCH/FIX/DIFF ZIPs or older canonical sources.

## Read first

1. [START_HERE.md](START_HERE.md)
2. [HANDOFF.md](HANDOFF.md)
3. [NEXT_CHAT_PROMPT.md](NEXT_CHAT_PROMPT.md)
4. [docs/specs/development/PSLOG_1.14_BASELINE.md](docs/specs/development/PSLOG_1.14_BASELINE.md)
5. [docs/specs/data/FREE_RADIO_LOGGING.md](docs/specs/data/FREE_RADIO_LOGGING.md)
6. [docs/INDEX.md](docs/INDEX.md)
7. [WINDOWS_BUILD.md](WINDOWS_BUILD.md)

## Core invariants

- Master log data remains the PSLog TXT **11-field** format, not SQLite.
- New TXT files are UTF-8 with BOM and CRLF; compatible existing files may omit BOM.
- Log timestamps are JST.
- Amateur-radio master logs are under `logbook/`; free-radio master logs are under `logbook_flr/`. The two sources must not be mixed by search, award, or edit workflows.
- Existing amateur-radio workflows remain the compatibility baseline.
- Contest `rule_view` is human-readable reference information; display text does not itself create scoring/submission restrictions.
- Registered rule catalog remains 87 rules: 86 contests + 1 QSO Party entry.

## Ver1.14 release highlights

- All accepted Ver1.13 free-radio functionality is retained.
- On first launch, the initial dialog starts with **「アマチュア無線のコールサイン」** and can switch to **「フリラのコールサイン」**.
- A user can begin PSLog as a free-radio-only user without first configuring an amateur-radio callsign.
- Free-radio first start collects callsign, type, optional model, and automatic log year, then replaces the initial empty standard tab with a free-radio tab.
- Free-radio-only settings do not write the free-radio callsign into the amateur `own` setting.
- Creating standard/EASY/contest tabs from a free-radio tab does not inherit the free-radio callsign as an amateur callsign.
- Blank-model free-radio tabs restore correctly after restart.
- Windows release filenames continue to derive the version from `storage.VERSION`.

## Development workflow

Collect requirements first. Do not implement while requirements are still being listed; wait for the user's explicit implementation instruction. `まとめ` means summarize/confirm only.

Run before/after changes:

```powershell
python -m unittest discover -v
```

Windows release build:

```powershell
.\build-windows.ps1
```

The next normal development patch is expected to be Ver1.141 unless the user explicitly chooses another number.
