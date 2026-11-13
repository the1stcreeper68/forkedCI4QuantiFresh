# [STATUS] NEW ADDED
#__ Exercise switching through controller/UI boundaries without touching Atlas.
from unittest.mock import MagicMock
import pytest
from Application import Application
from new_test.fakes import MemoryCollection
from new_test.test_sessions import manager
from new_test.test_document import populated_document


# [STATUS] NEW ADDED
#__ Both startup and main-menu switches must rebind all stores to the selected household.
@pytest.mark.parametrize("startup", [True, False])
def test_switch_rebinds_household(tmp_path, startup):
    ui = MagicMock()
    collection = MemoryCollection()
    session = manager(tmp_path, collection, ui)
    first, second = populated_document(), populated_document()
    first["name"], second["name"] = "First", "Second"
    session.cloud().create(first)
    session.cloud().create(second)
    session.open_household(first["_id"])
    session.local.remember(first)
    ui.ask_remembered_household.return_value = "switch" if startup else "continue"
    ui.ask_household_access.return_value = "enter"
    ui.ask_household_id.return_value = second["_id"]
    ui.ask_remember_household.return_value = True
    ui.ask_main_menu_choice.side_effect = ["3"] if startup else ["4", "3"]
    restarted = manager(tmp_path, collection, ui)
    Application(ui, restarted, MagicMock(), MagicMock()).run()
    assert restarted.base["_id"] == second["_id"]
    assert ui.show_welcome_back.call_args.args[0].name == "Second"
    assert restarted.local.read_settings()["last_household_id"] == second["_id"]


# [STATUS] NEW ADDED
#__ A failed sync stays in switch resolution; a retry can finish the switch.
def test_failed_sync_can_retry_without_returning_to_old_menu(tmp_path):
    collection = MemoryCollection()
    ui = MagicMock()
    session = manager(tmp_path, collection, ui)
    session.create_household("First")
    first_id = session.base["_id"]
    second = populated_document()
    session.cloud().create(second)
    session.stores["household"].name = "Edited first"
    session.use_mongo = False
    def resolve():
        if ui.ask_switch_resolution.call_count == 2:
            session.use_mongo = True
        return "sync"
    ui.ask_switch_resolution.side_effect = resolve
    ui.ask_household_access.return_value = "enter"
    ui.ask_household_id.return_value = second["_id"]
    session.select_household(switching=True)
    assert ui.ask_switch_resolution.call_count == 2
    assert session.base["_id"] == second["_id"]
    assert session.cloud().load(first_id)["name"] == "Edited first"


# [STATUS] NEW ADDED
#__ Same-ID input prompts again; cancelling startup switching can resume cached stores.
def test_same_id_reprompts_and_startup_cancel_resumes(tmp_path):
    collection = MemoryCollection()
    ui = MagicMock()
    session = manager(tmp_path, collection, ui)
    session.create_household("First")
    session.local.remember(session.base)
    ui.ask_remembered_household.return_value = "switch"
    ui.ask_household_access.side_effect = ["enter", "exit"]
    ui.ask_household_id.return_value = session.base["_id"]
    restarted = manager(tmp_path, collection, ui)
    stores = restarted.start()
    assert stores["household"].name == "First"
    assert ui.ask_household_access.call_count == 2
    ui.send_message.assert_any_call("That is the current household ID. Enter a different ID to switch.")
