# Dummy Atlas validation results

Captured on 2026-11-13 using the user-provided dummy Atlas cluster. Credentials were supplied only through the test process environment; they are not stored in this report, source files, or Git.

## Final captured result

```text
python -m pytest new_test/test_atlas_households.py -q --tb=short
....                                                                     [100%]
4 passed in 18.29s
```

The four scenarios exercised the real repository and Atlas:

1. Two concurrent saves from one version: one succeeds and one conflicts; another household remains unchanged.
2. Offline household creation and first upload: the ID is retained, pending data is cleared after success, and a no-op save does not change cloud metadata.
3. Consumption: fridge quantity and history are saved together; a stale offline draft is rejected and preserved locally.
4. Switching: the local cache contains only the selected household while both cloud documents remain intact.

## Environment findings and cleanup

- Authentication and connectivity succeeded.
- The initial generated test database names exceeded the cluster's reported 38-byte limit. The fixture now uses `qfval_` plus a 32-character random suffix.
- The provided account permits the tested application operations and collection deletion, but denied `dropDatabase`. Cleanup now removes only the generated test collection. The earlier run's four test collections were also explicitly removed.
- The final run passed both assertions and teardown. No existing application database or record was modified or migrated.
- A filtered post-run metadata check reported `Remaining generated Atlas test databases: 0`.
- These tests do not change `.env`, the normal application's selected household, or its local database folder.

Without the explicit Atlas environment variables, the suite is safely opt-in:

```text
python -m pytest new_test/test_atlas_households.py -q
ssss                                                                     [100%]
4 skipped in 0.21s
```

The earlier localhost/Docker validation remains documented in `VALIDATION_RESULTS.md`; this report adds validation on the supplied Atlas cluster. The captured Zi CLI walkthrough remains a separate local-MongoDB capture, not an Atlas transcript.
