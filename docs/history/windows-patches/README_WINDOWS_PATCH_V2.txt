PSLog 1.01 Windows portability patch v2

Fixes remaining Windows-only failures found after v1:
- contest_toyama_pdf.py: recognize/load Japanese Windows fonts under Qt offscreen.
- test_contest_score_ui.py: use Windows-native Path string for pending-row key.
- test_rule_catalog.py: make Japanese test fixture writes explicitly UTF-8.

Copy all files in this ZIP directly over pslog-1.01. Do not rename test_*.py files.
The long-path test is intentionally not changed here; if it remains the only error, inspect it separately because Windows long-path policy/capability must be distinguished from an application bug.
