# [STATUS] NEW MODIFY
#__ Coordinate the active household, offline drafts, remembered access, and safe switching.
from copy import deepcopy
from pathlib import Path
import json
from pymongo.errors import DuplicateKeyError
from .AppPaths import AppPaths
from .JsonRepository import JsonRepository
from .HouseholdDocument import HouseholdDocument as Doc
from .StorageErrors import CloudUnavailable, HouseholdNotFound, SaveConflict, LocalConflict


class DB_manager:
    # [STATUS] NEW MODIFY
    #__ Persistence is injectable so validation never uses real household data.
    def __init__(self, ui, database_dir=None, use_mongo=True, mongo_factory=None, json_factory=None):
        self.ui = ui
        self.database_dir = Path(database_dir) if database_dir else AppPaths.DATABASE_DIR
        self.use_mongo = use_mongo
        self.mongo_factory = mongo_factory or self._create_mongo_repository
        self.local = (json_factory or JsonRepository)(folder=self.database_dir)
        self.repository = None
        self.stores = None
        self.base = None
        self.revision = None
        self.unregistered = False
        self.is_local = True

    # [STATUS] NEW MODIFY
    #__ Delay cloud connection until a household operation needs it.
    @staticmethod
    def _create_mongo_repository():
        from .MongoDBRepository import MongoDBRepository
        return MongoDBRepository()

    # [STATUS] NEW ADDED
    #__ Keep access policy separate so authentication can replace code-only access later.
    def authorize_household(self, household_id):
        return Doc.normalize_id(household_id)

    # [STATUS] NEW ADDED
    #__ Explicit local-only mode supports offline creation and the current cache.
    def cloud(self):
        if not self.use_mongo:
            raise CloudUnavailable("Cloud access is disabled (USE_MONGO=0).")
        if self.repository is None:
            self.repository = self.mongo_factory()
        return self.repository

    # [STATUS] NEW ADDED
    #__ Bind domain objects to the original cloud version and local revision.
    def _activate(self, bundle):
        self.base = deepcopy(bundle["snapshot"])
        self.unregistered = bundle["state"]["unregistered"]
        self.revision = bundle["state"]["revision"]
        self.stores = Doc.to_stores(bundle["pending"] or self.base)
        return self.stores

    # [STATUS] NEW ADDED
    #__ Detect unsaved edits without including generated timestamps in comparisons.
    def has_changes(self):
        return self.stores is not None and Doc.editable(Doc.from_stores(self.base, self.stores)) != Doc.editable(self.base)

    # [STATUS] NEW ADDED
    #__ Refuse to overwrite another process's revision or silently abandon pending edits.
    def _check_selection(self, bundle, discard):
        actual = bundle["state"]["revision"] if bundle["state"] else None
        if self.base is not None and actual != self.revision:
            raise LocalConflict("Local selection changed in another instance. Your draft remains in memory.")
        pending = bundle["pending"] is not None or (bundle["state"] and bundle["state"]["unregistered"])
        if not discard and (pending or self.has_changes()):
            raise SaveConflict("Save/sync the current household or explicitly discard its edits before switching.")
        return actual

    # [STATUS] NEW ADDED
    #__ Load a target successfully before replacing the one-household local cache.
    def open_household(self, household_id, discard=False):
        household_id = self.authorize_household(household_id)
        with self.local.locked():
            bundle = self.local.read()
            same = bundle["snapshot"] is not None and bundle["snapshot"]["_id"] == household_id
            if self.base is not None and self.has_changes() and not discard:
                raise SaveConflict("Save or discard your in-memory edits before reopening.")
            actual = bundle["state"]["revision"] if bundle["state"] else None
            if self.base is not None and actual != self.revision:
                raise LocalConflict("Local household changed in another instance; your draft remains in memory.")
            if not same:
                self._check_selection(bundle, discard)
            if same and bundle["state"]["unregistered"] and not discard:
                self.is_local = True
                self.ui.send_message("Opening the current local-only household. Use Save/sync to register it in MongoDB.")
                return self._activate(bundle)
            try:
                loaded = self.cloud().load(household_id)
                self.is_local = False
            except CloudUnavailable:
                if not same:
                    raise CloudUnavailable("Cannot switch offline. Only the current cached household is available.")
                self.is_local = True
                if discard:
                    raise CloudUnavailable("Cannot reload cloud data while offline; your draft was retained.")
                self.ui.send_message("MongoDB is unavailable. Opening only this household's current local data.")
                return self._activate(bundle)
            if same and bundle["pending"] is not None and not discard:
                self.ui.send_message("A local draft is available. It retains its original cloud version; use Save/sync to upload or review conflicts.")
                return self._activate(bundle)
            bundle = self.local.write(loaded, None, False, actual)
            settings = self.local.read_settings()
            if settings and settings["last_household_id"] == household_id:
                self.local.remember(loaded)
            return self._activate(bundle)

    # [STATUS] NEW ADDED
    #__ Offline creation persists first; cloud registration can be retried later.
    def create_household(self, name, discard=False):
        document = Doc.new(name)
        with self.local.locked():
            previous = self.local.read()
            revision = self._check_selection(previous, discard)
            bundle = self.local.write(document, document, True, revision)
            self._activate(bundle)
        self.ui.send_message(f"Household created: {document['name']} — {document['_id']}")
        result = self.save()
        if result == "offline":
            self.ui.send_message("This household is local only until its first successful cloud sync. Save the displayed ID; it may change if MongoDB detects a collision.")
        return self.stores

    # [STATUS] NEW MODIFY
    #__ Preserve a local draft before cloud writes and never retry with a newer version.
    def save(self):
        if self.base is None:
            raise RuntimeError("Select a household before saving.")
        draft = Doc.from_stores(self.base, self.stores)
        if Doc.size(draft) >= Doc.WARNING_BYTES:
            self.ui.send_message("Household exceeds 8 MiB. Export history and plan separate history storage before 16 MiB; nothing is deleted automatically.")
        with self.local.locked():
            bundle = self.local.read()
            actual = bundle["state"]["revision"] if bundle["state"] else None
            if actual != self.revision or bundle["snapshot"]["_id"] != self.base["_id"]:
                raise LocalConflict("Another instance saved or switched households. Your draft remains in memory; review/export it before reloading.")
            changed = Doc.editable(draft) != Doc.editable(self.base)
            if not changed and not self.unregistered:
                if bundle["pending"] is not None:
                    bundle = self.local.write(self.base, None, False, self.revision)
                    self.revision = bundle["state"]["revision"]
                    # [STATUS] NEW MODIFY
                    #__ Explain why a reverted draft disappears without uploading.
                    self.ui.send_message("Changes were reverted. The pending draft was cleared; no cloud write was made.")
                else:
                    # [STATUS] NEW MODIFY
                    #__ Save/sync must acknowledge a no-op instead of silently returning to the menu.
                    self.ui.send_message("No changes to save. No cloud write was made and no pending draft is needed.")
                return "unchanged"
            if bundle["pending"] != draft:
                bundle = self.local.write(self.base, draft, self.unregistered, self.revision)
                self.revision = bundle["state"]["revision"]
            try:
                cloud = self.cloud()
                if self.unregistered:
                    for attempt in range(8):
                        try:
                            registered = cloud.create(self.base)
                            break
                        except DuplicateKeyError:
                            self.base["_id"] = Doc.generate_id()
                            draft["_id"] = self.base["_id"]
                            self.stores["household"].household_id = self.base["_id"]
                            bundle = self.local.write(self.base, draft, True, self.revision)
                            self.revision = bundle["state"]["revision"]
                            self.ui.send_message(f"Household ID collision: your new ID is {self.base['_id']}.")
                            if self.local.read_settings():
                                self.local.remember(self.base)
                    else:
                        raise SaveConflict("Could not allocate a unique household ID. Local data is retained.")
                    saved = cloud.save(draft, self.base["version"]) if changed else registered
                else:
                    current = cloud.load(self.base["_id"])
                    if current["version"] == self.base["version"] + 1 and Doc.editable(current) == Doc.editable(draft):
                        saved = current  # The earlier write may have succeeded before its reply was lost.
                    else:
                        saved = cloud.save(draft, self.base["version"])
            except CloudUnavailable as error:
                self.is_local = True
                # [STATUS] NEW MODIFY
                #__ Explain the offline result and identify where the recoverable draft was saved.
                self.ui.send_message(str(error))
                self.ui.send_message("Changes are saved locally and await cloud sync.")
                self.ui.send_message(f"Pending draft: {self.local.paths['pending']}")
                return "offline"
            bundle = self.local.write(saved, None, False, self.revision)
            self._activate(bundle)
            self.is_local = False
            settings = self.local.read_settings()
            if settings and settings["last_household_id"] == saved["_id"]:
                self.local.remember(saved)
            self.ui.send_message("Household saved to MongoDB.")
            return "saved"

    # [STATUS] NEW ADDED
    #__ Show the draft and latest cloud data without mutating either version.
    def review(self):
        draft = Doc.from_stores(self.base, self.stores)
        self.ui.send_message("YOUR DRAFT (base version " + str(draft["version"]) + "):\n" + json.dumps(draft, indent=2))
        try:
            current = self.cloud().load(self.base["_id"])
            self.ui.send_message("LATEST CLOUD:\n" + json.dumps(current, indent=2))
        except (CloudUnavailable, HouseholdNotFound) as error:
            self.ui.send_message(str(error))

    # [STATUS] NEW ADDED
    #__ Explicit exports preserve a draft without adding another household to the cache.
    def export_draft(self, path):
        draft = Doc.from_stores(self.base, self.stores)
        target = Path(path).expanduser().resolve()
        if target.is_relative_to(self.database_dir.resolve()):
            raise ValueError("Choose an export path outside the active database folder.")
        if target.exists():
            raise ValueError("Export file already exists; choose a new filename.")
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("x", encoding="utf-8") as stream:
            json.dump(draft, stream, indent=2, ensure_ascii=False)
        return target

    # [STATUS] NEW ADDED
    #__ Conflicts offer review, explicit discard/reload, export, or continued editing.
    def save_interactive(self):
        while True:
            try:
                self.save()
                return True
            except (RuntimeError, ValueError, OSError) as error:
                self.ui.send_message(str(error))
                choice = self.ui.ask_save_recovery()
                if choice == "review":
                    self.review()
                elif choice == "reload":
                    if self.ui.confirm_discard():
                        try:
                            self.reload_current()
                            return False
                        except (RuntimeError, ValueError, OSError) as reload_error:
                            self.ui.send_message(str(reload_error))
                elif choice == "export":
                    try:
                        self.ui.send_message(f"Draft exported to {self.export_draft(self.ui.ask_export_path())}")
                    except (ValueError, OSError) as export_error:
                        self.ui.send_message(str(export_error))
                elif choice == "keep":
                    return False

    # [STATUS] NEW ADDED
    #__ A failed reload must not grant an old session the new selection's revision.
    def reload_current(self):
        with self.local.locked():
            bundle = self.local.read()
            if bundle["snapshot"] is None:
                raise HouseholdNotFound("There is no current household to reload.")
            loaded = self.cloud().load(bundle["snapshot"]["_id"])
            bundle = self.local.write(loaded, None, False, bundle["state"]["revision"])
            self.is_local = False
            return self._activate(bundle)

    # [STATUS] NEW MODIFY
    #__ Keep failed synchronization in the switch flow until the user explicitly resumes.
    def select_household(self, switching=False):
        discard = False
        bundle = self.local.read()
        # [STATUS] NEW ADDED
        #__ Startup switch can explicitly resume its cached household after cancellation.
        if switching and self.base is None and bundle["snapshot"] is not None:
            self._activate(bundle)
        if switching or bundle["pending"] is not None:
            dirty = self.has_changes() or bundle["pending"] is not None or (bundle["state"] and bundle["state"]["unregistered"])
            while dirty:
                choice = self.ui.ask_switch_resolution()
                if choice == "cancel":
                    return self.stores if self.stores is not None else self._activate(bundle)
                if choice == "sync":
                    if self.base is None:
                        self._activate(bundle)
                    if not self.save_interactive() or self.local.read()["pending"] is not None:
                        self.ui.send_message("Switch has not completed: current edits are not synced. Retry sync, explicitly discard, or choose Resume current household.")
                        continue
                    break
                elif choice == "discard":
                    discard = self.ui.confirm_discard()
                    if discard:
                        break
        while True:
            action = self.ui.ask_household_access(switching=switching)
            if action == "exit":
                return self.stores if switching else None
            try:
                if action == "create":
                    stores = self.create_household(self.ui.ask_household_name(), discard=discard)
                else:
                    # [STATUS] NEW ADDED
                    #__ Re-entering the active code is not a household switch.
                    household_id = self.authorize_household(self.ui.ask_household_id())
                    current_id = self.base["_id"] if self.base else (bundle["snapshot"]["_id"] if bundle["snapshot"] else None)
                    if switching and household_id == current_id:
                        self.ui.send_message("That is the current household ID. Enter a different ID to switch.")
                        continue
                    stores = self.open_household(household_id, discard=discard)
                self.local.remember(self.base if self.ui.ask_remember_household() else None)
                if self.is_local:
                    self.ui.send_message("Using the current household locally. Use Save/sync when cloud access is available.")
                if switching:
                    self.ui.send_message(f"Switched to {self.base['name']} ({self.base['_id']}).")
                return stores
            except (RuntimeError, ValueError, OSError) as error:
                self.ui.send_message(str(error))

    # [STATUS] NEW MODIFY
    #__ Repair incomplete local storage before offering remembered access or selection.
    def start(self):
        backup = self.local.prepare_startup()
        if backup is not None:
            self.ui.send_message(f"Local household cache was incomplete or invalid. Starting with an empty local cache. Surviving files were backed up to: {backup}. MongoDB was not changed.")
        settings = self.local.read_settings()
        while settings:
            choice = self.ui.ask_remembered_household(settings["last_household_name"])
            if choice == "exit":
                return None
            if choice == "forget":
                if self.forget_household():
                    break
                continue
            if choice == "switch":
                return self.select_household(switching=True)
            try:
                return self.open_household(settings["last_household_id"])
            except (RuntimeError, ValueError, OSError) as error:
                self.ui.send_message(str(error))
                settings = None
        return self.select_household()

    # [STATUS] NEW MODIFY
    #__ Sync pending edits before signing out; leave the cache and cloud household intact.
    def forget_household(self):
        bundle = self.local.read()
        if self.base is None and bundle["snapshot"] is not None:
            self._activate(bundle)
        dirty = self.has_changes() or bundle["pending"] is not None or (bundle["state"] and bundle["state"]["unregistered"])
        if dirty:
            if not self.save_interactive() or self.local.read()["pending"] is not None:
                self.ui.send_message("Cannot forget yet: pending edits must reach MongoDB first. Your household and draft are retained; retry when cloud access is available.")
                return False
        self.local.remember()
        self.base = self.stores = self.revision = None
        self.unregistered = False
        self.ui.send_message("Household forgotten. Local files and MongoDB data are retained. You can now enter another household ID.")
        return True

