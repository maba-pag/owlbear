import json
import shutil
import subprocess
from pathlib import Path

import pytest

from owlbear_delivery_next.commands import cli
from owlbear_delivery_next.machine_host import registry, selfcheck
from owlbear_delivery_next.state_store import offline_protocol, project_home
from owlbear_delivery_next.state_store.database import MARKER, STORE_FORMAT
from owlbear_delivery_next.state_store.store import Store

BEFORE = "AAAAAAAA-0000-4000-8000-000000000001"
AFTER = "BBBBBBBB-0000-4000-8000-000000000002"


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    path = tmp_path / "shop"
    subprocess.run(["git", "init", "-q", "-b", "main", str(path)], check=True, capture_output=True)  # noqa: S603, S607
    folder = project_home.clone_dir(path)
    folder.mkdir(parents=True)
    (folder / MARKER).write_text("7")
    (folder / "config.json").write_text(json.dumps({"format": 1, "widths": [1600]}))
    return path


@pytest.fixture
def boot(monkeypatch) -> dict:
    state = {"id": BEFORE}
    monkeypatch.setattr(offline_protocol, "boot_session", lambda: state["id"])
    return state


def source(repo: Path) -> Path:
    return project_home.clone_dir(repo)


def move_to_next_boot(repo: Path, boot: dict) -> Path:
    """Prepare, reboot, Finish; returns the target folder the switched receipt names."""
    assert cli.main(["--repo", str(repo), "prepare"]) == 0
    boot["id"] = AFTER
    assert cli.main(["--repo", str(repo), "finish"]) == 0
    return Store.open(repo).root


@pytest.mark.usefixtures("current_binding", "boot")
def test_prepare_refuses_a_meta_only_clone_before_fencing_or_writing(repo, capsys) -> None:
    (source(repo) / "config.json").unlink()  # the payload already moved: only the marker and clone identity remain

    assert cli.main(["--repo", str(repo), "prepare"]) == 1

    assert "no legacy store to move" in capsys.readouterr().err
    assert (source(repo) / MARKER).read_text() == "7"
    assert not (source(repo) / offline_protocol.PREPARED).exists()
    assert not (source(repo) / "clone-id").exists()


@pytest.mark.usefixtures("current_binding")
def test_a_finished_move_source_is_canonical_only_while_its_switched_receipt_holds(repo, boot, monkeypatch) -> None:
    target = move_to_next_boot(repo, boot)
    assert (source(repo) / MARKER).read_text().strip() == "999"

    real_git = registry._git  # noqa: SLF001
    monkeypatch.setattr(
        registry,
        "_git",
        lambda cwd, *args: repo if "--show-toplevel" in args else real_git(cwd, *args),
    )
    monkeypatch.setattr(registry, "_owned", lambda _path: None)
    work, store = registry.canonical(repo)
    assert (work, store) == (repo, source(repo))

    shutil.rmtree(target)
    with pytest.raises(registry.RegistryError):
        registry.canonical(repo)
    assert (source(repo) / MARKER).read_text().strip() == "999"


@pytest.mark.usefixtures("current_binding")
def test_the_selfcheck_passes_a_finished_move_and_refuses_a_future_target(repo, boot) -> None:
    target = move_to_next_boot(repo, boot)
    pid = registry.clone_id(source(repo))
    assert selfcheck._project(pid, repo) == []  # noqa: SLF001

    (target / MARKER).write_text(f"{STORE_FORMAT + 1}")
    assert selfcheck._project(pid, repo) != []  # noqa: SLF001
    assert (source(repo) / MARKER).read_text().strip() == "999"
    assert (target / MARKER).read_text() == f"{STORE_FORMAT + 1}"
