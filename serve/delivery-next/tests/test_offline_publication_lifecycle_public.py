"""Publication and admission defects from review 6 on the d859 commit, through the public offline path.

Each case runs the real ``cli.main`` Prepare and Finish on a real git clone in a temporary directory. Test hooks only
inject the gap between two checks; the bytes, the phase and the refusal are asserted on the real filesystem.
"""

import errno
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from owlbear_delivery_next.commands import cli
from owlbear_delivery_next.machine_host import selfcheck
from owlbear_delivery_next.state_store import fd_tree, offline_protocol, project_home, project_move, registry
from owlbear_delivery_next.state_store.database import MARKER, FormatTooNewError, StoreError
from owlbear_delivery_next.state_store.store import Store

BEFORE = "AAAAAAAA-0000-4000-8000-000000000001"
AFTER = "BBBBBBBB-0000-4000-8000-000000000002"
PAYLOAD_FILE = Path("changes/c1/notes.txt")


@pytest.fixture
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


@pytest.fixture
def boot(monkeypatch) -> dict:
    state = {"id": BEFORE}
    monkeypatch.setattr(offline_protocol, "boot_session", lambda: state["id"])
    return state


def _source(repo: Path) -> Path:
    return project_home.clone_dir(repo)


def _record(repo: Path) -> dict:
    return json.loads((_source(repo) / project_move.MOVE_RECORD).read_text())


def _prepared(repo: Path, boot: dict) -> None:
    assert cli.main(["--repo", str(repo), "prepare"]) == 0
    boot["id"] = AFTER


def _switched_store(repo: Path, boot: dict, capsys) -> Path:
    _prepared(repo, boot)
    assert cli.main(["--repo", str(repo), "finish"]) == 0
    capsys.readouterr()
    target = Store.open(repo).root
    (target / MARKER).unlink()
    return target


def _finish_refused(repo: Path, capsys) -> bool:
    """Run Finish once; True when it refused (nonzero exit or StoreError), False when it switched."""
    try:
        code = cli.main(["--repo", str(repo), "finish"])
    except StoreError:
        code = None
    capsys.readouterr()
    return code in (None, 1)


@pytest.mark.usefixtures("current_binding")
def test_a_foreign_target_found_on_resume_is_refused_before_any_write(repo, boot, capsys, monkeypatch):
    _prepared(repo, boot)
    real_sync = project_move._sync_published  # noqa: SLF001 - the first attempt fails, the resume must not write
    calls: list[int] = []

    def fail_first_sync(pfd, target, tfd):
        calls.append(1)
        if len(calls) == 1:
            msg = "injected first-attempt sync failure"
            raise OSError(errno.EIO, msg)
        real_sync(pfd, target, tfd)

    monkeypatch.setattr(project_move, "_sync_published", fail_first_sync)
    with pytest.raises((OSError, StoreError)):
        cli.main(["--repo", str(repo), "finish"])
    capsys.readouterr()

    target = Path(_record(repo)["target"])
    assert target.exists(), "the first attempt should leave the published copy in place"
    shutil.rmtree(target)
    target.mkdir()
    (target / "foreign.txt").write_text("owner bytes\n")

    assert _finish_refused(repo, capsys), "a foreign target was resumed into"
    assert not (target / MARKER).exists(), "a format marker was written into the foreign target"
    assert sorted(p.name for p in target.iterdir()) == ["foreign.txt"]
    assert (target / "foreign.txt").read_text() == "owner bytes\n"
    assert _record(repo)["phase"] != project_move.SWITCHED


@pytest.mark.usefixtures("current_binding")
@pytest.mark.parametrize("tamper", ["delete", "8"])
def test_a_target_marker_changed_by_the_sync_is_refused_before_switch(repo, boot, capsys, monkeypatch, tamper):
    _prepared(repo, boot)
    real_sync = project_move._sync_published  # noqa: SLF001 - the owner changes the marker during the sync

    def sync_then_tamper(pfd, target, tfd):
        real_sync(pfd, target, tfd)
        marker = target / MARKER
        if tamper == "delete":
            marker.unlink()
        else:
            marker.write_text(tamper)

    monkeypatch.setattr(project_move, "_sync_published", sync_then_tamper)

    assert _finish_refused(repo, capsys), "a marker changed during the sync was switched"
    target = Path(_record(repo)["target"])
    if tamper == "delete":
        assert not (target / MARKER).exists(), "the owner's deletion was silently repaired"
    else:
        assert (target / MARKER).read_text() == tamper, "the owner's marker was overwritten"
    assert _record(repo)["phase"] != project_move.SWITCHED
    assert (_source(repo) / PAYLOAD_FILE).read_text() == "regular payload\n"


def _rewrite_prior(repo: Path, prior: str) -> None:
    path = _source(repo) / project_move.PREPARED
    record = json.loads(path.read_text())
    record["marker"] = prior
    path.write_text(json.dumps(record) + "\n")


def _consumers_refuse(repo: Path, target: Path) -> None:
    with pytest.raises(registry.RegistryError):
        registry.canonical(repo)
    with pytest.raises(StoreError):
        Store.open(repo)
    assert not (target / MARKER).exists(), "a marker was minted for an unproved store"
    clone = _source(repo)
    registry_pid = project_home.clone_id(clone)
    assert registry_pid is not None
    _, problem = selfcheck._receipt(registry_pid, clone)  # noqa: SLF001 - the selfcheck's own receipt verdict
    assert problem is not None, "selfcheck reported the receipt as sound"


@pytest.mark.usefixtures("current_binding")
def test_a_missing_target_marker_with_a_prepared_prior_8_is_refused_by_every_consumer(repo, boot, capsys):
    target = _switched_store(repo, boot, capsys)
    _rewrite_prior(repo, "8")
    _consumers_refuse(repo, target)


@pytest.mark.usefixtures("current_binding")
def test_a_missing_preparation_is_refused_by_every_consumer(repo, boot, capsys):
    target = _switched_store(repo, boot, capsys)
    prepared = _source(repo) / project_move.PREPARED
    assert prepared.exists(), "the preparation record should be present before the control removes it"
    prepared.unlink()
    _consumers_refuse(repo, target)


@pytest.mark.usefixtures("current_binding")
def test_a_prepared_prior_6_is_admitted_by_every_consumer(repo, boot, capsys):
    (_source(repo) / MARKER).write_text("6")
    target = _switched_store(repo, boot, capsys)
    _rewrite_prior(repo, "6")
    assert Store.open(repo).root == target
    assert (target / MARKER).read_text().strip() == "6"
    registry.canonical(repo)
    clone = _source(repo)
    _, problem = selfcheck._receipt(project_home.clone_id(clone), clone)  # noqa: SLF001
    assert problem is None


@pytest.mark.usefixtures("current_binding")
def test_a_target_marker_from_a_newer_store_is_refused_as_an_upgrade_and_nothing_is_written(
    repo, boot, capsys, monkeypatch
):
    _prepared(repo, boot)
    real_sync, planted = fd_tree.sync, []

    def sync(dfd, entry):
        real_sync(dfd, entry)
        if entry == project_home.clone_id(_source(repo)) and not planted:  # the copy is published with a newer marker
            planted.append(entry)
            (project_home.home(entry) / MARKER).write_text("99\n")

    monkeypatch.setattr(fd_tree, "sync", sync)
    before = {name: (_source(repo) / name).read_bytes() for name in (MARKER, project_move.PREPARED)}
    boot["id"] = AFTER
    with pytest.raises(FormatTooNewError):
        offline_protocol.finish_clone(repo, gaps=lambda: ())
    capsys.readouterr()
    assert planted, "the newer marker was never planted"
    assert project_home.home(planted[0]).joinpath(MARKER).read_text() == "99\n"
    assert {name: (_source(repo) / name).read_bytes() for name in before} == before
    with pytest.raises(FormatTooNewError):
        Store.open(repo)
