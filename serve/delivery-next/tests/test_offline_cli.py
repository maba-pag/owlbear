import subprocess
from pathlib import Path

import pytest

from owlbear_delivery_next.commands import cli
from owlbear_delivery_next.machine_host import command
from owlbear_delivery_next.state_store import legacy_family, offline_protocol, project_home
from owlbear_delivery_next.state_store.database import MARKER
from owlbear_delivery_next.state_store.store import StoreError

BEFORE = "AAAAAAAA-0000-4000-8000-000000000001"
AFTER = "BBBBBBBB-0000-4000-8000-000000000002"


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    path = tmp_path / "shop"
    subprocess.run(["git", "init", "-q", "-b", "main", str(path)], check=True, capture_output=True)  # noqa: S603, S607
    return path


@pytest.fixture
def legacy_repo(repo: Path) -> Path:
    folder = project_home.clone_dir(repo)  # a legacy clone with its own store to move
    (folder / "changes" / "c1").mkdir(parents=True)
    (folder / "changes" / "c1" / "runner.log").write_text("ran\n")
    (folder / MARKER).write_text("7")
    return repo


@pytest.fixture
def boot(monkeypatch) -> dict:
    state = {"id": BEFORE}
    monkeypatch.setattr(offline_protocol, "boot_session", lambda: state["id"])
    return state


def run(repo: Path, command_name: str) -> int:
    return cli.main(["--repo", str(repo), command_name])


def test_owlbear_forwards_prepare_and_finish_to_the_project_cli() -> None:
    assert {"prepare", "finish"} <= set(command.PROJECT)


@pytest.mark.usefixtures("boot")
def test_prepare_refuses_while_the_real_legacy_producers_are_unfenced(
    repo, current_binding, monkeypatch, capsys
) -> None:
    unproven = legacy_family.Binding(None, current_binding.interpreter, current_binding.package)
    monkeypatch.setattr(legacy_family, "live_binding", lambda: unproven)
    assert run(repo, "prepare") == 1
    folder = project_home.clone_dir(repo)
    assert "legacy producers are not proven fenced" in capsys.readouterr().err
    assert not (folder / offline_protocol.PREPARED).exists()
    assert not (folder / MARKER).exists()  # no fence is installed while a producer is open


@pytest.mark.usefixtures("current_binding")
def test_prepare_refuses_when_the_boot_session_is_unreadable(repo, monkeypatch, capsys) -> None:
    def unreadable() -> str:
        msg = "boot-session UUID is missing or malformed: refusing the offline move"
        raise StoreError(msg)

    monkeypatch.setattr(offline_protocol, "boot_session", unreadable)
    assert run(repo, "prepare") == 1
    assert "refusing the offline move" in capsys.readouterr().err
    assert not (project_home.clone_dir(repo) / offline_protocol.PREPARED).exists()


@pytest.mark.usefixtures("boot")
def test_finish_refuses_without_a_preparation(repo, capsys) -> None:
    assert run(repo, "finish") == 1
    assert "nothing was prepared" in capsys.readouterr().err


@pytest.mark.usefixtures("current_binding")
def test_finish_refuses_on_the_same_boot_session(legacy_repo, monkeypatch, capsys) -> None:
    repo = legacy_repo
    boot = {"id": BEFORE}
    monkeypatch.setattr(offline_protocol, "boot_session", lambda: boot["id"])
    assert run(repo, "prepare") == 0
    assert run(repo, "finish") == 1
    assert "still the boot session" in capsys.readouterr().err
    assert (project_home.clone_dir(repo) / offline_protocol.PREPARED).exists()


@pytest.mark.usefixtures("boot", "current_binding")
def test_finish_refuses_when_the_boot_session_is_unreadable_after_the_reboot(legacy_repo, monkeypatch, capsys) -> None:
    repo = legacy_repo
    assert run(repo, "prepare") == 0

    def unreadable() -> str:
        msg = "boot-session UUID is unreadable (no sysctl): refusing the offline move"
        raise StoreError(msg)

    monkeypatch.setattr(offline_protocol, "boot_session", unreadable)
    assert run(repo, "finish") == 1
    assert "refusing the offline move" in capsys.readouterr().err


def test_finish_refuses_when_the_binding_is_no_longer_proven(
    legacy_repo, boot, monkeypatch, capsys, current_binding
) -> None:
    repo = legacy_repo
    assert run(repo, "prepare") == 0
    boot["id"] = AFTER
    unproven = legacy_family.Binding(None, current_binding.interpreter, current_binding.package)
    monkeypatch.setattr(legacy_family, "live_binding", lambda: unproven)
    assert run(repo, "finish") == 1
    err = capsys.readouterr().err
    assert "legacy producers are not proven fenced" in err
    assert "no owlbear launcher" in err
    assert (project_home.clone_dir(repo) / offline_protocol.PREPARED).exists()
