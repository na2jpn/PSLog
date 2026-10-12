# PSLog Ver1.16 — Next Chat Plan

Use `PSLog_1.16_CANONICAL_SOURCE.zip` as the only baseline. Do not reconstruct it from the original 1.16 full-source ZIP or FIX1–FIX9.

Normal development starts at **1.161** unless the user chooses another line.

Preserve the Ver1.16 radio boundaries:
- one radio;
- CI-V or Hamlib selected, not both for one radio;
- virtual relay is optional, one external client, CI-V only in Ver1.16;
- MODE is never altered by frequency autoset;
- contest RMKS1 is never frequency-autoset;
- free-radio tabs do not consume amateur radio autoset;
- the com0com pair is persistent: create/delete only on explicit user action, not on ordinary PSLog shutdown;
- COM8 prefers COM208/COM209 and shifts by +100 when occupied;
- DTR/RTS safety settings must be applied before serial open;
- elevated setupc operations must run with the setupc.exe directory as the working directory.
