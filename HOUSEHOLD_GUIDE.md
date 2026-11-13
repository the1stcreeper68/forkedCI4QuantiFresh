# Multi-household usage and storage

## Start and select a household

Install `python_dependencies.txt`, then run `python main.py`. Docker users start with `docker compose run --build --rm quantifresh` so source changes are rebuilt before running. Without `--build`, an existing image can still contain older code.

- Choose `1` (Create household) and enter a household display name, such as **Zi Household**. Member names such as **Zi** remain separate dietary profiles.
- Share the generated `HS-XXXX-XXXX-XXXX` code with people who should use this household. Names may repeat; IDs identify households.
- Choose `2` (Enter household ID) on another device and supply that ID. Joining another device requires the household to exist in MongoDB.
- Remembering the household is optional. On the next startup, choose Continue, Switch, Forget, or Exit. You do not enter each person's name again.
- An existing household with no members resumes setup under its existing ID.

There are no passwords or individual login accounts in this version. Anyone with a household code can access that household through the app. `DB_manager.authorize_household()` separates the access-policy decision for future authentication; member profiles are not accounts.

## Offline use and creation

With MongoDB unavailable, only the current cached household can be opened. You can also create a household offline. `USE_MONGO=0` deliberately disables cloud access.

An offline-created ID is provisional until registration in MongoDB. Save/sync uploads it when connectivity returns. If MongoDB reports a genuine ID collision, the app generates and displays a replacement code. Other devices cannot join an offline-only household before that first upload.

Switching to another existing household requires a successful cloud load. Pending edits must be synced or explicitly discarded first. Declining discard, cancelling, or failing to load the target preserves the current local household. Creating a different offline household follows the same pending-edit confirmation.

If sync fails during switching, the app stays in the numbered resolution menu and explains the failure. Choose retry sync, explicit discard, or Resume current household. The household access menu labels option 3 **Cancel switch** during a switch. Entering the current ID prompts for a different ID; a successful switch displays the new household name and ID.

## What is stored

MongoDB contains one `households` collection and one document per household:

```text
households
  HS-… : name, version, created_at, updated_at
         household_members[]
         fridge[]
         consumption_history[]
```

Each member, fridge batch, and history record has a stable embedded `_id`. Embedded rows do not repeat the household ID. Member display numbers may change with ordering; storage IDs remain stable. The existing AI and business-rule dictionaries retain their existing format.

Local runtime storage contains only the current household:

```text
app_data/database/
  device_settings.json                 remembered ID/name; local only
  households/current.json              last cloud snapshot (or initial offline household)
  pending_households/current.json      optional draft retaining its base version
  sync_state/current.json              revision token and unregistered flag
  .household.lock                      process synchronization
  .household_transaction.json           temporary journal, removed after completion
```

The cloud and local household documents share the same fields. BSON metadata dates become UTC ISO strings in JSON; food dates remain calendar-date strings. The journal replays interrupted local writes before the next read. Settings and synchronization bookkeeping are not uploaded.

The Compose configuration mounts `./app_data/database` into `/app/app_data/database`; the remembered household and draft survive container replacement. The preference belongs to the installation/shared data folder, not a detected individual. Separate devices should use separate local folders; cloud versions coordinate their updates. Do not synchronize one active local folder between computers using a file-sync service as a replacement for MongoDB.

## Saves, conflicts, and unchanged edits

Main-menu option **6 saves/syncs and stays in the app**. Option **3 saves/syncs and exits**. When cloud access is unavailable, option 3 can exit after preserving a local pending draft; this does not mean MongoDB received it.

Option **5 saves pending changes to MongoDB and forgets the remembered household**, returning to the access menu. Cached local files remain until another household is selected. If pending changes cannot reach MongoDB, forgetting is stopped and the draft remains available. The startup Forget option follows the same rule.

If the local snapshot or sync-state file was deleted, startup backs up surviving cache files and settings under `app_data/database/recovery/<unique-id>/`, clears the invalid active cache, and opens the household menu. Cloud data is not changed. Enter the existing ID to reload from MongoDB, or create a new household. Recovery backups are not loaded or uploaded automatically; inspect them if unsynced edits need recovery. Valid pending drafts are preserved during ordinary startup.

The app compares the final editable document with its loaded snapshot. Entering an edit menu, cancelling, keeping the same expiry date, or fully reverting edits causes no cloud write and no version increment.

Save/sync now explicitly reports `No changes to save. No cloud write was made and no pending draft is needed.` when unchanged. An offline save reports why cloud access is unavailable and the pending file's path. A successful online save clears the pending file; its absence after success is expected.

A changed document is first preserved locally. MongoDB then uses both `_id` and the original `version` in one atomic update of all embedded arrays. The version increases only on a successful cloud update. Normal saves never upsert or delete collections.

If two people load version 7, only the first conflicting save can produce version 8. The other draft is retained. Recovery offers Review, Export draft, Reload and discard, Retry, or Keep editing. Retry does not substitute a newer cloud version. Review prints both datasets for manual comparison; automatic field-level merging is not implemented.

An exported draft must use a new path outside the active database folder. It is a user-requested backup, not an additional cached household. A stale local process cannot overwrite a newer local selection. It can review/export its in-memory draft before reloading.

## Explicit migration of existing data

Migration has **not** been run on your existing local data or Atlas database. The new application ignores the old three-store format; it does not delete it.

Stop all old application instances before migration so the legacy source does not change during export. Select the correct source, choose a dedicated backup directory outside the active database folder, and keep that directory for every retry.

From legacy JSON:

```powershell
python -m modules.repositories.migrate_household --source json --name "Zi Household" --json-dir "app_data/database" --backup-dir "app_data/migration_backup" --confirm-legacy-apps-stopped
```

From the configured Atlas database's legacy collections:

```powershell
python -m modules.repositories.migrate_household --source cloud --name "Zi Household" --backup-dir "app_data/migration_backup" --confirm-legacy-apps-stopped
```

Both commands require the configured MongoDB connection. They back up the old input, validate records/counts, create a household with stable IDs, read it back for verification, and print its access code. Old cloud collections and JSON files remain untouched. Use the printed ID to open the migrated household.

The backup directory's manifest stores the original generated document and completion status. Rerunning with that same directory/source/name reuses its IDs and never resets an already migrated household to old backup values. Do not create a new backup directory to retry the same migration: idempotence is tied to that manifest. A changed source or name is rejected rather than overwriting the existing manifest.

After you have verified the migrated data, retire the old application and move old JSON files to your backup location if you no longer need them. The new app neither reads nor updates those files. Do not run old application versions against the new workflow.

## Growth and validation

The app measures BSON size, warns at 8 MiB, and rejects documents reaching 16 MiB. It never silently deletes history. Export the household for backup; before the limit, a future schema migration should place older history in household-scoped, indexed documents in a separate collection. Automatic archival is not implemented.

Run `python -m pytest test_script.py new_test -q`. Validation uses temporary directories; optional localhost MongoDB and Docker checks are described in `new_test/README.md`.

See [captured real application output](HOUSEHOLD_RUNNING_OUTPUTS.md) for Zi's walkthrough and actual before/after documents.

## Official references used

- [MongoDB atomicity and expected-value filters](https://www.mongodb.com/docs/manual/core/write-operations-atomicity/)
- [MongoDB document-size limit](https://www.mongodb.com/docs/manual/reference/limits/#bson-document-size)
- [PyMongo conditional update and returned document](https://pymongo.readthedocs.io/en/stable/api/pymongo/collection.html#pymongo.collection.Collection.find_one_and_update)
- [Python secure random generation](https://docs.python.org/3/library/secrets.html)
- [Python atomic replacement](https://docs.python.org/3/library/os.html#os.replace)
- [Cross-process file locking](https://py-filelock.readthedocs.io/en/stable/)
