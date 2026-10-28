"""``owlbear data --move``: the checkout moves with all it holds, or nothing changes (owlbear-data#15)."""

import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from owlbear_delivery_next.commands import cli
from owlbear_delivery_next.local_system import data_place, data_repo, local_home
from owlbear_delivery_next.local_system.storage_io import open_lock
from owlbear_delivery_next.machine_host import data_move


def git(cwd: Path, *args: str) -> str:
    who = ["-c", "user.name=t", "-c", "user.email=t@example.com"]
    return subprocess.run(["git", *who, *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()  # noqa: S603, S607


@pytest.fixture
def source(tmp_path: Path, monkeypatch) -> Path:
    """The owner's checkout outside OwlBear's folder, holding something of every kind only it has."""
    remote, root = tmp_path / "remote.git", tmp_path / "Projects" / "owlbear-data"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(remote))
    git(tmp_path, "clone", "-q", str(remote), str(root))
    (root / "config.json").write_text("{}\n")
    git(root, "add", "config.json")
    git(root, "commit", "-qm", "start")
    git(root, "push", "-q", "origin", "HEAD")
    git(root, "switch", "-qc", "side")
    git(root, "commit", "-q", "--allow-empty", "-m", "unpushed")
    git(root, "switch", "-q", "main")
    (root / "config.json").write_text('{"a": 1}\n')
    git(root, "stash", "-q")
    (root / "memory").mkdir()
    (root / "memory" / "note.md").write_text("kept\n")
    (root / "config.json").write_text('{"b": 2}\n')
    git(root, "worktree", "add", "-q", str(tmp_path / "linked"), "side")
    local_home.root().mkdir(parents=True, exist_ok=True)
    data_place.pointer().write_text(json.dumps({"repository": str(root)}))
    monkeypatch.setattr(data_move, "_processes", list)  # this machine's own OwlBear runs beside the tests
    return root


def record() -> dict[str, str]:
    return json.loads(data_place.pointer().read_text())


def state(root: Path) -> tuple[str, ...]:
    return (
        git(root, "status", "--porcelain=v1", "-uall"),
        git(root, "for-each-ref", "--format=%(refname) %(objectname)", "refs/heads"),
        git(root, "stash", "list", "--format=%H"),
        (root / "memory" / "note.md").read_text(),
    )


def test_the_move_keeps_all_the_checkout_holds_and_its_linked_worktree(tmp_path: Path, source: Path) -> None:
    before, said = state(source), []
    remote = git(source, "config", "--get", "remote.origin.url")
    assert data_move.main(["--move"], said.append) == 0
    dest = data_place.default()
    assert (state(dest), source.exists()) == (before, False)
    assert record() == {"repository": str(dest), "remote": remote, "moved_from": str(source)}
    common = git(tmp_path / "linked", "rev-parse", "--path-format=absolute", "--git-common-dir")
    assert Path(common) == (dest / ".git").resolve()
    assert git(tmp_path / "linked", "status", "--porcelain") == ""
    assert said[-1] == f"moved: the shared repository is now {dest}; nothing is left at {source}"
    assert data_place.describe().line == f"shared data: {dest.resolve()} (default)"


def _held_host(_tmp: Path, _monkeypatch) -> int:
    fd = os.open(local_home.root(), os.O_RDONLY | os.O_DIRECTORY)
    try:
        return open_lock(fd, blocking=False, name="host.lock")
    finally:
        os.close(fd)


def _live_process(_tmp: Path, monkeypatch) -> None:
    monkeypatch.setattr(data_move, "_processes", lambda: ["process 7: python -m owlbear_delivery_next mcp"])


def _projects(monkeypatch, current) -> None:
    project = SimpleNamespace(path="/work/shop")
    monkeypatch.setattr(data_move.registry, "load", lambda: SimpleNamespace(projects=[project]))
    monkeypatch.setattr(data_move.project_home, "current", current)


def _unreadable_store(_tmp: Path, monkeypatch) -> None:
    def current(_repo: Path) -> Path:
        msg = "denied"
        raise OSError(msg)

    _projects(monkeypatch, current)


def _retained_runner(tmp: Path, monkeypatch) -> None:
    store = tmp / "store"
    (store / "changes" / "fix-x").mkdir(parents=True)
    (store / "changes" / "fix-x" / "runner.json").write_text('{"pid": 999999}')  # its runner long dead
    _projects(monkeypatch, lambda _repo: store)


def _unlistable_changes(tmp: Path, monkeypatch) -> None:
    changes, real = tmp / "store" / "changes", Path.iterdir
    changes.mkdir(parents=True)

    def iterdir(self: Path):
        if self == changes:
            msg = "denied"
            raise PermissionError(msg)
        return real(self)

    monkeypatch.setattr(Path, "iterdir", iterdir)
    _projects(monkeypatch, lambda _repo: tmp / "store")


def _dest_exists(_tmp: Path, _monkeypatch) -> None:
    (data_place.default() / "mine").mkdir(parents=True)


def _other_disk(_tmp: Path, monkeypatch) -> None:
    real, parent = Path.stat, data_place.default().parent

    def stat(self: Path, **kwargs: bool) -> os.stat_result:
        found = real(self, **kwargs)
        if self == parent:
            return os.stat_result((found[0], found[1], found.st_dev + 1, *found[3:10]))
        return found

    monkeypatch.setattr(Path, "stat", stat)


def _linked_source(tmp: Path, _monkeypatch) -> None:
    data_place.pointer().write_text(json.dumps({"repository": str(tmp / "linked")}))


@pytest.mark.parametrize(
    ("arrange", "reason"),
    [
        (_held_host, "OwlBear is running"),
        (_live_process, "process 7: python -m owlbear_delivery_next mcp"),
        (_unreadable_store, "/work/shop: its store cannot be read: denied"),
        (_retained_runner, "a runner's record; start OwlBear, let it settle the step"),
        (_unlistable_changes, "/work/shop: its store cannot be read: denied"),
        (_dest_exists, "exists; choose a new folder"),
        (_other_disk, "is on another disk"),
        (_linked_source, "is a linked worktree; move its main checkout"),
    ],
    ids=["host", "process", "store", "runner", "changes", "dest", "disk", "linked"],
)
def test_a_refused_move_changes_nothing(tmp_path: Path, source: Path, monkeypatch, arrange, reason: str) -> None:
    held = arrange(tmp_path, monkeypatch)
    pointer, before, said = record(), state(source), []
    try:
        assert data_move.main(["--move"], said.append) == 1
    finally:
        if isinstance(held, int):
            os.close(held)
    assert any(reason in line for line in said), said
    assert (record(), state(source)) == (pointer, before)
    assert sorted(p.name for p in data_place.default().glob("*")) == (["mine"] if arrange is _dest_exists else [])


def test_a_writer_found_after_the_pointer_names_the_move_refuses_it_and_readers_meanwhile_resolve_nothing(
    source: Path, monkeypatch
) -> None:
    seen = []

    def writers() -> list[str]:
        with pytest.raises(data_repo.DataRepoError, match="is not finished") as exc:
            data_repo.locate()
        seen.append(str(exc.value))
        return ["process 8: owlbear-next data"]

    monkeypatch.setattr(data_move, "writers", writers)
    pointer, said = record(), []
    assert data_move.main(["--move"], said.append) == 1
    assert (len(seen), record(), source.is_dir(), data_place.default().exists()) == (1, pointer, True, False)


@pytest.mark.usefixtures("source")
def test_a_failed_repair_keeps_readers_out_until_owlbear_data_finishes_the_move(tmp_path: Path, monkeypatch) -> None:
    real = data_place.relink
    monkeypatch.setattr(data_place, "relink", lambda _root: "`git worktree repair` failed: injected")
    said = []
    assert data_move.main(["--move"], said.append) == 1
    assert "then run `owlbear data` to finish" in said[-1]
    assert set(record()) == {"remote", "moving_from", "moving_to"}
    with pytest.raises(data_repo.DataRepoError, match="is not finished"):
        data_repo.locate()
    monkeypatch.setattr(data_place, "relink", real)
    assert cli.main(["data"]) == 0
    assert record()["repository"] == str(data_place.default())
    common = git(tmp_path / "linked", "rev-parse", "--path-format=absolute", "--git-common-dir")
    assert Path(common) == (data_place.default() / ".git").resolve()


def test_a_running_owlbear_process_is_found_and_this_one_is_not() -> None:
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)", "owlbear_delivery_next"])
    try:
        found = data_move._processes()  # noqa: SLF001
    finally:
        child.kill()
        child.wait()
    assert any(line.startswith(f"process {child.pid}: ") for line in found)
    assert not any(line.startswith(f"process {os.getpid()}: ") for line in found)
