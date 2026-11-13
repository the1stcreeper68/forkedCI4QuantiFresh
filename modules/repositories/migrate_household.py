# [STATUS] NEW ADDED
#__ Explicit migration only: back up legacy input and never delete old data.
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from bson import json_util
from filelock import FileLock
from .AppPaths import AppPaths
from .HouseholdDocument import HouseholdDocument as Doc
from .JsonRepository import JsonRepository
from .MongoDBRepository import MongoDBRepository
from modules.core.Household import Household
from modules.core.Fridge import Fridge
from modules.core.ConsumptionHistory import ConsumptionHistory


# [STATUS] NEW ADDED
#__ Convert legacy rows through existing domain validation, refusing silent row loss.
def convert_legacy(rows, name):
    document = Doc.new(name)
    stores = {"household": Household(document["_id"], name),
              "fridge": Fridge(), "consumption_history": ConsumptionHistory()}
    for key, store in stores.items():
        if key not in rows or not isinstance(rows[key], list):
            raise ValueError(f"Missing legacy array: {key}")
        clean = [{k: v for k, v in row.items() if k != "_id"} for row in rows[key]]
        errors = store.load_dicts(clean)
        if errors:
            raise ValueError("Migration stopped: " + "; ".join(errors))
        if len(store.to_dicts()) != len(clean):
            raise ValueError(f"Migration would merge or lose {key} rows; resolve duplicates first.")
        # Legacy constructors supply defaults; compare every explicitly stored value.
        for old, restored in zip(clean, store.to_dicts()):
            if any(key not in restored or restored[key] != value for key, value in old.items()):
                raise ValueError("Migration would change existing values; source data was retained.")
    result = Doc.from_stores(document, stores)
    Doc.size(result)
    return result


# [STATUS] NEW ADDED
#__ A durable manifest reuses the same generated IDs after retries or interrupted uploads.
def migrate(rows, name, backup_dir, cloud, source_identity):
    backup_dir = Path(backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    with FileLock(str(backup_dir / ".migration.lock"), timeout=15):
        raw = json_util.dumps(rows, sort_keys=True)
        fingerprint = hashlib.sha256((source_identity + raw).encode()).hexdigest()
        manifest_path = backup_dir / "migration_manifest.json"
        manifest = JsonRepository.read_json(manifest_path)
        if manifest is not None:
            if manifest["fingerprint"] != fingerprint or manifest["name"] != name:
                raise ValueError("This migration manifest belongs to different source data/name. Do not overwrite it.")
            document = manifest["document"]
        else:
            document = convert_legacy(rows, name)
            backup = backup_dir / "legacy_backup.json"
            if backup.exists():
                if backup.read_text(encoding="utf-8") != raw:
                    raise ValueError("Backup directory contains different legacy data.")
            else:
                with backup.open("x", encoding="utf-8") as stream:
                    stream.write(raw)
                    stream.flush()
                    import os
                    os.fsync(stream.fileno())
            manifest = {"fingerprint": fingerprint, "name": name, "document": document, "complete": False}
            JsonRepository.atomic_write(manifest_path, manifest)
        if manifest["complete"]:
            # A migrated household may since have changed; never reset it to the backup.
            cloud.load(document["_id"])
            return document["_id"]
        cloud.create(document)
        if cloud.load(document["_id"]) != document:
            raise RuntimeError("Migration verification failed; backup and legacy data remain untouched.")
        manifest["complete"] = True
        JsonRepository.atomic_write(manifest_path, manifest)
        return document["_id"]


# [STATUS] NEW ADDED
#__ Only this explicitly invoked command may read the old full collections.
def main():
    parser = argparse.ArgumentParser(description="Back up and migrate legacy data into one cloud household; old data is retained.")
    parser.add_argument("--source", choices=("json", "cloud"), required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--backup-dir", required=True, type=Path,
                        help="Dedicated backup directory; reuse exactly this directory for all retries.")
    parser.add_argument("--json-dir", type=Path, default=AppPaths.DATABASE_DIR)
    parser.add_argument("--confirm-legacy-apps-stopped", action="store_true", required=True)
    args = parser.parse_args()
    if args.backup_dir.resolve().is_relative_to(args.json_dir.resolve()):
        parser.error("Keep migration backups outside the active database folder.")
    cloud = MongoDBRepository()
    names = ("household", "fridge", "consumption_history")
    if args.source == "json":
        rows = {key: json.loads((args.json_dir / (key + ".json")).read_text(encoding="utf-8")) for key in names}
        identity = "json:" + str(args.json_dir.resolve())
    else:
        rows = {key: list(cloud.database[key].find({}).sort("_id", 1)) for key in names}
        identity = "cloud:" + cloud.database.name
    household_id = migrate(rows, args.name, args.backup_dir, cloud, identity)
    print(f"Migration verified. Household ID: {household_id}. Old data and backups retained.")


# [STATUS] NEW ADDED
#__ Importing migration helpers never contacts MongoDB or changes existing data.
if __name__ == "__main__":
    main()
