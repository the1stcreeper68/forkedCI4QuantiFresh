# [STATUS] NEW ADDED
#__ Validate the shared schema using domain records without production databases.
from copy import deepcopy
import pytest
from modules.repositories.HouseholdDocument import HouseholdDocument as Doc
from modules.core.Person import Person
from modules.core.FridgeItem import FridgeItem
from modules.core.ConsumptionRecord import ConsumptionRecord


# [STATUS] NEW ADDED
#__ Use realistic records to verify stable IDs and BSON/JSON round trips.
def populated_document():
    original = Doc.new("Tan Family")
    stores = Doc.to_stores(original)
    stores["household"].add_member(Person(1, "Alice", 22, "Female", "none"))
    stores["fridge"].add_item(FridgeItem("milk", 2, "l", "2026-11-13", "2026-11-20", "none"))
    stores["consumption_history"].add_record(ConsumptionRecord("milk", 1, "l", 5, "breakfast", "2026-11-13"))
    return Doc.from_stores(original, stores)


# [STATUS] NEW ADDED
#__ Verify that storage does not replace household identity with a member's name.
def test_round_trip_preserves_identity_and_records():
    document = populated_document()
    restored = Doc.from_cloud(Doc.to_cloud(document))
    assert restored == document
    assert Doc.from_stores(restored, Doc.to_stores(restored)) == document
    assert restored["name"] == "Tan Family"
    assert len({row["_id"] for field in Doc.EDITABLE[1:] for row in restored[field]}) == 3


# [STATUS] NEW ADDED
#__ Unchanged and reversed changes retain IDs and compare equal to the baseline.
def test_reverted_edits_and_generated_metadata():
    document = populated_document()
    stores = Doc.to_stores(document)
    item = stores["fridge"].get_items()[0]
    item.set_quantity(3)
    item.set_quantity(2)
    restored = Doc.from_stores(document, stores)
    restored["version"] += 1
    assert Doc.editable(restored) == Doc.editable(document)


# [STATUS] NEW ADDED
#__ Fail closed for duplicate embedded identities and invalid versions.
@pytest.mark.parametrize("change", ["id", "version", "field"])
def test_invalid_document_rejected(change):
    document = populated_document()
    if change == "id":
        document["fridge"][0]["_id"] = document["household_members"][0]["_id"]
    elif change == "version":
        document["version"] = True
    else:
        document["unknown"] = "data that must not be silently lost"
    with pytest.raises(ValueError):
        Doc.to_stores(document)


# [STATUS] NEW ADDED
#__ Names may repeat; random IDs follow the agreed human-readable format.
def test_ids_and_duplicate_names():
    first, second = Doc.new("Same name"), Doc.new("Same name")
    assert first["_id"] != second["_id"]
    assert Doc.normalize_id(" " + first["_id"].lower() + " ") == first["_id"]
    assert Doc.size(first) < Doc.WARNING_BYTES


# [STATUS] NEW ADDED
#__ Corrupt metadata and incomplete embedded records are rejected before loading.
@pytest.mark.parametrize("field", ["created_at", "fridge", "consumption_history"])
def test_incomplete_records_rejected(field):
    document = populated_document()
    if field == "created_at":
        document[field] = None
    else:
        del document[field][0]["Item_Name"]
    with pytest.raises(ValueError):
        Doc.to_stores(document)
