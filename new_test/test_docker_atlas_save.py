# [STATUS] NEW ADDED
#__ Validate the normal rebuilt app image against Atlas with isolated local/cloud data.
from datetime import date, timedelta
import json
import os
from urllib.parse import urlsplit
from uuid import uuid4
import subprocess
import pytest
from pymongo import MongoClient


# [STATUS] NEW ADDED
#__ Real CLI runs must create cloud records, preserve offline drafts, and upload on restart.
def test_docker_cli_online_offline_and_resync(tmp_path):
    uri = os.getenv("HOUSEHOLD_ATLAS_TEST_URI")
    host = os.getenv("HOUSEHOLD_ATLAS_TEST_HOST")
    if os.getenv("HOUSEHOLD_TEST_DOCKER_ATLAS") != "1" or not uri:
        pytest.skip("Opt in to the rebuilt Docker image's Atlas save test.")
    assert host and urlsplit(uri).hostname == host
    database = "qfval_" + uuid4().hex
    environment = dict(os.environ, MONGODB_URI=uri)
    client = MongoClient(uri, serverSelectionTimeoutMS=15000, tz_aware=True)

    # [STATUS] NEW ADDED
    #__ Pass the URI through the environment, not a command argument or saved file.
    def run(answers, online):
        command = ["docker", "run", "--rm", "-i", "-e", "MONGODB_URI", "-e",
                   "MONGODB_DATABASE=" + database, "-e", "USE_MONGO=" + str(int(online)),
                   "--mount", f"type=bind,source={tmp_path},target=/app/app_data/database",
                   "quantifresh"]
        result = subprocess.run(command, input="\n".join(answers) + "\n", env=environment,
                                capture_output=True, text=True, timeout=90)
        assert result.returncode == 0, result.stdout + result.stderr
        return result.stdout

    try:
        expiry = (date.today() + timedelta(days=7)).isoformat()
        changed_expiry = (date.today() + timedelta(days=8)).isoformat()
        output = run(["create", "Zi save verification", "yes", "Zi", "22", "male", "", "1",
                      "yes", "milk", "2 l", expiry, "", "3", "6", "3"], True)
        assert "Household saved to MongoDB." in output
        assert "No changes to save." in output
        snapshot_path = tmp_path / "households/current.json"
        pending_path = tmp_path / "pending_households/current.json"
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        collection = client[database]["households"]
        assert collection.count_documents({}) == 1
        assert collection.find_one({"_id": snapshot["_id"]})["fridge"][0]["Expiry_Date"] == expiry
        assert not pending_path.exists()

        output = run(["continue", "2", "1", "1", changed_expiry, "3", "3"], False)
        assert "Pending draft: /app/app_data/database/pending_households/current.json" in output
        pending = json.loads(pending_path.read_text(encoding="utf-8"))
        assert pending["fridge"][0]["Expiry_Date"] == changed_expiry
        assert json.loads(snapshot_path.read_text(encoding="utf-8")) == snapshot
        assert collection.find_one({"_id": snapshot["_id"]})["fridge"][0]["Expiry_Date"] == expiry

        output = run(["continue", "6", "3"], True)
        assert "Household saved to MongoDB." in output
        assert not pending_path.exists()
        saved = collection.find_one({"_id": snapshot["_id"]})
        assert saved["fridge"][0]["Expiry_Date"] == changed_expiry
        assert saved["version"] == snapshot["version"] + 1
    finally:
        client[database].drop_collection("households")
        client.close()
