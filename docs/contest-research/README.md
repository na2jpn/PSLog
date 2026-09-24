# Contest research notes — reading order

This folder contains both **current implementation status** and **historical research/provenance text**.
The historical text is intentionally retained, so words such as `未実装`, `未検証`, `本体未対応`, and `ルール未作成` can still appear.

Use this order:

1. `../IMPLEMENTATION_STATUS.md` — current 87-item implementation status.
2. The **現在の実装状態** banner at the top of the individual research note.
3. `PSLOG101_CURRENT_AUDIT.json` / `.md` — final PSLOG101 audit detail.
4. The remaining body of the individual note — investigation history, source evidence, decisions and unresolved external facts.

A historical “未実装” sentence does not override the current-status banner.
`Windows実機未検証` / `主催者受付未検証` describes final environment or external acceptance verification, not absence of implementation.

Run `python devtools/refresh_implementation_status.py` from the project root after a future implementation audit changes.
