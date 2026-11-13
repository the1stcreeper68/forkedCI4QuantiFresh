# Household implementation validation

Captured 2026-11-13.

## Windows host, including real MongoDB and Docker integration

Command (PowerShell):

```powershell
$env:HOUSEHOLD_TEST_MONGO_URI = 'mongodb://127.0.0.1:27028'
$env:HOUSEHOLD_TEST_DOCKER = '1'
python -m pytest test_script.py new_test -q
Remove-Item Env:HOUSEHOLD_TEST_MONGO_URI
Remove-Item Env:HOUSEHOLD_TEST_DOCKER
```

Captured result:

```text
148 passed in 12.95s
```

The opt-in tests used a disposable MongoDB 8 Docker container bound only to localhost and temporary directories for container persistence. Generated test databases were removed. Existing Atlas records and local runtime data were not migrated or modified.

## Rebuilt Python 3.14 Docker image

```text
docker compose -f .github/smoke_test/docker-compose.ci.yml build test
Image smoke_test-test Built

docker compose -f .github/smoke_test/docker-compose.ci.yml run --rm test python -m pytest test_script.py new_test -q
146 passed, 2 skipped in 3.06s
```

The two skips are expected: opt-in localhost MongoDB and host Docker restart checks. Both passed in the Windows host run above. No test was skipped because of a failing assertion.

## Captured application walkthrough

```text
python -m new_test.capture_walkthrough
Captured walkthrough: .../HOUSEHOLD_RUNNING_OUTPUTS.md
```

The walkthrough captures real prompts and data with Zi, online/offline operation, consumption, stale-save rejection, and switching. Scripted concurrency steps are explicitly labelled. The capture utility does not call AI providers or access Atlas.

## Coverage notes

The prior suite had 133 tests. Of those, 24 tests asserted the retired global storage/startup behaviour; their coverage was replaced by 39 household-specific tests under `new_test`. The remaining 109 existing business-rule, AI, logger, and entry-point tests still pass.

Tests cover household isolation, schema validity, stable IDs, no-op edits, real MongoDB conditional updates, real local process contention, interrupted file transactions, stale offline uploads, lost cloud responses, failed local writes, migration retries/backups, settings, startup, switching, expiry cancellation, and Docker persistence.

Limitations of this original run: it validated the MongoDB protocol and repository against local MongoDB. Subsequent validation on the user-provided dummy Atlas cluster is recorded in `ATLAS_VALIDATION_RESULTS.md`. Migration was tested with fixtures and has not been executed on existing data. Automatic conflict merging, account authentication, and automatic history archival are not implemented.
