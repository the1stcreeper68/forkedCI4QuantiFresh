# Multi-household validation

New validation files live in this folder. Run `python -m pytest test_script.py new_test -q` for business-rule and household regression tests.

Tests must use temporary directories and fake or mocked cloud collections. They must not read production credentials, migrate real data, or contact the configured MongoDB database.

Coverage:

- Household schema round trips and stable embedded record IDs.
- Household-scoped reads and atomic version-checked cloud saves.
- No-op and reverted edits, including expiry-date cancellation.
- Offline drafts, stale uploads, and failures that preserve pending edits.
- Concurrent local saves and switching with only one household cached.
- Remembered startup, missing households, incomplete setup, and forgetting.
- Explicit migration with backups and repeat-run protection.

## Official implementation references

- [MongoDB atomicity and expected-value update filters](https://www.mongodb.com/docs/manual/core/write-operations-atomicity/)
- [PyMongo collection operations and returning the updated document](https://pymongo.readthedocs.io/en/stable/api/pymongo/collection.html#pymongo.collection.Collection.find_one_and_update)
- [Python secure random generation](https://docs.python.org/3/library/secrets.html)
- [Python atomic file replacement](https://docs.python.org/3/library/os.html#os.replace)
- [Filelock documentation](https://py-filelock.readthedocs.io/en/stable/)

An atomic replacement protects one file. A lock and recoverable transaction are also needed when the snapshot, draft, and synchronization state change together.

## Optional real services

- Set `HOUSEHOLD_TEST_DOCKER_ATLAS=1` together with the explicit Atlas URI/host variables to run `new_test/test_docker_atlas_save.py`. This checks the rebuilt `quantifresh` image through online creation, offline editing, and synchronization after a container restart, using only temporary storage and a generated Atlas database.
- Atlas validation is separately opt-in: provide `HOUSEHOLD_ATLAS_TEST_URI` through the process environment and set `HOUSEHOLD_ATLAS_TEST_HOST` to its explicitly confirmed hostname. Run `python -m pytest new_test/test_atlas_households.py -q`. Never commit credentials. Each test creates a unique `qfval_…` database and removes only its own `households` collection afterwards; it does not require `dropDatabase` privileges.
- `HOUSEHOLD_TEST_MONGO_URI=mongodb://127.0.0.1:27028` enables the real MongoDB atomicity test. Only localhost is accepted; the generated test database is removed afterwards.
- `HOUSEHOLD_TEST_DOCKER=1` enables a two-container restart test using the built `smoke_test-test` image and a temporary bind mount.
- `python -m new_test.capture_walkthrough` captures the real application prompts and local MongoDB operations into `HOUSEHOLD_RUNNING_OUTPUTS.md`. It uses temporary local folders and removes its generated demo database.

The old tests that expected global `delete_many({})`, separate JSON stores, and automatic shared-data startup were replaced here. The existing business-rule, AI, logger, and entry-point tests remain in `test_script.py`.
