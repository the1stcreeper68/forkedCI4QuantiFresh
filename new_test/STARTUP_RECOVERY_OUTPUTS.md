# Startup, forget and save/exit — actual Docker output

Captured 2026-11-13 from the rebuilt `quantifresh` image. Temporary fixture households only; `USE_MONGO=0`. These are real CLI outputs, not proof of Atlas sync. No real local files or cloud records were modified or deleted. Online forgetting and conflict behavior are covered by isolated regression tests.

Validation: `python -m pytest test_script.py new_test -q` — **161 passed, 7 skipped** (optional live integrations).

## Deleted snapshot

Inputs: `3`

```text
Welcome to the QuantiFresh!
Local household cache was incomplete or invalid. Starting with an empty local cache. Surviving files were backed up to: /app/app_data/database/recovery/4e03eb9d427d4f128e818c1366acdaab. MongoDB was not changed.

Household menu:
  1. Create household
  2. Enter household ID
  3. Exit
Enter 1-3:
```

## Forget and return to access

Inputs: `1, 5, 3`

```text
Welcome to the QuantiFresh!

Household menu:
  1. Continue with Zi Demo Household
  2. Switch household
  3. Forget household
  4. Exit
Enter 1-4: MongoDB is unavailable. Opening only this household's current local data.
Welcome back, Zi Demo Household! Household ID: HS-NYSR-W3L5-TNV7

What would you like to do?
  1. Update consumption and plan groceries
  2. Edit expiry dates or delete items from your fridge
  3. Save/sync and exit the program
  4. Switch household
  5. Save/sync and forget household
  6. Save/sync now and stay in the application
Enter 1-6: Household forgotten. Local files and MongoDB data are retained. You can now enter another household ID.

Household menu:
  1. Create household
  2. Enter household ID
  3. Exit
Enter 1-3: Thank you for using the QuantiFresh!
```

## Save pending and exit

Inputs: `1, 6, 3`

```text
Welcome to the QuantiFresh!

Household menu:
  1. Continue with Zi Demo Household
  2. Switch household
  3. Forget household
  4. Exit
Enter 1-4: MongoDB is unavailable. Opening only this household's current local data.
Welcome back, Zi Offline Edit! Household ID: HS-U327-SZDU-MR4Y

What would you like to do?
  1. Update consumption and plan groceries
  2. Edit expiry dates or delete items from your fridge
  3. Save/sync and exit the program
  4. Switch household
  5. Save/sync and forget household
  6. Save/sync now and stay in the application
Enter 1-6: Cloud access is disabled (USE_MONGO=0).
Changes are saved locally and await cloud sync.
Pending draft: /app/app_data/database/pending_households/current.json
You are still in the application. Choose 3 to save/sync and exit.
Welcome back, Zi Offline Edit! Household ID: HS-U327-SZDU-MR4Y

What would you like to do?
  1. Update consumption and plan groceries
  2. Edit expiry dates or delete items from your fridge
  3. Save/sync and exit the program
  4. Switch household
  5. Save/sync and forget household
  6. Save/sync now and stay in the application
Enter 1-6: Cloud access is disabled (USE_MONGO=0).
Changes are saved locally and await cloud sync.
Pending draft: /app/app_data/database/pending_households/current.json
Thank you for using the QuantiFresh!
```

## Documentation consulted

- [Python filesystem replacement](https://docs.python.org/3/library/os.html#os.replace): existing journal/replacement mechanism retained for resetting active files.
- [MongoDB single-document atomicity](https://www.mongodb.com/docs/manual/core/write-operations-atomicity/): existing household version checks retained; no cloud deletion added.
