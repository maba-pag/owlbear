"""The shared data repository's place, ``~/.owlbear/data``: adopted, cloned, overridden, recovered."""

import json
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from owlbear_delivery_next.commands import cli
from owlbear_delivery_next.local_system import data_repo, local_home
from owlbear_delivery_next.local_system.storage_io import open_lock
from owlbear_delivery_next.machine_host import serve


def git(cwd: Path, *args: str) -> str:
    who = ["-c", "user.name=t", "-c", "user.email=t@example.com", "-c", "protocol.file.allow=always"]
    return subprocess.run(["git", *who, *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()  # noqa: S603, S607


def bare(tmp_path: Path, name: str) -> str:
    """A remote with one commit; its file:// address."""
    path, seed = tmp_path / f"{name}.git", tmp_path / f"{name}-seed"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(path))
    git(tmp_path, "clone", "-q", str(path), str(seed))
    (seed / "config.json").write_text("{}\n")
    git(seed, "add", "config.json")
    git(seed, "commit", "-qm", "start")
    git(seed, "push", "-q", "origin", "HEAD")
    return path.as_uri()


@pytest.fixture
def url(tmp_path: Path) -> str:
    return bare(tmp_path, "owlbear-data")


def home() -> Path:
    return local_home.root()


def record() -> dict[str, str] | None:
    path = data_repo.pointer()
    return json.loads(path.read_text()) if path.exists() else None


def clones() -> list[str]:
    return sorted(p.name for p in home().glob(".data-clone-*"))


def test_without_a_pointer_a_checkout_at_the_default_place_is_used_and_recorded_at_host_start(url: str) -> None:
    home().mkdir(parents=True, exist_ok=True)
    git(home(), "clone", "-q", url, "data")
    place = data_repo.default().resolve()
    assert data_repo.locate() == data_repo.DataRepo(place)
    assert record() is None  # reading never writes
    adopted = f"adopted {place}, a checkout of {data_repo.remote_identity(url)}"
    assert data_repo.provision(clone=False) == (data_repo.DataRepo(place), adopted)
    assert record() == {"repository": str(place), "remote": url}
    assert data_repo.describe().line == f"shared data: {place} (default)"


def test_a_default_place_that_is_no_checkout_is_refused_and_left_alone() -> None:
    (data_repo.default() / "notes").mkdir(parents=True)
    with pytest.raises(data_repo.DataRepoError, match="not a git repository's top folder"):
        data_repo.locate()
    with pytest.raises(data_repo.DataRepoError, match="move it away"):
        data_repo.provision(clone=False)
    assert (record(), sorted(p.name for p in data_repo.default().iterdir())) == (None, ["notes"])
    assert cli.main(["data"]) == 1


def test_data_url_clones_into_the_default_place_through_a_hidden_sibling(url: str, capsys) -> None:
    assert cli.main(["data", url]) == 0
    place = data_repo.default().resolve()
    assert f"Cloned {url} into {data_repo.default()}" in capsys.readouterr().out
    assert record() == {"repository": str(place), "remote": url}
    assert ((place / "config.json").read_text(), clones()) == ("{}\n", [])
    assert data_repo.locate() == data_repo.DataRepo(place)


def test_a_failed_clone_is_kept_in_the_pointer_and_said_everywhere(tmp_path: Path, capsys) -> None:
    gone = (tmp_path / "gone.git").as_uri()
    assert cli.main(["data", gone]) == 1
    assert "Not set: cloning" in capsys.readouterr().out
    kept = record()
    assert kept is not None
    assert (set(kept), kept["remote"], clones(), data_repo.default().exists()) == (
        {"remote", "failed"},
        gone,
        [],
        False,
    )
    with pytest.raises(data_repo.DataRepoError, match=f"{gone} is not cloned yet: "):
        data_repo.locate()
    assert data_repo.describe().kind == "problem"
    assert data_repo.provision(clone=False) == (None, f"the shared repository {gone} is not cloned yet")


@pytest.mark.parametrize("same", [True, False])
def test_a_finished_clone_at_the_default_place_is_adopted_only_for_the_same_repository(
    tmp_path: Path, url: str, monkeypatch, *, same: bool
) -> None:
    other = bare(tmp_path, "other")
    home().mkdir(parents=True, exist_ok=True)
    git(home(), "clone", "-q", url if same else other, "data")
    data_repo.pointer().write_text(json.dumps({"remote": url}))  # a clone that ended after its rename
    monkeypatch.setattr(data_repo, "_clone", lambda *_a, **_k: pytest.fail("no clone"))
    head = git(data_repo.default(), "rev-parse", "HEAD")
    if same:
        assert data_repo.provision()[0] == data_repo.DataRepo(data_repo.default().resolve())
        assert record() == {"repository": str(data_repo.default().resolve()), "remote": url}
    else:
        with pytest.raises(data_repo.DataRepoError, match="nothing was changed"):
            data_repo.provision()
        assert record() == {"remote": url}
    assert git(data_repo.default(), "rev-parse", "HEAD") == head


@pytest.mark.parametrize("same", [True, False])
def test_data_url_adopts_the_checkout_already_in_use_and_refuses_another_repository(
    tmp_path: Path, url: str, *, same: bool
) -> None:
    mine = tmp_path / "Projects" / "owlbear-data"
    git(tmp_path, "clone", "-q", url, str(mine))
    assert data_repo.point(mine) == data_repo.DataRepo(mine.resolve())
    before = record()
    asked = url if same else bare(tmp_path, "other")
    code, said = cli.show_data(asked)
    assert code == (0 if same else 1)
    assert ("Already uses" if same else "nothing was changed") in said
    assert (record(), data_repo.default().exists()) == (before, False)


def test_a_path_in_or_around_owlbears_folder_is_refused_except_its_data_place(tmp_path: Path, url: str) -> None:
    for inside in ("versions/v1.70/data", "runtime/data", "projects/x"):
        git(tmp_path, "clone", "-q", url, str(home() / inside))
        with pytest.raises(data_repo.DataRepoError, match="updates and uninstalling clear"):
            data_repo.point(home() / inside)
    for around in (home(), home().parent):
        with pytest.raises(data_repo.DataRepoError, match="in or around OwlBear's folder"):
            data_repo.point(around)
    git(tmp_path, "clone", "-q", url, str(data_repo.default()))
    assert data_repo.point(data_repo.default()).root == data_repo.default().resolve()


def test_a_pointer_written_while_cloning_wins_and_the_clone_is_dropped(url: str, monkeypatch) -> None:
    real = subprocess.run

    def run(*args, **kwargs):
        done = real(*args, **kwargs)
        data_repo.pointer().write_text(json.dumps({"repository": "/elsewhere"}))  # another writer meanwhile
        return done

    fake = SimpleNamespace(run=run, DEVNULL=subprocess.DEVNULL, TimeoutExpired=subprocess.TimeoutExpired)
    monkeypatch.setattr(data_repo, "subprocess", fake)
    with pytest.raises(data_repo.DataRepoError, match="changed while cloning"):
        data_repo.provision(url)
    assert (record(), clones(), data_repo.default().exists()) == ({"repository": "/elsewhere"}, [], False)


def test_the_inventory_names_all_that_only_this_checkout_holds(tmp_path: Path, url: str) -> None:
    root = tmp_path / "data"
    git(tmp_path, "clone", "-q", url, str(root))
    shared = data_repo.DataRepo(root)
    assert data_repo.inventory(shared) == []
    git(root, "switch", "-qc", "side")
    git(root, "commit", "-q", "--allow-empty", "-m", "unpushed")
    git(root, "switch", "-q", "main")
    (root / "config.json").write_text('{"a": 1}\n')
    git(root, "stash", "-q")
    (root / "memory" / "global").mkdir(parents=True)
    (root / "memory" / "global" / "note.md").write_text("kept\n")
    (root / "config.json").write_text('{"b": 2}\n')
    git(root, "worktree", "add", "-q", str(tmp_path / "linked"), "side")
    assert data_repo.inventory(shared) == [
        "2 file(s) not committed, 1 of them never added",
        "1 commit(s) on local branches that no remote has",
        "1 stash(es)",
        f"linked worktree: {(tmp_path / 'linked').resolve()}",
    ]


def test_a_held_pointer_lock_is_refused_at_once_and_nothing_changes(url: str) -> None:
    home().mkdir(parents=True, exist_ok=True)
    data_repo.pointer().write_text(json.dumps({"remote": url}))
    fd = os.open(home(), os.O_RDONLY | os.O_DIRECTORY)
    lock = open_lock(fd, blocking=False, name=local_home.DATA_LOCK)
    os.close(fd)
    try:
        with pytest.raises(data_repo.BusyError, match="try again"):
            data_repo.provision(url)
        assert cli.main(["data", url]) == 1
    finally:
        os.close(lock)
    assert (record(), data_repo.default().exists()) == ({"remote": url}, False)


@pytest.mark.parametrize("left", ["source", "destination", "both", "neither"])
def test_an_unfinished_move_is_finished_undone_or_refused(tmp_path: Path, url: str, left: str) -> None:
    source, dest = tmp_path / "old-data", data_repo.default()
    git(tmp_path, "clone", "-q", url, str(source))
    git(source, "worktree", "add", "-q", str(tmp_path / "linked"))
    home().mkdir(parents=True, exist_ok=True)
    transition = {"remote": url, "moving_from": str(source), "moving_to": str(dest)}
    data_repo.pointer().write_text(json.dumps(transition))
    with pytest.raises(data_repo.DataRepoError, match="is not finished; `owlbear data` finishes it"):
        data_repo.locate()
    if left in {"destination", "neither"}:
        source.rename(dest) if left == "destination" else None
        if left == "neither":
            subprocess.run(["rm", "-rf", str(source)], check=True)  # noqa: S603, S607
    if left == "both":
        git(tmp_path, "clone", "-q", url, str(dest))
    if left in {"both", "neither"}:
        assert cli.main(["data"]) == 1
        assert record() == transition
        return
    assert cli.main(["data"]) == 0
    if left == "source":
        assert record() == {"repository": str(source), "remote": url}
    else:
        assert record() == {"repository": str(dest), "remote": url, "moved_from": str(source)}
        assert git(tmp_path / "linked", "rev-parse", "--path-format=absolute", "--git-common-dir") == str(
            (dest / ".git").resolve()
        )


def test_an_old_checkout_back_after_a_move_is_warned_about(tmp_path: Path, url: str) -> None:
    old = tmp_path / "old-data"
    git(tmp_path, "clone", "-q", url, str(data_repo.default()))
    data_repo.pointer().write_text(
        json.dumps({"repository": str(data_repo.default()), "remote": url, "moved_from": str(old)})
    )
    assert data_repo.describe().warning == ""
    old.mkdir()
    assert data_repo.describe().warning == f"the old checkout {old} is back; OwlBear doesn't use it"
    assert "is back" in cli.show_data(None)[1]


def test_the_host_clones_a_remote_only_pointer_in_the_background_then_loads_the_projects(
    tmp_path: Path, url: str
) -> None:
    gone = (tmp_path / "late.git").as_uri()
    home().mkdir(parents=True, exist_ok=True)
    data_repo.pointer().write_text(json.dumps({"remote": gone}))
    said, done = [], []

    class Stopping:
        def is_set(self) -> bool:
            return False

        def wait(self, _seconds: float) -> bool:  # the retry pause: the remote appears meanwhile
            subprocess.run(["git", "clone", "-q", "--bare", url, str(tmp_path / "late.git")], check=True)  # noqa: S603, S607
            return False

    machine = SimpleNamespace(
        stopping=Stopping(), say=said.append, carry=lambda: done.append("carry"), retry=lambda: done.append("retry")
    )
    assert serve._provisioned(machine) is True  # noqa: SLF001
    assert said == [f"shared data: the shared repository {gone} is not cloned yet"]
    serve._cloning(machine)  # noqa: SLF001
    assert said[1].startswith(f"shared data: cloning {gone} failed")
    assert said[2:] == [f"shared data: cloned {gone} into {data_repo.default()}"]
    assert done == ["carry", "retry"]
    assert record() == {"repository": str(data_repo.default().resolve()), "remote": gone}
