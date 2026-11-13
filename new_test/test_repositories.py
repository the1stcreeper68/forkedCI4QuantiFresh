# [STATUS] NEW ADDED
#__ Test repository isolation, conditional writes, local conflicts and crash recovery.
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import multiprocessing
import pytest
from new_test.fakes import MemoryCollection
from new_test.test_document import populated_document
from modules.repositories.HouseholdDocument import HouseholdDocument as Doc
from modules.repositories.MongoDBRepository import MongoDBRepository
from modules.repositories.JsonRepository import JsonRepository
from modules.repositories.StorageErrors import SaveConflict, LocalConflict, HouseholdNotFound, CloudUnavailable


# [STATUS] NEW ADDED
#__ A spawned process races through the real filesystem lock, not a mocked lock.
def local_writer(folder, document, revision, barrier, results):
    local = JsonRepository(folder)
    barrier.wait(timeout=10)
    try:
        local.write(document, document, False, revision)
        results.put("saved")
    except LocalConflict:
        results.put("conflict")


# [STATUS] NEW ADDED
#__ Only one process can commit a draft from the same local revision.
def test_two_real_local_processes(tmp_path):
    local = JsonRepository(tmp_path)
    document = populated_document()
    bundle = local.write(document, None, False, None)
    ctx = multiprocessing.get_context("spawn")
    barrier, results = ctx.Barrier(2), ctx.Queue()
    processes = [ctx.Process(target=local_writer, args=(str(tmp_path), document, bundle["state"]["revision"], barrier, results)) for _ in range(2)]
    try:
        for process in processes:
            process.start()
        for process in processes:
            process.join(timeout=15)
            assert process.exitcode == 0
        assert sorted(results.get(timeout=3) for _ in range(2)) == ["conflict", "saved"]
    finally:
        for process in processes:
            if process.is_alive():
                process.terminate()
                process.join(timeout=3)
        results.close()


# [STATUS] NEW ADDED
#__ Two clients editing one version cannot overwrite each other; other homes survive.
def test_atomic_cloud_race_and_isolation():
    collection = MemoryCollection()
    cloud = MongoDBRepository(collection=collection)
    first, second = populated_document(), Doc.new("Other")
    cloud.create(first)
    cloud.create(second)
    drafts = [deepcopy(first), deepcopy(first)]
    drafts[0]["name"], drafts[1]["name"] = "Alice", "Bob"

    def save(draft):
        try:
            return cloud.save(draft, 1)
        except SaveConflict:
            return None

    with ThreadPoolExecutor(2) as workers:
        results = list(workers.map(save, drafts))
    assert sum(result is not None for result in results) == 1
    assert cloud.load(first["_id"])["version"] == 2
    assert cloud.load(second["_id"]) == second


# [STATUS] NEW ADDED
#__ A missing cloud household must not be reported as a connectivity failure.
def test_missing_versus_unavailable():
    collection = MemoryCollection()
    cloud = MongoDBRepository(collection=collection)
    with pytest.raises(HouseholdNotFound):
        cloud.load(Doc.generate_id())
    collection.offline = True
    with pytest.raises(CloudUnavailable):
        cloud.load(Doc.generate_id())


# [STATUS] NEW ADDED
#__ Switches replace the current household and fence out older application instances.
def test_local_switch_rejects_old_writer(tmp_path):
    local = JsonRepository(tmp_path)
    first, second = populated_document(), Doc.new("Next")
    bundle = local.write(first, None, False, None)
    old_revision = bundle["state"]["revision"]
    local.write(second, None, False, old_revision)
    with pytest.raises(LocalConflict):
        local.write(first, first, False, old_revision)
    assert local.load(second["_id"]) == second
    with pytest.raises(HouseholdNotFound):
        local.load(first["_id"])
    assert not local.paths["pending"].exists()


# [STATUS] NEW ADDED
#__ Recover all three files together after interruption midway through replacement.
def test_interrupted_transaction_recovers(tmp_path, monkeypatch):
    local = JsonRepository(tmp_path)
    first, second = populated_document(), Doc.new("Next")
    bundle = local.write(first, None, False, None)
    apply = local._apply

    def interrupted(bundle):
        local.atomic_write(local.paths["snapshot"], bundle["snapshot"])
        raise OSError("power interruption")

    monkeypatch.setattr(local, "_apply", interrupted)
    with pytest.raises(OSError):
        local.write(second, None, False, bundle["state"]["revision"])
    monkeypatch.setattr(local, "_apply", apply)
    assert local.load(second["_id"]) == second
    assert not local.journal.exists()


# [STATUS] NEW ADDED
#__ Corrupt preferences must not destroy the pending household draft.
def test_settings_and_pending_are_independent(tmp_path):
    local = JsonRepository(tmp_path)
    document = populated_document()
    local.write(document, document, True, None)
    local.remember(document)
    assert local.read_settings()["last_household_id"] == document["_id"]
    local.remember()
    assert local.read_settings() is None
    local.settings.write_text("broken", encoding="utf-8")
    assert local.read_settings() is None
    assert local.read()["pending"] == document
