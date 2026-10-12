# PSLog Ver1.16 Baseline

Ver1.16 canonical baseline is `PSLog_1.16_CANONICAL_SOURCE.zip`. It integrates the original Ver1.16 full source and accepted FIX1 through FIX9. Do not replay those fixes.

## Integrated changes

### Radio information
- Single radio only.
- User selects a radio model; known Icom models map to CI-V and supported Yaesu/Kenwood models map to Hamlib/rigctld. Custom entries keep manual CI-V address or Hamlib model ID available.
- COM and baud support AUTO; saved missing ports remain visible as not detected.
- Auto-connect at startup when enabled; failure is non-fatal.
- Connection test and normal connect/disconnect are available from radio settings; the main screen also has a compact connect/disconnect control.
- Frequency display beside the add-tab button: `-.--MHz` disconnected, `7.012MHz` style connected. Connected text is green, bold, and 2pt larger.
- Serial opens force DTR/RTS OFF before open and disable RTS/CTS and DSR/DTR handshakes. Hamlib starts with PTT NONE and DTR/RTS OFF.

### Automatic set on callsign RETURN
- Three opt-in checks: RMKS1, RMKS2, Band; all default OFF.
- Applies to the currently selected standard/EASY/contest amateur workspace.
- Frequency text appended to RMKS is MHz numeric text only plus a trailing ASCII space; exact repeated tail is not duplicated.
- Band uses PSLog band representative values. MODE is never changed.
- Contest RMKS1 is protected because it is the contest exchange; only RMKS2/Band may be applied.
- Free-radio tabs do not consume amateur-radio autoset.

### Persistent CI-V virtual COM relay
- One external client path only: external rig software or WSJT-X → persistent virtual COM → PSLog → physical COM → radio.
- Optional, default OFF. Ver1.16 virtual relay is CI-V only.
- Uses preinstalled com0com/setupc; PSLog does not install or bundle the kernel driver.
- Virtual COM management has its own settings tab. Users who do not need relay do not configure it.
- Create/delete actions require UAC. The created pair persists across PSLog shutdown; ordinary connect/disconnect only opens/closes relay handles.
- Preferred pair: physical COM8 → COM208 (external) / COM209 (PSLog internal). If either is busy, use COM308/309, COM408/409, etc.
- Pair state is recorded in `config/pslog_virtual_com.json`; next startup reuses the existing pair.
- setupc is searched in configured path, PATH, Program Files, and Program Files (x86). Elevated setupc operations set the working directory to the setupc.exe directory so com0com INF files are resolved correctly.
- Virtual relay failure never tears down an already-working physical radio connection.

### Windows save robustness
- Atomic replacement retries transient PermissionError/WinError 5 with short backoff.
- Before retry, the original snapshot is rechecked; a real external modification still aborts.
- Persistent permission failure is not hidden.

### Contest edit compatibility
- Existing contest files may serialize non-standard/non-numeric RST fields used as contest exchange information.
- Normal QSO creation and non-contest validation remain strict.

## Preserved invariants
- 11-field PSLog master format; JST; UTF-8 BOM + CRLF for new files.
- `logbook/` and `logbook_flr/` stay separate.
- One-ZIP updater architecture and protected user-data roots from Ver1.15.
- Contest display information never silently becomes a new scoring/rejection rule.
