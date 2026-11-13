# Multi-household implementation checklist

Status: implemented and validated on 2026-11-13. Migration tooling is implemented but has NOT been run on existing data. This local checklist is intentionally excluded from Git commits. See HOUSEHOLD_GUIDE.md, HOUSEHOLD_RUNNING_OUTPUTS.md, and new_test/VALIDATION_RESULTS.md.

## 1. Change the database structure and collection layout

- [x] Use one MongoDB collection named `households`.
- [x] Store one document per household, with embedded `household_members`, `fridge`, and `consumption_history` arrays.
- [x] Include `_id`, `name`, `version`, `created_at`, and `updated_at` in each household document.
- [x] Keep stable IDs for individual members, fridge batches, and consumption records; generate and maintain their uniqueness in the application.
- [x] Do not repeat `household_id` inside embedded records: their containing document identifies their household.

Collection layout:

```text
Quantifresh database
└── households (collection)
    ├── HS-7K9M-2X4P-8R6T (Tan Family document)
    │   ├── name, version, created_at, updated_at
    │   ├── household_members[]
    │   ├── fridge[]
    │   └── consumption_history[]
    └── HS-3B8N-6W2C-9T5R (Lim Family document)
        ├── name, version, created_at, updated_at
        ├── household_members[]
        ├── fridge[]
        └── consumption_history[]
```

Example household document (IDs are illustrative):

```json
{
  "_id": "HS-7K9M-2X4P-8R6T",
  "name": "Tan Family",
  "version": 7,
  "created_at": "2026-11-13T08:00:00Z",
  "updated_at": "2026-11-13T10:00:00Z",
  "household_members": [
    {
      "_id": "person_001",
      "name": "Alice",
      "age": 22,
      "gender": "female",
      "dietary_restriction": "none"
    }
  ],
  "fridge": [
    {
      "_id": "item_001",
      "Item_Name": "milk",
      "Quantity": 2,
      "Unit": "l",
      "Purchase_Date": "2026-11-13",
      "Expiry_Date": "2026-11-20",
      "Remarks": "none"
    }
  ],
  "consumption_history": [
    {
      "_id": "record_001",
      "Item_Name": "milk",
      "Quantity": 1,
      "Unit": "l",
      "Date_Range": 5,
      "Record_Date": "2026-11-13",
      "Remarks": "breakfast"
    }
  ]
}
```

The repositories will map domain objects to this shared document schema. Cloud timestamps can use BSON dates; JSON serializes those dates as UTC ISO 8601 strings, as illustrated above.

## 2. Generate a unique household ID

- [x] Generate a securely random ID prefixed with `HS-`, such as `HS-7K9M-2X4P-8R6T`.
- [x] Use a sufficiently long random suffix rather than exactly four characters.
- [x] Use MongoDB's unique top-level `_id` constraint and retry generation on a collision.
- [x] Allow duplicate household display names.
- [x] Display the generated ID so users can save and share it.

## 3. Handle race conditions

- [x] Load the document and its version together.
- [x] Save with a filter containing both `_id` and the originally loaded `version`.
- [x] Update the embedded data, timestamp, and version in one atomic document update.
- [x] Do not use upsert for ordinary saves of existing households.
- [x] If the document no longer matches, preserve the draft and offer reload/review instead of overwriting newer data.
- [x] Do not automatically retry stale edits using a newer version.

```text
Alice loads version 7; Bob loads version 7.
Alice saves with version 7 -> succeeds; database becomes version 8.
Bob saves with version 7 -> rejected; Bob's draft remains available.
```

## 4. Add household creation and access flow

- [x] Support offline household creation; register at the first successful cloud sync and report any replacement ID after a collision.
- [x] Keep offline creation and normal selection separate from joining an existing cloud household.

- [x] Add startup options: Create household / Enter household ID / Exit.
- [x] Validate and consistently normalize entered household IDs.
- [x] Show a clear message when an ID is not found.
- [x] Do not require passwords for this version; anyone holding the household ID can access it.
- [x] Keep access checks separate so accounts and household membership checks can be added later.
- [x] Keep dietary member profiles separate from future login accounts.
- [x] Ask for a household display name during creation; use the household's `name` in welcome messages instead of the first member's name.
- [x] Identify existing households by ID, not by whether the member list is populated. Resume setup for an existing household with no members.
- [x] After successful creation/access, ask: "Remember this household on this device? (yes/no)".
- [x] Store the remembered ID and cached display name in local `device_settings.json`, separate from household documents and cloud synchronization.
- [x] On startup with a remembered ID, offer Continue with household / Switch household / Exit.
- [x] When no ID is remembered, or settings are missing/invalid, show Create household / Enter household ID / Exit.
- [x] Provide a Forget household option that clears the remembered preference without deleting household data or pending drafts.
- [x] When switching households, save/sync the current household's pending edits or obtain explicit confirmation to discard them before changing the active session. If edits cannot be synced and the user does not discard them, keep the current household active.
- [x] Load and validate the target household before replacing the current local household. A failed switch must leave the current data intact.
- [x] After a successful switch, replace the local snapshot, pending-draft storage, and synchronization state so only the newly selected household remains locally; offer to remember its ID.
- [x] Use the cached name only for the startup menu; refresh it from the loaded household document after successful access.
- [x] Keep settings in the persistent application data folder, including the mounted data folder when running in Docker.

The remembered preference belongs to the local installation or OS user. It is a saved household access code, not automatic identification of the person using the device. Users do not need to re-enter their name on each startup.

```text
Start application
        |
        v
Read device_settings.json
        |
        +-- No valid remembered ID
        |      -> Create household / Enter household ID / Exit
        |
        +-- Remembered ID found
               -> Continue with household / Switch household / Exit
                              |
                              v
                  Load the selected household by ID
                              |
                              v
                  Resume setup or open the main menu
```

Example local settings:

```json
{
  "last_household_id": "HS-7K9M-2X4P-8R6T",
  "last_household_name": "Tan Family"
}
```

Startup checks:

| Situation | Required behaviour |
|---|---|
| Household exists in MongoDB | Load it and handle any pending local draft before refreshing the cache. |
| MongoDB confirms the ID does not exist | Explain that it was not found; offer another ID or creation. Do not silently recreate it from a cached copy. Preserve pending drafts. |
| MongoDB is unavailable and this household has cached data | Offer offline access to that household, preserving pending edits and their base version. |
| MongoDB is unavailable and no cached data exists | Explain that the household cannot be loaded; offer retry or exit. |
| Existing household has no members | Resume setup within the same household ID. |
| Settings file is missing or invalid | Show the create/access menu without deleting household data. |

## 5. Load and save only the selected household

- [x] Load using `db.households.find_one({"_id": selected_household_id})`.
- [x] Remove collection-wide loading and deletion from normal application operations.
- [x] Save only the active household document using its version check.
- [x] Use only the active household's members, fridge, and history for recommendations.

## 6. Skip saving when nothing changed

- [x] Keep an independent snapshot of the originally loaded editable data.
- [x] Compare the final members, fridge, history, and editable household name against that snapshot.
- [x] Exclude version and generated timestamps from the change comparison.
- [x] Skip the database write when the final data is identical; do not increment the version or update the timestamp.
- [x] Detect edits that were reversed, provided the complete final dataset is unchanged.

## 7. Improve expiry editing

- [x] Allow cancellation or keeping the existing expiry date.
- [x] Show "Expiry date unchanged" when the existing date is entered.
- [x] Skip expiry-update and batch-merge logic when the date is unchanged.
- [x] Preserve validation and batch merging for actual date changes.

## 8. Use the same collection/document format for local JSON and cloud storage

- [x] Keep only the currently selected household locally; do not accumulate a cache of previously accessed households.
- [x] Represent the cloud `households` collection locally with `households/current.json`, containing one household document with the same fields and embedded arrays as the cloud.
- [x] Replace the separate member, fridge, and consumption JSON files with this combined household document format.
- [x] Verify that the `_id` inside `households/current.json` matches the selected household before loading it. Never use another household's cache as an offline fallback.
- [x] Use the same serializer/schema mapping for cloud and local data, with explicit BSON-date/JSON-string conversion.
- [x] Store pending drafts in the same household document format; retain the cloud base version until a cloud save succeeds.
- [x] Keep synchronization bookkeeping outside the shared household document, including any local revision needed to protect concurrent local edits.
- [x] Keep the last cloud snapshot and pending draft separate so a refresh cannot discard unsaved changes.
- [x] Upload pending changes with the same household-ID and base-version check used by online saves.
- [x] Handle a conflict separately from a connection failure; never treat a stale upload as permission to replace cloud data.
- [x] Protect local read/check/write operations with a file lock and atomic file replacement.
- [x] Coordinate household switching with local saves under the same locking rules. An application instance still editing the previous household must not overwrite the new current household's local files; preserve its draft in memory and report the changed local selection.
- [x] Switch to another household only when it can be loaded successfully from the cloud; offline access is limited to the household currently stored locally.
- [x] Replace old local household data only after pending edits are resolved and the target load succeeds. Switching does not delete either household from MongoDB.

```text
database/
├── device_settings.json                # Remembered household; local only
├── households/                         # Only the current household
│   └── current.json                    # Same schema as its cloud document
├── pending_households/                 # Optional draft for that same household
│   └── current.json                    # Same document schema
└── sync_state/                         # Current household's local bookkeeping
    └── current.json
```

JSON files represent collection documents; JSON itself does not provide MongoDB collection queries or concurrency controls. The local database contains only the current household, while MongoDB retains all households. The snapshot and optional pending draft always belong to the same current household.

```text
Use Tan Family -> Local database contains Tan Family only.
Switch to Lim Family -> Resolve Tan Family edits, then load Lim Family.
Successful switch -> Local database contains Lim Family only.
Failed/cancelled switch -> Local database still contains Tan Family.
```

## 9. Update classes and repository interfaces

- [x] Add household identity and name to `Household`.
- [x] Introduce household creation/access logic and an active household session.
- [x] Track the loaded version and original snapshot in the session or persistence layer.
- [x] Update `DB_manager`, `MongoDBRepository`, and `JsonRepository` for the shared embedded document schema.
- [x] Retain separate Python classes for household members, fridge, and consumption history.
- [x] Introduce a distinct save-conflict error/result.

## 10. Migrate existing data

The items below describe implemented command capabilities. Running the migration on existing data remains an explicit user action. Reuse the same backup directory and manifest for every retry.

- [x] Back up existing cloud/local data before migration.
- [x] Combine existing members, fridge, and history into one initial named household document.
- [x] Generate its household ID and initialize its version and timestamps.
- [x] Assign stable IDs to existing nested records.
- [x] Verify record counts and values after migration before retiring the old storage layout.
- [x] Ensure rerunning migration does not create duplicate households or records.

## 11. Test the new behaviour

- [x] Verify that different households remain isolated during loading and saving.
- [x] Verify duplicate household names are allowed and household-ID collisions are handled.
- [x] Verify only one of two saves based on the same version succeeds.
- [x] Verify fridge changes and related consumption records are saved together.
- [x] Verify cancelled, unchanged, and fully reversed edits do not cause writes.
- [x] Verify stale offline uploads cannot overwrite newer cloud data.
- [x] Verify failures and conflicts preserve drafts.
- [x] Verify cloud/local serialization round trips preserve data and version values.
- [x] Verify concurrent local application instances cannot silently overwrite each other's drafts.
- [x] Verify migration preserves the existing data.
- [x] Verify remembered-household startup, switching, forgetting, and missing/invalid settings.
- [x] Verify welcome messages use the household name rather than the first member's name.
- [x] Verify a missing cloud household is distinguished from an unavailable cloud connection.
- [x] Verify offline startup loads only the selected household's cache and preserves pending drafts.
- [x] Verify incomplete household setup resumes under the existing ID.
- [x] Verify remembered settings survive Docker restarts when the persistent data folder is mounted.
- [x] Verify a successful household switch leaves only the target household in local snapshot, draft, and synchronization storage.
- [x] Verify failed/cancelled switches retain the current household and its pending edits.
- [x] Verify switching cannot silently discard unsynced edits or load a different household's cache while offline.
- [x] Verify an older application instance cannot overwrite local storage after another instance switches households.

## 12. Monitor household document size

- [x] Measure actual BSON document size, including embedded history.
- [x] Set an early threshold, such as 8 MiB, below MongoDB's 16 MiB document limit.
- [x] Define an archive/export strategy or move older history to a separate collection before reaching the limit.
- [x] Do not silently delete historical records to reduce size.

## Delivery notes

- Real Zi application transcripts: `HOUSEHOLD_RUNNING_OUTPUTS.md`.
- Usage and migration commands: `HOUSEHOLD_GUIDE.md`.
- Host validation: 148 passed, including disposable MongoDB and Docker persistence.
- Docker validation: 146 passed; 2 opt-in host integration tests skipped inside the container.
- No Git push, no production migration, and no automatic history archival.
- New code blocks use `# [STATUS]` and `#__` comments.
