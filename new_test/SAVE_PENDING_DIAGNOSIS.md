# Cloud/save/pending diagnosis — 2026-11-13

## Observed state

- The supplied Atlas connection succeeded and initially listed only `admin` and `local`.
- The earlier validation databases were intentionally temporary and removed after tests.
- The project's actual `.env` selects the supplied cluster, `MONGODB_DATABASE=QuantiFresh`, and `USE_MONGO=1`.
- Using those actual application settings, the repository connected successfully. `QuantiFresh.households` contained zero documents.
- A generated diagnostic household was successfully inserted and read back using the actual application credentials. Only the generated diagnostic collection was removed afterwards.
- The normal `quantifresh` Docker image was dated 10 November, before the household implementation. The user's command, `docker compose run --rm quantifresh`, did not request a rebuild.
- The current code had a silent unchanged-save branch: it returned to the main menu without explaining that no write was needed.

These findings do not indicate an Atlas authentication or write-permission failure. No real household was created in `QuantiFresh` by the validation runs; those runs deliberately used temporary database names.

## Applied fixes

- Rebuilt the normal `quantifresh` image using `docker compose build quantifresh`.
- Unchanged saves now explicitly say that no cloud write or pending draft is needed.
- Reverted edits explicitly report when the pending draft is cleared.
- Offline saves report the reason and path of the saved pending draft.
- Updated the recommended launch command to `docker compose run --build --rm quantifresh`.

## Validation

Focused session and CLI regression tests:

```text
21 passed in 4.11s
```

The rebuilt normal Docker image was then tested with the real Atlas cluster and a temporary bind-mounted local database folder:

```text
python -m pytest new_test/test_docker_atlas_save.py -q --tb=short
1 passed in 10.79s
```

That test verified all of the following through the actual interactive application:

1. Create Zi's test household online; confirm its document and fridge data exist in Atlas.
2. Save unchanged data; confirm the explicit no-change message.
3. Restart with cloud disabled, edit an expiry date, and save; confirm the pending file exists while cloud/snapshot data remain unchanged.
4. Restart online and choose Save/sync; confirm Atlas receives the edit, the version increases once, and the pending file is removed.

Temporary test records were removed. Existing application records, local household files, and credentials were not changed by this test.

## Expected next run

Start the rebuilt application and create a household to save a permanent record into `QuantiFresh.households`. The diagnostic tests do not leave a demo household there. Refresh Atlas Data Explorer after creation.

A pending JSON file exists only while changed data is awaiting upload or conflict resolution. An unchanged save does not create one; a successful cloud save removes it.

Docker documents `--build` as building the image before starting the container: [docker compose run reference](https://docs.docker.com/reference/cli/docker/compose/run/).
