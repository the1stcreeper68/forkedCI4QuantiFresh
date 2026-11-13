# [STATUS] NEW ADDED
#__ Explicit Atlas validation creates only disposable databases on a confirmed host.
from concurrent.futures import ThreadPoolExecutor
import os
from urllib.parse import urlsplit
from uuid import uuid4
from unittest.mock import MagicMock
import pytest
from pymongo import MongoClient
from modules.repositories.DB_manager import DB_manager
from modules.repositories.HouseholdDocument import HouseholdDocument as Doc
from modules.repositories.MongoDBRepository import MongoDBRepository
from modules.repositories.StorageErrors import SaveConflict
from new_test.test_document import populated_document


# [STATUS] NEW ADDED
#__ Require credentials via environment and a separately confirmed destination host.
@pytest.fixture
def atlas_cloud():
    uri = os.getenv("HOUSEHOLD_ATLAS_TEST_URI")
    if not uri:
        pytest.skip("Atlas validation requires explicit temporary test credentials.")
    expected_host = os.getenv("HOUSEHOLD_ATLAS_TEST_HOST")
    if not expected_host or urlsplit(uri).hostname != expected_host:
        pytest.fail("Atlas test host must match the explicitly confirmed destination.")
    client = MongoClient(uri, serverSelectionTimeoutMS=15000, connectTimeoutMS=10000,
                         socketTimeoutMS=15000, tz_aware=True)
    # [STATUS] NEW MODIFY
    #__ Atlas shared clusters limit database names to 38 bytes, including the prefix.
    database = "qfval_" + uuid4().hex
    try:
        client.admin.command("ping")
        yield MongoDBRepository(collection=client[database]["households"])
    finally:
        try:
            # [STATUS] NEW MODIFY
            #__ Remove only this test's collection; the account need not have dropDatabase.
            client[database].drop_collection("households")
        finally:
            client.close()


# [STATUS] NEW ADDED
#__ Real Atlas version predicates allow only one writer from the same base version.
def test_atlas_atomic_race_and_household_isolation(atlas_cloud):
    first, other = populated_document(), Doc.new("Another household")
    atlas_cloud.create(first)
    atlas_cloud.create(other)

    def save(name):
        draft = dict(first, name=name)
        try:
            return atlas_cloud.save(draft, first["version"])
        except SaveConflict:
            return None

    with ThreadPoolExecutor(2) as workers:
        saved = list(workers.map(save, ["Zi", "Other editor"]))
    assert sum(result is not None for result in saved) == 1
    assert atlas_cloud.load(first["_id"])["version"] == 2
    assert atlas_cloud.load(other["_id"]) == other
    assert atlas_cloud.collection.count_documents({}) == 2


# [STATUS] NEW ADDED
#__ Offline creation uploads through the production manager without changing its ID.
def test_atlas_offline_creation_and_noop_save(atlas_cloud, tmp_path):
    session = DB_manager(MagicMock(), database_dir=tmp_path, use_mongo=False,
                         mongo_factory=lambda: atlas_cloud)
    session.create_household("Zi offline household")
    household_id = session.base["_id"]
    session.stores["household"].name = "Zi synced household"
    session.save()
    assert atlas_cloud.collection.count_documents({}) == 0
    session.use_mongo = True
    assert session.save() == "saved"
    before = atlas_cloud.load(household_id)
    assert before["name"] == "Zi synced household"
    assert session.local.read()["pending"] is None
    assert session.save() == "unchanged"
    assert atlas_cloud.load(household_id) == before


# [STATUS] NEW ADDED
#__ Consumption and fridge changes commit together; stale offline edits stay local.
def test_atlas_consumption_and_stale_offline_draft(atlas_cloud, tmp_path):
    document = populated_document()
    atlas_cloud.create(document)
    sessions = [DB_manager(MagicMock(), database_dir=tmp_path / name,
                           mongo_factory=lambda: atlas_cloud) for name in ("a", "b")]
    for session in sessions:
        session.open_household(document["_id"])
    first, second = sessions
    first.stores["consumption_history"].add_record(first.stores["fridge"].consume("milk", 0.5, "l", 1, "Zi breakfast"))
    first.save()
    cloud = atlas_cloud.load(document["_id"])
    assert cloud["fridge"][0]["Quantity"] == 1.5
    assert len(cloud["consumption_history"]) == 2
    second.use_mongo = False
    second.stores["fridge"].get_items()[0].set_quantity(3)
    assert second.save() == "offline"
    second.use_mongo = True
    with pytest.raises(SaveConflict):
        second.save()
    assert second.local.read()["pending"]["fridge"][0]["Quantity"] == 3
    assert atlas_cloud.load(document["_id"]) == cloud


# [STATUS] NEW ADDED
#__ Switching replaces the local household but preserves both documents in Atlas.
def test_atlas_switch_keeps_only_current_cache(atlas_cloud, tmp_path):
    first, second = populated_document(), Doc.new("Switch target")
    atlas_cloud.create(first)
    atlas_cloud.create(second)
    session = DB_manager(MagicMock(), database_dir=tmp_path, mongo_factory=lambda: atlas_cloud)
    session.open_household(first["_id"])
    session.open_household(second["_id"])
    assert session.local.read()["snapshot"] == second
    assert session.local.read()["pending"] is None
    assert atlas_cloud.load(first["_id"]) == first
    assert atlas_cloud.load(second["_id"]) == second
