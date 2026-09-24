PSLOG101 Windows portability patch

Apply by extracting these files over pslog-1.01.
Changes:
- storage.py: do not use Windows st_ctime_ns in snapshot identity check.
- test*.py: specify UTF-8 explicitly for read_text() calls used by the Windows test suite.
- test_contest_areas.py / test_contest_countries.py: use str(Path(...)) for platform-neutral draft keys.

After overwrite:
  python -m unittest discover -v
If all 586 tests pass:
  .\build-windows.ps1
