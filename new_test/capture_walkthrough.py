# [STATUS] NEW ADDED
#__ Capture real CLI output and real localhost MongoDB state using disposable demo data.
from contextlib import redirect_stdout
from datetime import date, timedelta
import io
import json
from pathlib import Path
import tempfile
from unittest.mock import MagicMock, patch
from uuid import uuid4
from pymongo import MongoClient
from bson import json_util
from Application import Application
from modules.io.IO_manager import IO_manager
from modules.repositories.DB_manager import DB_manager
from modules.repositories.MongoDBRepository import MongoDBRepository
from modules.repositories.StorageErrors import SaveConflict


# [STATUS] NEW ADDED
#__ Echo supplied answers next to the actual input prompts for a readable transcript.
def run_cli(path, cloud, answers, online):
    ui = IO_manager()
    manager = DB_manager(ui, database_dir=path, use_mongo=online, mongo_factory=lambda: cloud)
    entries = iter(answers)
    output = io.StringIO()

    def answer(prompt):
        value = next(entries)
        print(prompt + value)
        return value

    with redirect_stdout(output), patch("builtins.input", side_effect=answer):
        Application(ui, manager, MagicMock(), MagicMock()).run()
    return output.getvalue(), manager


# [STATUS] NEW ADDED
#__ Run only against a fixed localhost port; remove the generated database afterwards.
def main():
    client = MongoClient("mongodb://127.0.0.1:27028", serverSelectionTimeoutMS=5000, tz_aware=True)
    client.admin.command("ping")
    database = "quantifresh_demo_" + uuid4().hex
    cloud = MongoDBRepository(collection=client[database]["households"])
    sections = ["# Multi-household: captured application walkthrough\n",
                f"Captured on {date.today().isoformat()}. These are real application prompts/output and database reads from disposable demo data. Input answers are echoed by the capture harness. MongoDB ran locally in Docker, not Atlas. No existing user data was used. AI shopping recommendations are outside this demonstration.\n",
                "Run again with `python -m new_test.capture_walkthrough` while a disposable MongoDB is available on `127.0.0.1:27028`. The script removes only its generated demo database after capture.\n"]

    def transcript(title, explanation, output):
        sections.extend([f"## {title}\n", explanation + "\n", "```text\n" + "\n".join(line.rstrip() for line in output.rstrip().splitlines()) + "\n```\n"])

    def data(title, value):
        sections.extend([f"### {title}\n", "```json\n" + json.dumps(value, indent=2) + "\n```\n"])

    try:
        with tempfile.TemporaryDirectory(prefix="quantifresh-demo-") as folder:
            root = Path(folder)
            expiry = (date.today() + timedelta(days=7)).isoformat()
            output, first = run_cli(root / "device_a", cloud,
                ["create", "Zi Household", "yes", "Zi", "22", "male", "", "1", "yes", "milk", "2 l", expiry, "", "3", "3"], False)
            first_id = first.base["_id"]
            assert cloud.collection.count_documents({}) == 0
            transcript("1. Zi creates a household offline", "The household name is separate from Zi's member profile. The code is stored locally; no MongoDB document exists yet.", output)
            data("Pending local document before first upload", first.local.read()["pending"])

            output, first = run_cli(root / "device_a", cloud, ["continue", "6", "3"], True)
            transcript("2. Remembered startup and first cloud sync", "Continue reads the saved household ID. Save/sync registers the household and uploads its members/fridge. The local pending draft is cleared only after success.", output)
            data("Document read back from MongoDB", cloud.load(first_id))
            data("Local synchronization state", first.local.read()["state"])

            before = cloud.load(first_id)
            output, second = run_cli(root / "device_b", cloud,
                                     ["enter", first_id, "no", "2", "1", "1", "", "3", "3"], True)
            assert cloud.load(first_id) == before
            transcript("3. Another device joins and cancels an expiry edit", "Device B loads only the entered household. Blank expiry input leaves the document, version, and updated timestamp unchanged.", output)

            consumption_output = io.StringIO()
            with redirect_stdout(consumption_output), patch("builtins.input", side_effect=lambda prompt: (print(prompt + "0.5"), "0.5")[1]):
                first.ui.get_consumption(first.stores["fridge"], first.stores["consumption_history"], 5, "breakfast")
                first.save()
            transcript("4. Consumption moves stock into history", "This section invokes the actual consumption prompt and save operation directly, without running the AI grocery step. One atomic save updates both embedded arrays.", consumption_output.getvalue())
            saved = cloud.load(first_id)
            assert saved["fridge"][0]["Quantity"] == 1.5
            assert len(saved["consumption_history"]) == 1
            data("Fridge and history after consumption", {key: saved[key] for key in ("_id", "version", "fridge", "consumption_history")})

            first.open_household(first_id)
            second.open_household(first_id)
            race_output = io.StringIO()
            with redirect_stdout(race_output):
                print(f"Scripted two-device scenario: both loaded version {first.base['version']}.")
                first.stores["fridge"].change_expiry(first.stores["fridge"].get_items()[0], (date.today() + timedelta(days=8)).isoformat())
                print("Device A changes milk expiry and saves:")
                first.save()
                second.stores["consumption_history"].add_record(second.stores["fridge"].consume("milk", 0.5, "l", 1, "second device"))
                print("Device B tries to save consumption using the old version:")
                try:
                    second.save()
                    raise AssertionError("Expected conflict")
                except SaveConflict as error:
                    print(type(error).__name__ + ": " + str(error))
                print("Cloud milk quantity:", cloud.load(first_id)["fridge"][0]["Quantity"])
                print("Device B preserved draft milk quantity:", second.local.read()["pending"]["fridge"][0]["Quantity"])
            transcript("5. Concurrent saves preserve the losing draft", "This is a scripted two-session scenario using the real repository and MongoDB, not fabricated console output. Device B's stale save cannot replace A's update. The UI offers review/export/reload when this occurs during normal use.", race_output.getvalue())

            _, third = run_cli(root / "device_c", cloud,
                              ["create", "Lim Household", "no", "Lim", "35", "female", "", "1", "no", "3"], True)
            second_id = third.base["_id"]
            output, first = run_cli(root / "device_a", cloud,
                                   ["continue", "4", "enter", second_id, "yes", "3"], True)
            transcript("6. Switch replaces only the current local household", "Device A switches to an existing household after it is loaded successfully. Zi's household remains in MongoDB. Device B still retains its own pending Zi draft.", output)
            data("Device A current household", first.local.read()["snapshot"])
            assert first.local.read()["snapshot"]["_id"] == second_id
            assert first.local.read()["pending"] is None
            data("Cloud households remain separate", [{"_id": key, "name": cloud.load(key)["name"]} for key in (first_id, second_id)])

            # [STATUS] NEW ADDED
            #__ Capture native MongoDB records, including BSON dates, alongside local files.
            sections.extend(["## 7. What the cloud database records look like\n",
                "The following records are read directly from the disposable MongoDB database used in this run. Atlas uses the same collection/document schema; these are not records copied from your Atlas database. Atlas connectivity and workflow tests are recorded separately in `new_test/ATLAS_VALIDATION_RESULTS.md`.\n",
                "```text\n<configured MongoDB database>\n└── households (collection)\n    ├── " + first_id + "  Zi Household\n    └── " + second_id + "  Lim Household\n```\n",
                "There are **two top-level documents**, one per household. Members, fridge batches, and consumption events are embedded records inside their household document; they are not separate collections. Every embedded record has its own stable `_id`, without repeating the household ID.\n",
                "These full records use MongoDB Extended JSON: `{\"$date\": \"...\"}` represents a BSON date. The local JSON files below use ordinary UTC timestamp strings. Food dates remain `YYYY-MM-DD` strings in both places.\n"])
            for household_id in (first_id, second_id):
                raw = cloud.collection.find_one({"_id": household_id})
                sections.extend([f"### Cloud document: {raw['name']}\n",
                                 "```json\n" + json_util.dumps(raw, indent=2) + "\n```\n"])

            # [STATUS] NEW ADDED
            #__ Demonstrate a registered household editing offline with its base unchanged.
            offline = DB_manager(IO_manager(), database_dir=root / "device_d", mongo_factory=lambda: cloud)
            offline.open_household(first_id)
            offline.local.remember(offline.base)
            base_version = offline.base["version"]
            offline.use_mongo = False
            offline_output = io.StringIO()
            with redirect_stdout(offline_output):
                print("Scripted offline scenario: Zi records another 0.25 l of milk consumed.")
                offline.stores["consumption_history"].add_record(
                    offline.stores["fridge"].consume("milk", 0.25, "l", 1, "offline breakfast"))
                assert offline.save() == "offline"
            transcript("8. What the offline database files look like",
                       "This is a fresh simulated device using Zi's already registered household. The harness disables cloud access, records consumption through the domain methods, and invokes the real save path. MongoDB stays unchanged until synchronization.", offline_output.getvalue())
            sections.append("```text\napp_data/database/\n├── device_settings.json\n├── households/\n│   └── current.json              last cloud snapshot\n├── pending_households/\n│   └── current.json              offline edits awaiting upload\n└── sync_state/\n    └── current.json              local concurrency bookkeeping\n```\n\n"
                            "All these files refer to **Zi's current household only**. Lim's records are not cached on this device. The lock file and temporary recovery journal are implementation files, not extra household records.\n")
            local_bundle = offline.local.read()
            data("device_settings.json — remembered access, not a cloud document", offline.local.read_settings())
            data("households/current.json — last confirmed cloud data", local_bundle["snapshot"])
            data("pending_households/current.json — offline draft", local_bundle["pending"])
            data("sync_state/current.json — local revision and registration status", local_bundle["state"])
            assert local_bundle["snapshot"] == cloud.load(first_id)
            assert local_bundle["pending"]["version"] == base_version
            sections.append("| Location before sync | Version | Milk remaining | History records |\n"
                            "|---|---:|---:|---:|\n"
                            f"| MongoDB Zi document | {base_version} | 1.5 l | 1 |\n"
                            f"| Local snapshot | {base_version} | 1.5 l | 1 |\n"
                            f"| Local pending draft | {base_version} | 1.25 l | 2 |\n\n"
                            "The pending draft keeps the **original cloud version and metadata timestamps**. Offline edits do not claim a newer cloud version. `unregistered: false` means the household already exists in MongoDB, even though this device is currently offline. A newly created offline household instead has `unregistered: true` until first registration. The local `revision` token is separate from MongoDB's `version`.\n")

            # [STATUS] NEW ADDED
            #__ Capture successful reconciliation and prove the pending file is removed.
            offline.use_mongo = True
            sync_output = io.StringIO()
            with redirect_stdout(sync_output):
                assert offline.save() == "saved"
            transcript("9. What changes after the offline draft syncs",
                       f"Cloud access is restored. The update matches household ID and base version {base_version}, so the fridge and history are committed together. If another device had changed that version, the draft would remain local instead.", sync_output.getvalue())
            synced = offline.local.read()
            assert synced["snapshot"] == cloud.load(first_id)
            assert synced["pending"] is None
            assert not offline.local.paths["pending"].exists()
            data("Updated local snapshot — same logical document as MongoDB", synced["snapshot"])
            sections.append(f"MongoDB and `households/current.json` now both contain version **{synced['snapshot']['version']}**, **1.25 l** of milk, and **two consumption records**. MongoDB supplies the new `updated_at` timestamp. `pending_households/current.json` is **removed**, rather than saved as an empty document. The local revision is refreshed, and the remembered household stays Zi.\n\n"
                            "Switching to Lim later replaces this device's snapshot and synchronization state with Lim's data, after pending edits are resolved and the target loads successfully. Both household documents remain in MongoDB.\n")

        sections.append("## How data moves\n\n"
            "1. Input updates the selected household's Python objects.\n"
            "2. Save compares editable data with the loaded snapshot; unchanged data causes no cloud write.\n"
            "3. Changed data is preserved in `pending_households/current.json` with its original cloud version.\n"
            "4. MongoDB updates one `households` document only if both ID and version match.\n"
            "5. Success refreshes `households/current.json` and clears the pending draft under a local process lock.\n"
            "6. Conflict retains the draft. A failed or cancelled switch retains the current cache. A successful switch replaces it with the target household.\n\n"
            "`device_settings.json` is a remembered access preference; `sync_state/current.json` holds local revision/registration bookkeeping. They are not cloud household documents. A temporary transaction journal recovers interrupted local writes.\n\n"
            "Migration is an explicit command described in `HOUSEHOLD_GUIDE.md`; it was not run against existing data.\n")
        destination = Path(__file__).resolve().parents[1] / "HOUSEHOLD_RUNNING_OUTPUTS.md"
        destination.write_text("\n".join(sections), encoding="utf-8")
        print(f"Captured walkthrough: {destination}")
    finally:
        client.drop_database(database)
        client.close()


# [STATUS] NEW ADDED
#__ Importing the capture utility has no side effects.
if __name__ == "__main__":
    main()
