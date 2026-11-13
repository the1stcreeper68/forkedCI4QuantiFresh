# [STATUS] NEW ADDED
#__ Capture actual Docker CLI output using temporary local fixtures and no cloud connection.
from copy import deepcopy
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from modules.repositories.JsonRepository import JsonRepository
from new_test.test_document import populated_document


# [STATUS] NEW ADDED
#__ Each scenario gets an isolated mount; the real app folder and Atlas are never used.
def capture(case, answers):
    with TemporaryDirectory(prefix="qf-recovery-") as folder:
        local = JsonRepository(folder)
        document = populated_document()
        document["name"] = "Zi Demo Household"
        pending = None
        if case == "Save pending and exit":
            pending = deepcopy(document)
            pending["name"] = "Zi Offline Edit"
        local.write(document, pending, False, None)
        local.remember(document)
        if case == "Deleted snapshot":
            local.paths["snapshot"].unlink()
        result = subprocess.run(
            ["docker", "run", "--rm", "-i", "-e", "USE_MONGO=0", "--mount",
             f"type=bind,source={folder},target=/app/app_data/database", "quantifresh"],
            input="\n".join(answers) + "\n", text=True, capture_output=True, timeout=30)
        assert result.returncode == 0, result.stderr
        bundle = local.read()
        if case == "Deleted snapshot":
            assert bundle["snapshot"] is None and bundle["state"] is None
        elif case == "Forget and return to access":
            assert bundle["snapshot"] == document and local.read_settings() is None
        else:
            assert bundle["pending"] == pending
        return f"## {case}\n\nInputs: `{', '.join(answers)}`\n\n```text\n{result.stdout.strip()}\n```\n"


# [STATUS] NEW ADDED
#__ Store reproducible output with its offline scope and test results explicitly identified.
if __name__ == "__main__":
    report = "# Startup, forget and save/exit — actual Docker output\n\nCaptured 2026-11-13 from the rebuilt `quantifresh` image. Temporary fixture households only; `USE_MONGO=0`. These are real CLI outputs, not proof of Atlas sync. No real local files or cloud records were modified or deleted. Online forgetting and conflict behavior are covered by isolated regression tests.\n\nValidation: `python -m pytest test_script.py new_test -q` — **161 passed, 7 skipped** (optional live integrations).\n\n"
    for case, answers in [
        ("Deleted snapshot", ["3"]),
        ("Forget and return to access", ["1", "5", "3"]),
        ("Save pending and exit", ["1", "6", "3"]),
    ]:
        report += capture(case, answers) + "\n"
    report += "## Documentation consulted\n\n- [Python filesystem replacement](https://docs.python.org/3/library/os.html#os.replace): existing journal/replacement mechanism retained for resetting active files.\n- [MongoDB single-document atomicity](https://www.mongodb.com/docs/manual/core/write-operations-atomicity/): existing household version checks retained; no cloud deletion added.\n"
    Path("new_test/STARTUP_RECOVERY_OUTPUTS.md").write_text(report, encoding="utf-8")
