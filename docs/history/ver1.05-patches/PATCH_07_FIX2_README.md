# PSLog Ver1.057 PATCH 07 FIX2

Windows GUI tests that intentionally use historical fixed timestamps could block on the PATCH 07 record-time confirmation dialog.

- `test_blacklist_gui.py`: bypass the unrelated record-time confirmation in the fixed-date blacklist test.
- `test_gui.py`: bypass the unrelated record-time confirmation in the historical-date persistence/external-change test.
- Production behavior is unchanged. The 3-minute warning remains active in PSLog itself.
- VERSION remains 1.057.
