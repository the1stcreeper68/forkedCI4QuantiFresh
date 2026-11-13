# [STATUS] NEW ADDED
#__ Opt-in integration tests use only a disposable localhost MongoDB, never Atlas.
import os
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
import pytest
from pymongo import MongoClient
from modules.repositories.MongoDBRepository import MongoDBRepository
from modules.repositories.HouseholdDocument import HouseholdDocument as Doc
from modules.repositories.StorageErrors import SaveConflict


# [STATUS] NEW ADDED
#__ Require an explicit local test URI and delete only the generated test database.
@pytest.fixture
def live_cloud():
    uri = os.getenv("HOUSEHOLD_TEST_MONGO_URI")
    if not uri:
        pytest.skip("Set HOUSEHOLD_TEST_MONGO_URI for disposable localhost MongoDB tests.")
    if not uri.startswith("mongodb://127.0.0.1:"):
        pytest.fail("Integration tests require a localhost-only MongoDB URI.")
    client = MongoClient(uri, serverSelectionTimeoutMS=5000, tz_aware=True)
    client.admin.command("ping")
    name = "quantifresh_validation_" + uuid4().hex
    try:
        yield MongoDBRepository(collection=client[name]["households"])
    finally:
        client.drop_database(name)
        client.close()


# [STATUS] NEW ADDED
#__ Verify MongoDB itself enforces the atomic version predicate with real BSON dates.
def test_real_mongodb_atomic_save(live_cloud):
    document = Doc.new("Integration home")
    live_cloud.create(document)

    def update(name):
        draft = dict(document, name=name)
        try:
            return live_cloud.save(draft, 1)
        except SaveConflict:
            return None

    with ThreadPoolExecutor(2) as workers:
        results = list(workers.map(update, ["Alice", "Bob"]))
    assert sum(item is not None for item in results) == 1
    saved = live_cloud.load(document["_id"])
    assert saved["version"] == 2
    assert isinstance(saved["updated_at"], str)
    assert live_cloud.collection.count_documents({}) == 1
