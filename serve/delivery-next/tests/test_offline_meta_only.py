import json
import shutil
import subprocess
from pathlib import Path

import pytest

from owlbear_delivery_next.commands import cli
from owlbear_delivery_next.machine_host import selfcheck
from owlbear_delivery_next.settings.config import CONFIG_FORMAT
from owlbear_delivery_next.state_store import offline_protocol, project_home, project_move, registry
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


@pytest.mark.usefixtures("current_binding", "boot")
@pytest.mark.parametrize(
    "backup",
    [b"{not json", b"\xff\xfe\x00", json.dumps({"format": CONFIG_FORMAT + 1}).encode()],
    ids=["malformed", "not-utf8", "newer"],
)
def test_the_selfcheck_ignores_the_backup_config_of_a_validated_move(repo, boot, backup) -> None:
    target = move_to_next_boot(repo, boot)
    (source(repo) / "config.json").write_bytes(backup)  # the retained copy; the target's config is what counts

    assert selfcheck._project(registry.clone_id(source(repo)), repo) == []  # noqa: SLF001
    assert (source(repo) / "config.json").read_bytes() == backup
    assert json.loads((target / "config.json").read_text()) == {"format": 1, "widths": [1600]}


@pytest.mark.usefixtures("current_binding", "boot")
def test_the_selfcheck_still_refuses_a_bad_clone_config_before_the_move_finishes(repo) -> None:
    assert cli.main(["--repo", str(repo), "prepare"]) == 0
    (source(repo) / "config.json").write_bytes(b"{not json")

    found = selfcheck._project(registry.clone_id(source(repo)), repo)  # noqa: SLF001
    assert any(str(source(repo) / "config.json") in line for line in found)


@pytest.mark.usefixtures("current_binding", "boot")
@pytest.mark.parametrize(
    "active",
    [b"{not json", json.dumps({"format": CONFIG_FORMAT + 1}).encode()],
    ids=["malformed", "newer"],
)
def test_the_selfcheck_still_refuses_a_bad_active_target_config(repo, boot, active) -> None:
    target = move_to_next_boot(repo, boot)
    (target / "config.json").write_bytes(active)

    found = selfcheck._project(registry.clone_id(source(repo)), repo)  # noqa: SLF001
    assert any(str(target / "config.json") in line for line in found)


@pytest.mark.usefixtures("current_binding", "boot")
def test_the_selfcheck_still_refuses_a_corrupted_source_fence(repo, boot) -> None:
    move_to_next_boot(repo, boot)
    (source(repo) / MARKER).write_text("998")

    found = selfcheck._project(registry.clone_id(source(repo)), repo)  # noqa: SLF001
    assert any("SWITCHED receipt needs" in line for line in found)


@pytest.mark.usefixtures("current_binding", "boot")
def test_the_selfcheck_still_refuses_a_corrupted_source_receipt(repo, boot) -> None:
    move_to_next_boot(repo, boot)
    (source(repo) / project_move.MOVE_RECORD).write_text("{not json")

    assert selfcheck._project(registry.clone_id(source(repo)), repo) != []  # noqa: SLF001


@pytest.mark.usefixtures("current_binding", "boot")
def test_a_corrupted_source_receipt_does_not_hide_a_bad_backup_config(repo, boot) -> None:
    move_to_next_boot(repo, boot)
    (source(repo) / project_move.MOVE_RECORD).write_text("{not json")
    (source(repo) / "config.json").write_bytes(b"{not json")

    found = selfcheck._project(registry.clone_id(source(repo)), repo)  # noqa: SLF001
    assert any(str(source(repo) / "config.json") in line for line in found)
