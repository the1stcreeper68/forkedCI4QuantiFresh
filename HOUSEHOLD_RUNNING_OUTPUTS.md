# Multi-household: captured application walkthrough

Captured on 2026-11-13. These are real application prompts/output and database reads from disposable demo data. Input answers are echoed by the capture harness. MongoDB ran locally in Docker, not Atlas. No existing user data was used. AI shopping recommendations are outside this demonstration.

Run again with `python -m new_test.capture_walkthrough` while a disposable MongoDB is available on `127.0.0.1:27028`. The script removes only its generated demo database after capture.

## 1. Zi creates a household offline

The household name is separate from Zi's member profile. The code is stored locally; no MongoDB document exists yet.

```text
Welcome to the QuantiFresh!

Create household / Enter household ID / Exit (create/enter/exit): create
Household display name: Zi Household
Household created: Zi Household — HS-67YJ-53FS-HN8V
Changes are saved locally and await cloud sync.
This household is local only until its first successful cloud sync. Save the displayed ID; it may change if MongoDB detects a collision.
Remember this household on this device? (yes/no): yes
Using the current household locally. Use Save/sync when cloud access is available.
Complete setup for Zi Household (HS-67YJ-53FS-HN8V).
Please enter name: Zi
Please enter age: 22
Please enter gender (Male, Female): male
Please enter dietary restrictions (leave blank if none):
Please enter your family size including yourself: 1
User Zi registered successfully!

Household summary:
  1. Zi, 22, Male, diet: none

Do you have any food items at home you want to add? (yes/no): yes

Enter the items you currently have at home.
Item name: milk
Quantity and unit (e.g. 6kg, 500 g, 3 pcs) - units: kg, g, l, ml, pcs: 2 l
Expiry date (YYYY-MM-DD): 2026-11-20
Any remarks about this item? e.g. opened, for a party (leave blank if none):
Added 2 l of milk (expires 2026-11-20) to your home items.

Fridge
No. | Item name  | Current amt | Purchase date | Expiry date | Remarks  |
1   | milk       | 2 l         | NA            | 2026-11-20  | none     |

1. Add item
2. Edit/Remove an item
3. Confirm and submit items
Choose your option (1,2 or 3): 3

Fridge
No. | Item name  | Current amt | Purchase date | Expiry date | Remarks  |
1   | milk       | 2 l         | NA            | 2026-11-20  | none     |
Changes are saved locally and await cloud sync.
Welcome back, Zi Household! Household ID: HS-67YJ-53FS-HN8V

What would you like to do?
  1. Update consumption and plan groceries
  2. Edit expiry dates or delete items from your fridge
  3. Save database and exit the program
  4. Switch household
  5. Forget remembered household
  6. Save/sync now
Enter 1-6: 3
Changes are saved locally and await cloud sync.
Thank you for using the QuantiFresh!
```

### Pending local document before first upload

```json
{
  "_id": "HS-67YJ-53FS-HN8V",
  "name": "Zi Household",
  "version": 1,
  "created_at": "2026-11-13T08:25:02.766Z",
  "updated_at": "2026-11-13T08:25:02.766Z",
  "household_members": [
    {
      "_id": "e4df9d77545247ccb135c46685c1ec36",
      "name": "Zi",
      "age": 22,
      "gender": "male",
      "dietary_restriction": "none"
    }
  ],
  "fridge": [
    {
      "_id": "40e9a1f581d1461f8a640160b4cc08bb",
      "Item_Name": "milk",
      "Quantity": 2.0,
      "Unit": "l",
      "Purchase_Date": "",
      "Expiry_Date": "2026-11-20",
      "Remarks": "none"
    }
  ],
  "consumption_history": []
}
```

## 2. Remembered startup and first cloud sync

Continue reads the saved household ID. Save/sync registers the household and uploads its members/fridge. The local pending draft is cleared only after success.

```text
Welcome to the QuantiFresh!

Continue with Zi Household / Switch / Forget / Exit (continue/switch/forget/exit): continue
Opening the current local-only household. Use Save/sync to register it in MongoDB.
Welcome back, Zi Household! Household ID: HS-67YJ-53FS-HN8V

What would you like to do?
  1. Update consumption and plan groceries
  2. Edit expiry dates or delete items from your fridge
  3. Save database and exit the program
  4. Switch household
  5. Forget remembered household
  6. Save/sync now
Enter 1-6: 6
Household saved to MongoDB.
Welcome back, Zi Household! Household ID: HS-67YJ-53FS-HN8V

What would you like to do?
  1. Update consumption and plan groceries
  2. Edit expiry dates or delete items from your fridge
  3. Save database and exit the program
  4. Switch household
  5. Forget remembered household
  6. Save/sync now
Enter 1-6: 3
Thank you for using the QuantiFresh!
```

### Document read back from MongoDB

```json
{
  "_id": "HS-67YJ-53FS-HN8V",
  "name": "Zi Household",
  "version": 2,
  "created_at": "2026-11-13T08:25:02.766Z",
  "updated_at": "2026-11-13T08:25:02.931Z",
  "household_members": [
    {
      "_id": "e4df9d77545247ccb135c46685c1ec36",
      "name": "Zi",
      "age": 22,
      "gender": "male",
      "dietary_restriction": "none"
    }
  ],
  "fridge": [
    {
      "_id": "40e9a1f581d1461f8a640160b4cc08bb",
      "Item_Name": "milk",
      "Quantity": 2.0,
      "Unit": "l",
      "Purchase_Date": "",
      "Expiry_Date": "2026-11-20",
      "Remarks": "none"
    }
  ],
  "consumption_history": []
}
```

### Local synchronization state

```json
{
  "household_id": "HS-67YJ-53FS-HN8V",
  "revision": "de77fe7e1ae3400ba06613a83ae365ed",
  "unregistered": false
}
```

## 3. Another device joins and cancels an expiry edit

Device B loads only the entered household. Blank expiry input leaves the document, version, and updated timestamp unchanged.

```text
Welcome to the QuantiFresh!

Create household / Enter household ID / Exit (create/enter/exit): enter
Household ID (HS-XXXX-XXXX-XXXX): HS-67YJ-53FS-HN8V
Remember this household on this device? (yes/no): no
Welcome back, Zi Household! Household ID: HS-67YJ-53FS-HN8V

What would you like to do?
  1. Update consumption and plan groceries
  2. Edit expiry dates or delete items from your fridge
  3. Save database and exit the program
  4. Switch household
  5. Forget remembered household
  6. Save/sync now
Enter 1-6: 2

Fridge
No. | Item name  | Current amt | Purchase date | Expiry date | Remarks  |
1   | milk       | 2 l         | NA            | 2026-11-20  | none     |

What would you like to do with your fridge?
  1. Edit an expiry date
  2. Delete an item
  3. Done
Enter 1, 2 or 3: 1
Enter the item number (1-1): 1
New expiry date for milk (YYYY-MM-DD, blank/cancel to keep):
Expiry date unchanged.

Fridge
No. | Item name  | Current amt | Purchase date | Expiry date | Remarks  |
1   | milk       | 2 l         | NA            | 2026-11-20  | none     |

What would you like to do with your fridge?
  1. Edit an expiry date
  2. Delete an item
  3. Done
Enter 1, 2 or 3: 3
Welcome back, Zi Household! Household ID: HS-67YJ-53FS-HN8V

What would you like to do?
  1. Update consumption and plan groceries
  2. Edit expiry dates or delete items from your fridge
  3. Save database and exit the program
  4. Switch household
  5. Forget remembered household
  6. Save/sync now
Enter 1-6: 3
Thank you for using the QuantiFresh!
```

## 4. Consumption moves stock into history

This section invokes the actual consumption prompt and save operation directly, without running the AI grocery step. One atomic save updates both embedded arrays.

```text
How much milk did you consume? (you have 2.0 l): 0.5

Consumption recorded:
  Over the last 5 day(s), remarks: breakfast
  1. 0.5 l of milk
Household saved to MongoDB.
```

### Fridge and history after consumption

```json
{
  "_id": "HS-67YJ-53FS-HN8V",
  "version": 3,
  "fridge": [
    {
      "_id": "40e9a1f581d1461f8a640160b4cc08bb",
      "Item_Name": "milk",
      "Quantity": 1.5,
      "Unit": "l",
      "Purchase_Date": "",
      "Expiry_Date": "2026-11-20",
      "Remarks": "none"
    }
  ],
  "consumption_history": [
    {
      "_id": "5a6657d1a8c14ebe816cc7195bcc8d6c",
      "Date_Range": 5,
      "Item_Name": "milk",
      "Quantity": 0.5,
      "Unit": "l",
      "Remarks": "breakfast",
      "Record_Date": "2026-11-13"
    }
  ]
}
```

## 5. Concurrent saves preserve the losing draft

This is a scripted two-session scenario using the real repository and MongoDB, not fabricated console output. Device B's stale save cannot replace A's update. The UI offers review/export/reload when this occurs during normal use.

```text
Scripted two-device scenario: both loaded version 3.
Device A changes milk expiry and saves:
Household saved to MongoDB.
Device B tries to save consumption using the old version:
SaveConflict: This household changed or was removed. Review your draft before reloading.
Cloud milk quantity: 1.5
Device B preserved draft milk quantity: 1.0
```

## 6. Switch replaces only the current local household

Device A switches to an existing household after it is loaded successfully. Zi's household remains in MongoDB. Device B still retains its own pending Zi draft.

```text
Welcome to the QuantiFresh!

Continue with Zi Household / Switch / Forget / Exit (continue/switch/forget/exit): continue
Welcome back, Zi Household! Household ID: HS-67YJ-53FS-HN8V

What would you like to do?
  1. Update consumption and plan groceries
  2. Edit expiry dates or delete items from your fridge
  3. Save database and exit the program
  4. Switch household
  5. Forget remembered household
  6. Save/sync now
Enter 1-6: 4

Create household / Enter household ID / Exit (create/enter/exit): enter
Household ID (HS-XXXX-XXXX-XXXX): HS-TFFQ-NY8C-SQ2T
Remember this household on this device? (yes/no): yes
Welcome back, Lim Household! Household ID: HS-TFFQ-NY8C-SQ2T

What would you like to do?
  1. Update consumption and plan groceries
  2. Edit expiry dates or delete items from your fridge
  3. Save database and exit the program
  4. Switch household
  5. Forget remembered household
  6. Save/sync now
Enter 1-6: 3
Thank you for using the QuantiFresh!
```

### Device A current household

```json
{
  "_id": "HS-TFFQ-NY8C-SQ2T",
  "name": "Lim Household",
  "version": 2,
  "created_at": "2026-11-13T08:25:03.322Z",
  "updated_at": "2026-11-13T08:25:03.410Z",
  "household_members": [
    {
      "_id": "b51a5f78364a4ee4bbf96708efdb8a02",
      "name": "Lim",
      "age": 35,
      "gender": "female",
      "dietary_restriction": "none"
    }
  ],
  "fridge": [],
  "consumption_history": []
}
```

### Cloud households remain separate

```json
[
  {
    "_id": "HS-67YJ-53FS-HN8V",
    "name": "Zi Household"
  },
  {
    "_id": "HS-TFFQ-NY8C-SQ2T",
    "name": "Lim Household"
  }
]
```

## 7. What the cloud database records look like

The following records are read directly from the disposable MongoDB database used in this run. Atlas uses the same collection/document schema; these are not records copied from your Atlas database. Atlas connectivity and workflow tests are recorded separately in `new_test/ATLAS_VALIDATION_RESULTS.md`.

```text
<configured MongoDB database>
└── households (collection)
    ├── HS-67YJ-53FS-HN8V  Zi Household
    └── HS-TFFQ-NY8C-SQ2T  Lim Household
```

There are **two top-level documents**, one per household. Members, fridge batches, and consumption events are embedded records inside their household document; they are not separate collections. Every embedded record has its own stable `_id`, without repeating the household ID.

These full records use MongoDB Extended JSON: `{"$date": "..."}` represents a BSON date. The local JSON files below use ordinary UTC timestamp strings. Food dates remain `YYYY-MM-DD` strings in both places.

### Cloud document: Zi Household

```json
{
  "_id": "HS-67YJ-53FS-HN8V",
  "name": "Zi Household",
  "version": 4,
  "created_at": {
    "$date": "2026-11-13T08:25:02.766Z"
  },
  "updated_at": {
    "$date": "2026-11-13T08:25:03.243Z"
  },
  "household_members": [
    {
      "_id": "e4df9d77545247ccb135c46685c1ec36",
      "name": "Zi",
      "age": 22,
      "gender": "male",
      "dietary_restriction": "none"
    }
  ],
  "fridge": [
    {
      "_id": "40e9a1f581d1461f8a640160b4cc08bb",
      "Item_Name": "milk",
      "Quantity": 1.5,
      "Unit": "l",
      "Purchase_Date": "",
      "Expiry_Date": "2026-11-21",
      "Remarks": "none"
    }
  ],
  "consumption_history": [
    {
      "_id": "5a6657d1a8c14ebe816cc7195bcc8d6c",
      "Date_Range": 5,
      "Item_Name": "milk",
      "Quantity": 0.5,
      "Unit": "l",
      "Remarks": "breakfast",
      "Record_Date": "2026-11-13"
    }
  ]
}
```

### Cloud document: Lim Household

```json
{
  "_id": "HS-TFFQ-NY8C-SQ2T",
  "name": "Lim Household",
  "version": 2,
  "created_at": {
    "$date": "2026-11-13T08:25:03.322Z"
  },
  "updated_at": {
    "$date": "2026-11-13T08:25:03.410Z"
  },
  "household_members": [
    {
      "_id": "b51a5f78364a4ee4bbf96708efdb8a02",
      "name": "Lim",
      "age": 35,
      "gender": "female",
      "dietary_restriction": "none"
    }
  ],
  "fridge": [],
  "consumption_history": []
}
```

## 8. What the offline database files look like

This is a fresh simulated device using Zi's already registered household. The harness disables cloud access, records consumption through the domain methods, and invokes the real save path. MongoDB stays unchanged until synchronization.

```text
Scripted offline scenario: Zi records another 0.25 l of milk consumed.
Changes are saved locally and await cloud sync.
```

```text
app_data/database/
├── device_settings.json
├── households/
│   └── current.json              last cloud snapshot
├── pending_households/
│   └── current.json              offline edits awaiting upload
└── sync_state/
    └── current.json              local concurrency bookkeeping
```

All these files refer to **Zi's current household only**. Lim's records are not cached on this device. The lock file and temporary recovery journal are implementation files, not extra household records.

### device_settings.json — remembered access, not a cloud document

```json
{
  "last_household_id": "HS-67YJ-53FS-HN8V",
  "last_household_name": "Zi Household"
}
```

### households/current.json — last confirmed cloud data

```json
{
  "_id": "HS-67YJ-53FS-HN8V",
  "name": "Zi Household",
  "version": 4,
  "created_at": "2026-11-13T08:25:02.766Z",
  "updated_at": "2026-11-13T08:25:03.243Z",
  "household_members": [
    {
      "_id": "e4df9d77545247ccb135c46685c1ec36",
      "name": "Zi",
      "age": 22,
      "gender": "male",
      "dietary_restriction": "none"
    }
  ],
  "fridge": [
    {
      "_id": "40e9a1f581d1461f8a640160b4cc08bb",
      "Item_Name": "milk",
      "Quantity": 1.5,
      "Unit": "l",
      "Purchase_Date": "",
      "Expiry_Date": "2026-11-21",
      "Remarks": "none"
    }
  ],
  "consumption_history": [
    {
      "_id": "5a6657d1a8c14ebe816cc7195bcc8d6c",
      "Date_Range": 5,
      "Item_Name": "milk",
      "Quantity": 0.5,
      "Unit": "l",
      "Remarks": "breakfast",
      "Record_Date": "2026-11-13"
    }
  ]
}
```

### pending_households/current.json — offline draft

```json
{
  "_id": "HS-67YJ-53FS-HN8V",
  "name": "Zi Household",
  "version": 4,
  "created_at": "2026-11-13T08:25:02.766Z",
  "updated_at": "2026-11-13T08:25:03.243Z",
  "household_members": [
    {
      "_id": "e4df9d77545247ccb135c46685c1ec36",
      "name": "Zi",
      "age": 22,
      "gender": "male",
      "dietary_restriction": "none"
    }
  ],
  "fridge": [
    {
      "_id": "40e9a1f581d1461f8a640160b4cc08bb",
      "Item_Name": "milk",
      "Quantity": 1.25,
      "Unit": "l",
      "Purchase_Date": "",
      "Expiry_Date": "2026-11-21",
      "Remarks": "none"
    }
  ],
  "consumption_history": [
    {
      "_id": "5a6657d1a8c14ebe816cc7195bcc8d6c",
      "Date_Range": 5,
      "Item_Name": "milk",
      "Quantity": 0.5,
      "Unit": "l",
      "Remarks": "breakfast",
      "Record_Date": "2026-11-13"
    },
    {
      "_id": "1eef2692c58b4a0a94bd2b45199ba1b6",
      "Date_Range": 1,
      "Item_Name": "milk",
      "Quantity": 0.25,
      "Unit": "l",
      "Remarks": "offline breakfast",
      "Record_Date": "2026-11-13"
    }
  ]
}
```

### sync_state/current.json — local revision and registration status

```json
{
  "household_id": "HS-67YJ-53FS-HN8V",
  "revision": "0e69b564e5e8461790ac5e6427d4295a",
  "unregistered": false
}
```

| Location before sync | Version | Milk remaining | History records |
|---|---:|---:|---:|
| MongoDB Zi document | 4 | 1.5 l | 1 |
| Local snapshot | 4 | 1.5 l | 1 |
| Local pending draft | 4 | 1.25 l | 2 |

The pending draft keeps the **original cloud version and metadata timestamps**. Offline edits do not claim a newer cloud version. `unregistered: false` means the household already exists in MongoDB, even though this device is currently offline. A newly created offline household instead has `unregistered: true` until first registration. The local `revision` token is separate from MongoDB's `version`.

## 9. What changes after the offline draft syncs

Cloud access is restored. The update matches household ID and base version 4, so the fridge and history are committed together. If another device had changed that version, the draft would remain local instead.

```text
Household saved to MongoDB.
```

### Updated local snapshot — same logical document as MongoDB

```json
{
  "_id": "HS-67YJ-53FS-HN8V",
  "name": "Zi Household",
  "version": 5,
  "created_at": "2026-11-13T08:25:02.766Z",
  "updated_at": "2026-11-13T08:25:03.588Z",
  "household_members": [
    {
      "_id": "e4df9d77545247ccb135c46685c1ec36",
      "name": "Zi",
      "age": 22,
      "gender": "male",
      "dietary_restriction": "none"
    }
  ],
  "fridge": [
    {
      "_id": "40e9a1f581d1461f8a640160b4cc08bb",
      "Item_Name": "milk",
      "Quantity": 1.25,
      "Unit": "l",
      "Purchase_Date": "",
      "Expiry_Date": "2026-11-21",
      "Remarks": "none"
    }
  ],
  "consumption_history": [
    {
      "_id": "5a6657d1a8c14ebe816cc7195bcc8d6c",
      "Date_Range": 5,
      "Item_Name": "milk",
      "Quantity": 0.5,
      "Unit": "l",
      "Remarks": "breakfast",
      "Record_Date": "2026-11-13"
    },
    {
      "_id": "1eef2692c58b4a0a94bd2b45199ba1b6",
      "Date_Range": 1,
      "Item_Name": "milk",
      "Quantity": 0.25,
      "Unit": "l",
      "Remarks": "offline breakfast",
      "Record_Date": "2026-11-13"
    }
  ]
}
```

MongoDB and `households/current.json` now both contain version **5**, **1.25 l** of milk, and **two consumption records**. MongoDB supplies the new `updated_at` timestamp. `pending_households/current.json` is **removed**, rather than saved as an empty document. The local revision is refreshed, and the remembered household stays Zi.

Switching to Lim later replaces this device's snapshot and synchronization state with Lim's data, after pending edits are resolved and the target loads successfully. Both household documents remain in MongoDB.

## How data moves

1. Input updates the selected household's Python objects.
2. Save compares editable data with the loaded snapshot; unchanged data causes no cloud write.
3. Changed data is preserved in `pending_households/current.json` with its original cloud version.
4. MongoDB updates one `households` document only if both ID and version match.
5. Success refreshes `households/current.json` and clears the pending draft under a local process lock.
6. Conflict retains the draft. A failed or cancelled switch retains the current cache. A successful switch replaces it with the target household.

`device_settings.json` is a remembered access preference; `sync_state/current.json` holds local revision/registration bookkeeping. They are not cloud household documents. A temporary transaction journal recovers interrupted local writes.

Migration is an explicit command described in `HOUSEHOLD_GUIDE.md`; it was not run against existing data.
# Latest startup, forget, and save/exit fixes

See [QuantiTest cloud creation and switch output](new_test/QUANTITEST_CLOUD_OUTPUT.md) for a retained Atlas household and verification that switching changes both active stores and the local snapshot. QuantiTest ID: `HS-TU92-25LV-7Z5M`.

See [actual Docker recovery outputs](new_test/STARTUP_RECOVERY_OUTPUTS.md) for the numbered household menu, recovery after deleting a local snapshot, forgetting without deleting cached records, and option 6 saving while option 3 exits. These additional runs use temporary offline fixtures and leave Atlas untouched.

