# [STATUS] NEW ADDED
#__ Optional real-container restart check mounts only pytest's temporary directory.
import os
import subprocess
import pytest


# [STATUS] NEW ADDED
#__ A saved household preference and its data survive replacement of the container.
@pytest.mark.skipif(os.getenv("HOUSEHOLD_TEST_DOCKER") != "1", reason="Opt in to the Docker persistence check.")
def test_remembered_household_survives_container_restart(tmp_path):
    command = ["docker", "run", "--rm", "-i", "-e", "USE_MONGO=0", "--mount",
               f"type=bind,source={tmp_path},target=/app/app_data/database", "smoke_test-test"]
    first = subprocess.run(command, input="create\nZi Restart Test\nyes\nZi\n22\nmale\n\n1\nno\n3\n",
                           capture_output=True, text=True, timeout=40)
    assert first.returncode == 0, first.stderr
    second = subprocess.run(command, input="continue\n3\n", capture_output=True, text=True, timeout=40)
    assert second.returncode == 0, second.stderr
    assert "Continue with Zi Restart Test" in second.stdout
    assert "Welcome back, Zi Restart Test!" in second.stdout
    assert "Please enter name:" not in second.stdout
