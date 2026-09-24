PSLog 1.01 Windows finishing patch v3

Changes:
1. Fix QFileDialog filters that used full-width Japanese parentheses.
   - import_ui.py: PS Log TXT / ADIF / HAMLOG CSV
   - qsl_ui.py: received-list TXT
2. Normalize the award/activity save dialog filter format.
3. Bundle the built-in contest data in Windows builds:
   - config/rules
   - config/db/contest
   - config/templates/cabrillo
4. Extend release packaging validation so built-in contest assets are required and
   unexpected/private config files are still rejected.
5. Update test_windows_package.py for the bundled contest assets.

Overlay these files onto pslog-1.01 without renaming test_*.py.
Then run:
  python -m unittest discover -v
If all 586 tests pass, run build-windows.ps1 again.
