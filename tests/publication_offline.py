"""Native Prepare/Finish inputs shared by publication and marker admission tests."""

import json
import subprocess
from pathlib import Path

from owlbear_delivery_next.commands import cli
from owlbear_delivery_next.state_store import offline_protocol, project_home, project_move
from owlbear_delivery_next.state_store.database import MARKER
from owlbear_delivery_next.state_store.store import Store

BEFORE = "AAAAAAAA-0000-4000-8000-000000000001"
AFTER = "BBBBBBBB-0000-4000-8000-000000000002"
PAYLOAD_FILE = Path("changes/c1/notes.txt")


def repo(tmp_path: Path) -> Path:
    path = tmp_path / "shop"
    subprocess.run(["git", "init", "-q", "-b", "main", str(path)], check=True, capture_output=True)  # noqa: S603, S607
    folder = project_home.clone_dir(path)
    folder.mkdir(parents=True)
    (folder / MARKER).write_text("7")
    (folder / "config.json").write_text(json.dumps({"format": 1, "widths": [1600]}))
    (folder / PAYLOAD_FILE.parent).mkdir(parents=True)
    (folder / PAYLOAD_FILE).write_text("regular payload\n")
    return path


def boot(monkeypatch) -> dict:
    state = {"id": BEFORE}
    monkeypatch.setattr(offline_protocol, "boot_session", lambda: state["id"])
    return state


def source(repo: Path) -> Path:
    return project_home.clone_dir(repo)


def record(repo: Path) -> dict:
    return json.loads((source(repo) / project_move.MOVE_RECORD).read_text())


def prepare(repo: Path, boot: dict) -> None:
    assert cli.main(["--repo", str(repo), "prepare"]) == 0
    boot["id"] = AFTER


def switched_store(repo: Path, boot: dict, capsys) -> Path:
    prepare(repo, boot)
    assert cli.main(["--repo", str(repo), "finish"]) == 0
    capsys.readouterr()
    return Store.open(repo).root
