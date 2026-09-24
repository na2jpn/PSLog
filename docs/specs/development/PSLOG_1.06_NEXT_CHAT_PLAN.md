# PSLog Ver1.06 — Next Chat Plan

## Main theme: free-radio (フリラ) support

Free-radio support was intentionally deferred from the Ver1.05 development line so the amateur-radio baseline could be stabilized first.

### Initial user mode

New users should be able to choose:

- アマチュア無線
- フリラ
- 両方

Existing amateur-radio users must keep their current amateur callsign configuration without re-entry.

### Callsign types

Amateur callsigns and free-radio callsigns are separate internal types.

Amateur:

- existing uppercase/full-width normalization remains.
- current amateur-only callsign validators must not be reused blindly for free-radio input.

Free-radio normalization direction:

- Japanese portion canonical form: hiragana.
- katakana input → hiragana.
- Latin letters → ASCII uppercase.
- digits → ASCII digits.
- kanji is not automatically converted to a guessed reading.

### UI / tabs

- Amateur standard tabs remain `[A]...`.
- Free-radio tabs are expected to use `[F]...`.
- Free-radio input fields/log behavior may be separated from the existing standard/contest amateur workspace where that is safer.

### Storage compatibility

Do not break existing PSLog TXT 11-field logs or contest/standard amateur features to force free-radio support into the same shape.
Decide free-radio log semantics explicitly before implementation.

## Patch workflow

The first development patch after the canonical Ver1.06 baseline is expected to be **Ver1.061**.
Collect requirements first. Do not implement a patch until the user explicitly says `1実装`, `2実装`, etc.
