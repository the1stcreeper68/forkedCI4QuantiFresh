# QuantiTest cloud creation and switch verification

Created 2026-11-13 in `QuantiFresh.households` using the configured QuantiFresh database account. The household is retained in Atlas. Existing cloud records and the real local cache were not changed.

```json
{
  "_id": "HS-TU92-25LV-7Z5M",
  "name": "QuantiTest",
  "version": 1,
  "created_at": "2026-11-13T09:36:52.023Z",
  "updated_at": "2026-11-13T09:36:52.023Z",
  "household_members": [],
  "fridge": [],
  "consumption_history": []
}
```

## Actual switch output against Atlas

Used a temporary local cache. Inputs: `2`, the new household ID, `no`. Cloud access used the real repository; only terminal input was supplied automatically.

```text

Household menu:
  1. Create household
  2. Enter household ID
  3. Cancel switch
Switched to QuantiTest (HS-TU92-25LV-7Z5M).
```

Verified active stores and local snapshot both point to QuantiTest. Its member, fridge and history arrays are empty; entering it in the full app will request initial setup.

Regression checks: **165 passed, 7 optional integration checks skipped**.

Reference: [PyMongo insert and read operations](https://www.mongodb.com/docs/languages/python/pymongo-driver/current/crud/).
