# [STATUS] NEW ADDED
#__ Exercise the CLI's household flow and expiry no-ops without external services.
from unittest.mock import MagicMock, patch
from pathlib import Path
import subprocess
import sys
import pytest
from Application import Application
from modules.io.IO_manager import IO_manager
from modules.io.DatePrompt import DatePrompt
from modules.repositories.HouseholdDocument import HouseholdDocument as Doc
from new_test.fakes import MemoryCollection
from new_test.test_document import populated_document
from new_test.test_sessions import manager


# [STATUS] NEW ADDED
#__ Cancel and an existing historical date bypass edits and batch merging.
@pytest.mark.parametrize("answer", ["", "cancel", "2020-01-01"])
def test_expiry_prompt_noop(answer):
    prompt = DatePrompt("Edit: ", allow_past=True, current_date="2020-01-01")
    with patch("builtins.input", return_value=answer):
        assert prompt.ask() in (None, "2020-01-01")


# [STATUS] NEW ADDED
#__ Going into expiry editing and cancelling never calls the mutation method.
def test_fridge_ui_cancel_does_not_change(capsys):
    stores = Doc.to_stores(populated_document())
    fridge = stores["fridge"]
    before = fridge.to_dicts()
    with patch("builtins.input", side_effect=["1", "1", "", "3"]), patch.object(fridge, "change_expiry") as change:
        IO_manager().update_fridge(fridge)
    change.assert_not_called()
    assert fridge.to_dicts() == before
    assert "Expiry date unchanged" in capsys.readouterr().out


# [STATUS] NEW ADDED
#__ Remembered startup binds the household by ID, and empty profiles resume setup.
def test_remembered_and_empty_household_startup(tmp_path):
    collection = MemoryCollection()
    session = manager(tmp_path, collection)
    session.create_household("Family display name")
    session.local.remember(session.base)
    ui = MagicMock()
    ui.ask_remembered_household.return_value = "continue"
    restarted = manager(tmp_path, collection, ui)
    stores = restarted.start()
    assert stores["household"].household_id == session.base["_id"]
    assert stores["household"].name == "Family display name"
    assert stores["household"].get_members() == []
    ui.ask_household_name.assert_not_called()


# [STATUS] NEW ADDED
#__ Save-and-exit uses the new recovery path and never requests AI recommendations.
def test_application_save_exit(tmp_path):
    collection = MemoryCollection()
    ui = MagicMock()
    session = manager(tmp_path, collection, ui)
    document = populated_document()
    session.cloud().create(document)
    session.local.remember(document)
    ui.ask_remembered_household.return_value = "continue"
    ui.ask_main_menu_choice.return_value = "3"
    ai = MagicMock()
    Application(ui, session, ai, MagicMock()).run()
    ui.show_welcome_back.assert_called_once()
    assert ui.show_welcome_back.call_args.args[0].name == "Tan Family"
    ai.get_ai_recommendations.assert_not_called()
    assert collection.writes == []


# [STATUS] NEW ADDED
#__ Failed AI generation preserves consumption without checking out the planned cart.
def test_ai_failure_saves_consumption(tmp_path):
    collection = MemoryCollection()
    ui = MagicMock()
    session = manager(tmp_path, collection, ui)
    document = populated_document()
    session.cloud().create(document)
    session.local.remember(document)
    ui.ask_remembered_household.return_value = "continue"
    ui.ask_main_menu_choice.return_value = "1"
    ui.ask_last_use_days.return_value = 7
    ui.get_consumption_remarks.return_value = "none"
    ui.ask_days_until_next.return_value = 7
    ui.ask_use_recommended_cart.return_value = False
    ui.get_cart_remarks.return_value = "none"
    ui.get_consumption.side_effect = lambda fridge, history, days, remarks: history.add_record(fridge.consume("milk", 1, "l", days, remarks))
    ai = MagicMock()
    ai.get_ai_recommendations.return_value = (None, "test unavailable")
    with pytest.raises(RuntimeError, match="AI recommendation failed"):
        Application(ui, session, ai, MagicMock()).run()
    saved = session.cloud().load(document["_id"])
    assert saved["fridge"][0]["Quantity"] == 1
    assert len(saved["consumption_history"]) == 2
    ui.shopping_cart_conclusion.assert_not_called()


# [STATUS] NEW ADDED
#__ Display a household label instead of the first member's personal name.
def test_welcome_uses_household_name(capsys):
    IO_manager().show_welcome_back(Doc.to_stores(populated_document())["household"])
    output = capsys.readouterr().out
    assert "Tan Family" in output
    assert "Alice" not in output


# [STATUS] NEW ADDED
#__ Run real CLI prompts in a child process while isolating all writes in tmp_path.
def test_real_cli_offline_create_and_exit(tmp_path):
    script = """
import sys
from unittest.mock import MagicMock
from Application import Application
from modules.io.IO_manager import IO_manager
from modules.repositories.DB_manager import DB_manager
ui = IO_manager()
Application(ui, DB_manager(ui, database_dir=sys.argv[1], use_mongo=False), MagicMock(), MagicMock()).run()
"""
    inputs = (Path(__file__).parent / "docker_input.txt").read_text(encoding="utf-8")
    result = subprocess.run([sys.executable, "-c", script, str(tmp_path)], input=inputs,
                            text=True, capture_output=True, timeout=20)
    assert result.returncode == 0, result.stderr
    assert "Household summary:" in result.stdout
    assert "Welcome back, Smoke Test Household!" in result.stdout
    assert "Thank you for using" in result.stdout
