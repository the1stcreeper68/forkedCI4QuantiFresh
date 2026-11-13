# [STATUS] NEW ADDED
#__ Migration validation uses generated legacy fixtures, never the real database.
from copy import deepcopy
import pytest
from new_test.fakes import MemoryCollection
from new_test.test_document import populated_document
from modules.repositories.HouseholdDocument import HouseholdDocument as Doc
from modules.repositories.MongoDBRepository import MongoDBRepository
from modules.repositories.migrate_household import migrate, convert_legacy


# [STATUS] NEW ADDED
#__ Repeated migration preserves counts and uses the same household and record IDs.
def test_migration_is_idempotent_and_preserves_values(tmp_path):
    stores = Doc.to_stores(populated_document())
    legacy = {key: value.to_dicts() for key, value in stores.items()}
    original = deepcopy(legacy)
    collection = MemoryCollection()
    cloud = MongoDBRepository(collection=collection)
    first = migrate(legacy, "Migrated", tmp_path, cloud, "test")
    document = cloud.load(first)
    second = migrate(legacy, "Migrated", tmp_path, cloud, "test")
    assert first == second
    assert len(collection.documents) == 1
    assert legacy == original
    assert (tmp_path / "legacy_backup.json").exists()
    restored = Doc.to_stores(document)
    assert {key: value.to_dicts() for key, value in restored.items()} == original
    document["name"] = "Changed after migration"
    cloud.save(document, 1)
    migrate(legacy, "Migrated", tmp_path, cloud, "test")
    assert cloud.load(first)["name"] == "Changed after migration"


# [STATUS] NEW ADDED
#__ Reject malformed data and rows that would be merged before writing to cloud.
def test_invalid_legacy_never_silently_drops_rows():
    stores = Doc.to_stores(populated_document())
    legacy = {key: value.to_dicts() for key, value in stores.items()}
    legacy["fridge"].append(deepcopy(legacy["fridge"][0]))
    with pytest.raises(ValueError, match="merge or lose"):
        convert_legacy(legacy, "Test")
