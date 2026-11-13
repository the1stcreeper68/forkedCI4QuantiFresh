# [STATUS] NEW ADDED
#__ Validate deleted-file startup and sign-out using isolated storage and a fake cloud.
from copy import deepcopy
from unittest.mock import MagicMock, patch
import pytest
from Application import Application
from modules.io.IO_manager import IO_manager
from modules.repositories.StorageErrors import LocalConflict
from new_test.fakes import MemoryCollection
from new_test.test_sessions import manager
from new_test.test_document import populated_document


# [STATUS] NEW ADDED
#__ Every access-menu number maps to the existing controller action.
@pytest.mark.parametrize("answer,action", [("1", "create"), ("2", "enter"), ("3", "exit")])
def test_numbered_access_menu(answer, action, capsys):
    with patch("builtins.input", return_value=answer):
        assert IO_manager().ask_household_access() == action
    assert "1. Create household" in capsys.readouterr().out


# [STATUS] NEW ADDED
#__ Missing snapshot/state combinations restart cleanly and preserve surviving drafts.
@pytest.mark.parametrize("missing", [("snapshot",), ("state",), ("snapshot", "pending"), ("snapshot", "pending", "state")])
def test_missing_files_restart_without_softlock(tmp_path, missing):
    collection = MemoryCollection()
    old = manager(tmp_path, collection)
    old.create_household("Before deletion")
    old.local.remember(old.base)
    cloud_before = deepcopy(collection.documents)
    old.use_mongo = False
    old.stores["household"].name = "Unsynced edit"
    old.save()
    for key in missing:
        old.local.paths[key].unlink(missing_ok=True)
    survivors = {key: path.read_bytes() for key, path in old.local.paths.items() if path.exists()}
    ui = MagicMock()
    ui.ask_household_access.return_value = "exit"
    # All three cache files removed is a valid empty cache; remove preferences too.
    if len(missing) == 3:
        old.local.settings.unlink()
    restarted = manager(tmp_path, collection, ui)
    assert restarted.start() is None
    ui.ask_household_access.assert_called_once()
    ui.ask_remembered_household.assert_not_called()
    assert restarted.local.read() == {"snapshot": None, "pending": None, "state": None}
    for key, content in survivors.items():
        backups = list((tmp_path / "recovery").glob("*/" + str(old.local.paths[key].relative_to(tmp_path))))
        assert len(backups) == 1
        assert backups[0].read_bytes() == content
    assert collection.documents == cloud_before
    with pytest.raises(LocalConflict):
        old.save()
    restarted.create_household("Fresh start")
    assert restarted.base["name"] == "Fresh start"


# [STATUS] NEW ADDED
#__ A failed backup leaves the original local files intact.
def test_recovery_backup_failure_keeps_data(tmp_path):
    session = manager(tmp_path, MemoryCollection(), online=False)
    session.create_household("Local")
    session.local.paths["snapshot"].unlink()
    pending = session.local.paths["pending"].read_bytes()
    with patch("modules.repositories.JsonRepository.shutil.copy2", side_effect=OSError("disk full")):
        with pytest.raises(OSError, match="disk full"):
            session.local.prepare_startup()
    assert session.local.paths["pending"].read_bytes() == pending


# [STATUS] NEW ADDED
#__ Forget uploads edits, retains cached files, then allows a different household ID.
def test_forget_syncs_and_allows_another_household(tmp_path):
    collection = MemoryCollection()
    session = manager(tmp_path, collection)
    session.create_household("First")
    first_id = session.base["_id"]
    session.local.remember(session.base)
    session.stores["household"].name = "Saved before forgetting"
    assert session.forget_household() is True
    assert session.cloud().load(first_id)["name"] == "Saved before forgetting"
    assert session.local.paths["snapshot"].exists()
    assert session.local.read_settings() is None
    assert session.stores is None
    second = populated_document()
    session.cloud().create(second)
    session.open_household(second["_id"])
    assert session.base["_id"] == second["_id"]
    assert session.cloud().load(first_id)["name"] == "Saved before forgetting"


# [STATUS] NEW ADDED
#__ Failed sync keeps access and the pending draft instead of silently abandoning edits.
def test_forget_offline_keeps_pending(tmp_path):
    session = manager(tmp_path, MemoryCollection(), online=False)
    session.create_household("Offline")
    session.local.remember(session.base)
    assert session.forget_household() is False
    assert session.local.read()["pending"] is not None
    assert session.local.read_settings() is not None
    assert session.stores is not None


# [STATUS] NEW ADDED
#__ Both startup Forget and main-menu Forget return to access without resuming old data.
@pytest.mark.parametrize("at_startup", [True, False])
def test_forget_returns_to_access_menu(tmp_path, at_startup):
    collection = MemoryCollection()
    ui = MagicMock()
    session = manager(tmp_path, collection, ui)
    document = populated_document()
    session.cloud().create(document)
    session.open_household(document["_id"])
    session.local.remember(document)
    session.use_mongo = False
    session.stores["household"].name = "Pending name"
    session.save()
    ui.ask_remembered_household.return_value = "forget" if at_startup else "continue"
    ui.ask_main_menu_choice.return_value = "5"
    ui.ask_household_access.return_value = "exit"
    restarted = manager(tmp_path, collection, ui)
    Application(ui, restarted, MagicMock(), MagicMock()).run()
    ui.ask_household_access.assert_called_once()
    ui.ask_switch_resolution.assert_not_called()
    assert restarted.local.read_settings() is None
    assert restarted.cloud().load(document["_id"])["name"] == "Pending name"


# [STATUS] NEW ADDED
#__ Option 6 stays open; option 3 exits after either a cloud save or a durable offline save.
@pytest.mark.parametrize("online", [True, False])
def test_save_stays_then_save_exits(tmp_path, online):
    ui = MagicMock()
    session = manager(tmp_path, MemoryCollection(), ui)
    document = populated_document()
    session.cloud().create(document)
    session.open_household(document["_id"])
    session.local.remember(document)
    session.use_mongo = False
    session.stores["household"].name = "Saved edit"
    session.save()
    session.use_mongo = online
    ui.ask_remembered_household.return_value = "continue"
    ui.ask_main_menu_choice.side_effect = ["6", "3"]
    restarted = manager(tmp_path, session.repository.collection, ui, online=online)
    Application(ui, restarted, MagicMock(), MagicMock()).run()
    assert ui.ask_main_menu_choice.call_count == 2
    ui.show_exit.assert_called_once()
    ui.send_message.assert_any_call("You are still in the application. Choose 3 to save/sync and exit.")
    assert (restarted.local.read()["pending"] is None) == online
