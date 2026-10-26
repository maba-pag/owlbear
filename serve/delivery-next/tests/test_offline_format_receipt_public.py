"""Format markers and move records are validated before any public offline write.

Every case drives the real ``cli.main`` prepare/finish flow with the same unpatched verifier as the public CLI tests;
only the boot-session reader is replaced. Refusals must leave the source, its preparation and its move record
unchanged, and the supported formats 1 through 7 must still move and open.
"""

import json
import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

from owlbear_delivery_next.commands import cli
from owlbear_delivery_next.machine_host import registry, selfcheck
from owlbear_delivery_next.state_store import offline_protocol, project_home, project_move
from owlbear_delivery_next.state_store.database import MARKER, StoreError
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


def _source(repo: Path) -> Path:
    return project_home.clone_dir(repo)


def _snapshot(folder: Path) -> dict[str, bytes | str]:
    state: dict[str, bytes | str] = {}
    for entry in sorted(folder.rglob("*")):
        rel = str(entry.relative_to(folder))
        if rel == project_move.MOVE_LOCK:  # startup creates the move lock on purpose; it holds no state
            continue
        mode = os.lstat(entry).st_mode
        if stat.S_ISREG(mode):
            state[rel] = entry.read_bytes()
        else:
            state[rel] = "dir" if stat.S_ISDIR(mode) else "other"
    return state


def _prepare_and_finish(repo: Path, boot: dict, marker: str) -> Path:
    """Set the clone's own format, prepare, model a reboot, finish; returns the active store's root."""
    (_source(repo) / MARKER).write_text(marker)
    assert cli.main(["--repo", str(repo), "prepare"]) == 0
    boot["id"] = AFTER
    assert cli.main(["--repo", str(repo), "finish"]) == 0
    return Store.open(repo).root


@pytest.mark.usefixtures("current_binding", "boot")
@pytest.mark.parametrize("marker", ["8", "998", "1000", "0", "x9"])
def test_prepare_refuses_an_unsupported_prior_format_before_any_write(repo, marker, capsys) -> None:
    (_source(repo) / MARKER).write_text(marker)
    before = _snapshot(_source(repo))

    assert cli.main(["--repo", str(repo), "prepare"]) == 1

    assert "not a supported store format" in capsys.readouterr().err
    assert _snapshot(_source(repo)) == before, "a refused prepare wrote to the source"


@pytest.mark.usefixtures("current_binding")
@pytest.mark.parametrize("marker", ["1", "6", "7"])
def test_a_supported_legacy_format_moves_and_every_public_consumer_accepts_it(repo, boot, marker) -> None:
    target = _prepare_and_finish(repo, boot, marker)
    pid = registry.clone_id(_source(repo))
    assert pid is not None

    assert (target / MARKER).read_text().strip() == marker, "the move changed the format the store was written in"
    assert registry.register(repo).id == pid
    assert selfcheck._project(pid, repo) == []  # noqa: SLF001
    assert registry.adopt(pid).id == pid
    assert Store.open(repo).root == target


@pytest.mark.usefixtures("current_binding")
@pytest.mark.parametrize("stored", ["8", "998", "1000"])
def test_finish_refuses_a_tampered_prior_format_and_writes_nothing(repo, boot, stored, capsys) -> None:
    assert cli.main(["--repo", str(repo), "prepare"]) == 0
    record_path = _source(repo) / offline_protocol.PREPARED
    record = json.loads(record_path.read_text()) | {"marker": stored + "\n"}
    record_path.write_text(json.dumps(record) + "\n")
    boot["id"] = AFTER
    before = _snapshot(_source(repo))

    assert cli.main(["--repo", str(repo), "finish"]) == 1

    assert "not a supported store format" in capsys.readouterr().err
    assert _snapshot(_source(repo)) == before, "a refused finish changed the source or its preparation"


@pytest.mark.usefixtures("current_binding")
@pytest.mark.parametrize("record", ["null", "false", "0", "[]"])
def test_a_non_object_move_record_is_refused_by_finish_before_any_write(repo, boot, record) -> None:
    assert cli.main(["--repo", str(repo), "prepare"]) == 0
    boot["id"] = AFTER
    (_source(repo) / project_move.MOVE_RECORD).write_text(record)
    before = _snapshot(_source(repo))

    assert cli.main(["--repo", str(repo), "finish"]) == 1

    assert _snapshot(_source(repo)) == before, "finish rewrote a non-object move record"


@pytest.mark.usefixtures("current_binding")
def test_a_null_move_record_with_a_missing_target_is_refused_and_no_authority_is_rebuilt(repo, boot) -> None:
    target = _prepare_and_finish(repo, boot, "7")
    shutil.rmtree(target)
    (_source(repo) / project_move.MOVE_RECORD).write_text("null")
    before = _snapshot(_source(repo))

    with pytest.raises(StoreError, match="move record"):
        Store.open(repo)

    assert _snapshot(_source(repo)) == before, "a refused open rewrote the source"
    assert not target.exists(), "a refused open rebuilt the target from the source"
    assert (_source(repo) / MARKER).read_text() == f"{project_move.FENCE}\n"


@pytest.mark.usefixtures("current_binding")
def test_a_legitimately_absent_move_record_still_starts_a_new_move(repo, boot) -> None:
    assert cli.main(["--repo", str(repo), "prepare"]) == 0
    boot["id"] = AFTER
    assert not (_source(repo) / project_move.MOVE_RECORD).exists()

    assert cli.main(["--repo", str(repo), "finish"]) == 0
    assert Store.open(repo).root.is_dir()


@pytest.mark.usefixtures("current_binding")
def test_a_future_format_target_is_refused_by_every_public_consumer_and_nothing_changes(repo, boot) -> None:
    target = _prepare_and_finish(repo, boot, "7")
    pid = registry.clone_id(_source(repo))
    assert pid is not None
    registry.register(repo)
    (target / MARKER).write_text("8\n")
    source_before, target_before = _snapshot(_source(repo)), _snapshot(target)

    with pytest.raises(registry.RegistryError):
        registry.adopt(pid)
    assert selfcheck._project(pid, repo) != []  # noqa: SLF001
    with pytest.raises(StoreError):
        Store.open(repo)

    assert _snapshot(_source(repo)) == source_before, "a consumer changed the retained source"
    assert _snapshot(target) == target_before, "a consumer changed the future-format target"
