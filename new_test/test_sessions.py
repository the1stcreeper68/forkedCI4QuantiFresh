# [STATUS] NEW ADDED
#__ Exercise real session orchestration using temporary folders and a fake collection.
from copy import deepcopy
from unittest.mock import MagicMock
from pymongo.errors import ConnectionFailure
import pytest
from new_test.fakes import MemoryCollection
from new_test.test_document import populated_document
from modules.repositories.HouseholdDocument import HouseholdDocument as Doc
from modules.repositories.MongoDBRepository import MongoDBRepository
from modules.repositories.DB_manager import DB_manager
from modules.repositories.StorageErrors import SaveConflict, LocalConflict, HouseholdNotFound, CloudUnavailable


# [STATUS] NEW ADDED
#__ Give each simulated device its own one-household cache and shared cloud collection.
def manager(path, collection, ui=None, online=True):
    return DB_manager(ui or MagicMock(), database_dir=path, use_mongo=online,
                      mongo_factory=lambda: MongoDBRepository(collection=collection))


# [STATUS] NEW ADDED
#__ Different devices can open the same version, but only one conflicting save succeeds.
def test_two_devices_conflict_preserves_draft(tmp_path):
    collection = MemoryCollection()
    document = populated_document()
    MongoDBRepository(collection=collection).create(document)
    alice, bob = manager(tmp_path / "alice", collection), manager(tmp_path / "bob", collection)
    for session in (alice, bob):
        session.open_household(document["_id"])
    alice.stores["fridge"].get_items()[0].set_quantity(3)
    bob.stores["fridge"].get_items()[0].set_quantity(4)
    assert alice.save() == "saved"
    with pytest.raises(SaveConflict):
        bob.save()
    assert bob.local.read()["pending"]["fridge"][0]["Quantity"] == 4
    assert bob.base["version"] == 1
    assert alice.cloud().load(document["_id"])["fridge"][0]["Quantity"] == 3


# [STATUS] NEW ADDED
#__ Online and offline no-op saves leave cloud version/timestamps untouched.
def test_noop_and_reverted_changes(tmp_path):
    collection = MemoryCollection()
    session = manager(tmp_path, collection)
    session.create_household("Tan")
    before = session.cloud().load(session.base["_id"])
    session.stores["household"].name = "temporary"
    session.stores["household"].name = "Tan"
    assert session.save() == "unchanged"
    assert session.cloud().load(session.base["_id"]) == before
    assert collection.writes == []
    session.ui.send_message.assert_any_call("No changes to save. No cloud write was made and no pending draft is needed.")


# [STATUS] NEW ADDED
#__ An offline save reports the draft file, and reverting it reports removal explicitly.
def test_pending_save_and_revert_explain_outcome(tmp_path):
    collection = MemoryCollection()
    session = manager(tmp_path, collection)
    session.create_household("Tan")
    session.use_mongo = False
    session.stores["household"].name = "Offline change"
    assert session.save() == "offline"
    session.ui.send_message.assert_any_call(f"Pending draft: {session.local.paths['pending']}")
    assert session.local.paths["pending"].is_file()
    session.stores["household"].name = "Tan"
    assert session.save() == "unchanged"
    session.ui.send_message.assert_any_call("Changes were reverted. The pending draft was cleared; no cloud write was made.")
    assert not session.local.paths["pending"].exists()


# [STATUS] NEW ADDED
#__ Offline creation registers later and remains isolated from similarly named homes.
def test_offline_create_and_register(tmp_path):
    collection = MemoryCollection()
    session = manager(tmp_path, collection, online=False)
    session.create_household("Same name")
    first_id = session.base["_id"]
    session.stores["household"].name = "Offline edits"
    assert session.save() == "offline"
    assert session.local.read()["state"]["unregistered"]
    assert not collection.documents
    session.use_mongo = True
    assert session.save() == "saved"
    assert session.base["_id"] == first_id
    assert session.cloud().load(first_id)["name"] == "Offline edits"
    assert session.local.read()["pending"] is None


# [STATUS] NEW ADDED
#__ On a genuine collision, generate a new code without claiming the other household.
def test_offline_id_collision(tmp_path, monkeypatch):
    collection = MemoryCollection()
    existing = populated_document()
    existing["created_at"] = "2020-01-01T00:00:00.000Z"
    MongoDBRepository(collection=collection).create(existing)
    new_id = Doc.generate_id()
    ids = iter([existing["_id"], new_id])
    monkeypatch.setattr(Doc, "generate_id", lambda: next(ids))
    session = manager(tmp_path, collection)
    session.create_household("Collision")
    assert session.base["_id"] == new_id
    assert session.cloud().load(existing["_id"]) == existing


# [STATUS] NEW ADDED
#__ Stale offline edits never replace newer cloud values.
def test_stale_offline_sync_and_startup(tmp_path):
    collection = MemoryCollection()
    session = manager(tmp_path, collection)
    session.create_household("Tan")
    original = deepcopy(session.base)
    session.use_mongo = False
    session.stores["household"].name = "Offline"
    session.save()
    cloud = MongoDBRepository(collection=collection)
    original["name"] = "Newer cloud"
    cloud.save(original, 1)
    restarted = manager(tmp_path, collection)
    restarted.open_household(original["_id"])
    assert restarted.stores["household"].name == "Offline"
    with pytest.raises(SaveConflict):
        restarted.save()
    assert restarted.local.read()["pending"]["name"] == "Offline"


# [STATUS] NEW ADDED
#__ Failed switches and cancelled discards preserve the original local draft.
def test_switch_success_failure_and_offline_scope(tmp_path):
    collection = MemoryCollection()
    session = manager(tmp_path, collection)
    session.create_household("Tan")
    first = deepcopy(session.base)
    second = Doc.new("Lim")
    session.cloud().create(second)
    session.use_mongo = False
    session.stores["household"].name = "Edited Tan"
    session.save()
    before = session.local.read()
    with pytest.raises(SaveConflict):
        session.open_household(second["_id"])
    with pytest.raises(CloudUnavailable):
        session.open_household(second["_id"], discard=True)
    assert session.local.read() == before
    session.use_mongo = True
    with pytest.raises(HouseholdNotFound):
        session.open_household(Doc.generate_id(), discard=True)
    assert session.local.read() == before
    session.open_household(second["_id"], discard=True)
    assert session.local.read()["snapshot"] == second
    assert session.local.read()["pending"] is None
    assert session.cloud().load(first["_id"]) == first


# [STATUS] NEW ADDED
#__ A confirmed deletion is never recreated from local cache automatically.
def test_missing_cloud_keeps_local_data(tmp_path):
    collection = MemoryCollection()
    session = manager(tmp_path, collection)
    session.create_household("Tan")
    before = session.local.read()
    del collection.documents[session.base["_id"]]
    with pytest.raises(HouseholdNotFound):
        manager(tmp_path, collection).open_household(session.base["_id"])
    assert session.local.read() == before


# [STATUS] NEW ADDED
#__ Another instance's switch prevents both local and cloud writes by a stale instance.
def test_old_process_cannot_save_after_switch(tmp_path):
    collection = MemoryCollection()
    first = manager(tmp_path, collection)
    first.create_household("Tan")
    second_doc = Doc.new("Lim")
    first.cloud().create(second_doc)
    other = manager(tmp_path, collection)
    other.open_household(second_doc["_id"])
    first.stores["household"].name = "Old draft"
    with pytest.raises(LocalConflict):
        first.save()
    assert first.stores["household"].name == "Old draft"
    assert other.local.read()["snapshot"] == second_doc


# [STATUS] NEW ADDED
#__ A failed reload cannot let a stale process overwrite the newly selected household.
def test_failed_reload_keeps_old_session_fenced(tmp_path):
    collection = MemoryCollection()
    first = manager(tmp_path, collection)
    first.create_household("Tan")
    first.stores["household"].name = "Unsaved"
    second = Doc.new("Lim")
    first.cloud().create(second)
    other = manager(tmp_path, collection)
    other.open_household(second["_id"])
    collection.offline = True
    with pytest.raises(CloudUnavailable):
        first.reload_current()
    with pytest.raises(LocalConflict):
        first.save()
    assert other.local.read()["snapshot"] == second


# [STATUS] NEW ADDED
#__ A lost success response must not apply the same edit a second time.
def test_unknown_cloud_save_outcome_recovers_without_extra_version(tmp_path, monkeypatch):
    collection = MemoryCollection()
    session = manager(tmp_path, collection)
    session.create_household("Tan")
    session.stores["household"].name = "Changed"
    update = collection.find_one_and_update

    def lose_response(*args, **kwargs):
        update(*args, **kwargs)
        raise ConnectionFailure("response lost after commit")

    monkeypatch.setattr(collection, "find_one_and_update", lose_response)
    assert session.save() == "offline"
    assert session.local.read()["pending"]["version"] == 1
    monkeypatch.setattr(collection, "find_one_and_update", update)
    restarted = manager(tmp_path, collection)
    restarted.open_household(session.base["_id"])
    assert restarted.save() == "saved"
    assert restarted.base["version"] == 2
    assert len(collection.writes) == 1


# [STATUS] NEW ADDED
#__ Failed draft persistence prevents cloud updates and retains the in-memory edit.
def test_local_write_failure_prevents_cloud_update(tmp_path, monkeypatch):
    collection = MemoryCollection()
    session = manager(tmp_path, collection)
    session.create_household("Tan")
    session.stores["household"].name = "Unsaved"
    monkeypatch.setattr(session.local, "write", MagicMock(side_effect=OSError("disk full")))
    with pytest.raises(OSError):
        session.save()
    assert session.stores["household"].name == "Unsaved"
    assert collection.writes == []
    assert session.cloud().load(session.base["_id"])["name"] == "Tan"
