"""The shared data repository's place, ``~/.owlbear/data``: adopted, cloned, overridden, recovered."""

import json
import os
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from owlbear_delivery_next.commands import cli
from owlbear_delivery_next.local_system import codebase, data_place, data_repo, git_run, local_home, publication_hold
from owlbear_delivery_next.local_system.storage_io import open_lock
from owlbear_delivery_next.machine_host import app, project, serve
from owlbear_delivery_next.machine_host.machine import Machine
from owlbear_delivery_next.project_host.host import HostRecord
from owlbear_delivery_next.state_store import project_home, registry


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
    path = data_place.pointer()
    return json.loads(path.read_text()) if path.exists() else None


def clones() -> list[str]:
    return sorted(p.name for p in home().glob(".data-clone-*"))


def test_without_a_pointer_a_checkout_at_the_default_place_is_used_and_recorded_at_host_start(url: str) -> None:
    home().mkdir(parents=True, exist_ok=True)
    git(home(), "clone", "-q", url, "data")
    place = data_place.default().resolve()
    assert data_repo.locate() == data_repo.DataRepo(place)
    assert record() is None  # reading never writes
    adopted = f"adopted {place}, a checkout of {data_repo.remote_identity(url)}"
    assert data_place.provision(clone=False) == (data_repo.DataRepo(place), adopted)
    assert record() == {"repository": str(place), "remote": url}
    assert data_place.describe().line == f"shared data: {place} (default)"


def test_a_default_place_that_is_no_checkout_is_refused_and_left_alone() -> None:
    (data_place.default() / "notes").mkdir(parents=True)
    with pytest.raises(data_repo.DataRepoError, match="not a git repository's top folder"):
        data_repo.locate()
    with pytest.raises(data_repo.DataRepoError, match="move it away"):
        data_place.provision(clone=False)
    assert (record(), sorted(p.name for p in data_place.default().iterdir())) == (None, ["notes"])
    assert cli.main(["data"]) == 1


def test_data_url_clones_into_the_default_place_through_a_hidden_sibling(url: str, capsys) -> None:
    assert cli.main(["data", url]) == 0
    place = data_place.default().resolve()
    assert f"Cloned {url} into {data_place.default()}" in capsys.readouterr().out
    assert record() == {"repository": str(place), "remote": url}
    assert ((place / "config.json").read_text(), clones()) == ("{}\n", [])
    assert data_repo.locate() == data_repo.DataRepo(place)


def test_a_failed_clone_is_kept_in_the_pointer_and_said_everywhere(tmp_path: Path, capsys) -> None:
    gone = (tmp_path / "gone.git").as_uri()
    assert cli.main(["data", gone]) == 1
    assert "Not set: DataRepoError: cloning" in capsys.readouterr().out
    kept = record()
    assert kept is not None
    assert (set(kept), kept["remote"], clones(), data_place.default().exists()) == (
        {"remote", "failed"},
        gone,
        [],
        False,
    )
    with pytest.raises(data_repo.DataRepoError, match=f"{gone} is not cloned yet: "):
        data_repo.locate()
    assert data_place.describe().kind == "problem"
    assert data_place.provision(clone=False) == (None, f"the shared repository {gone} is not cloned yet")


@pytest.mark.parametrize("same", [True, False])
def test_a_finished_clone_at_the_default_place_is_adopted_only_for_the_same_repository(
    tmp_path: Path, url: str, monkeypatch, *, same: bool
) -> None:
    other = bare(tmp_path, "other")
    home().mkdir(parents=True, exist_ok=True)
    git(home(), "clone", "-q", url if same else other, "data")
    data_place.pointer().write_text(json.dumps({"remote": url}))  # a clone that ended after its rename
    monkeypatch.setattr(data_place, "_clone", lambda *_a, **_k: pytest.fail("no clone"))
    head = git(data_place.default(), "rev-parse", "HEAD")
    if same:
        assert data_place.provision()[0] == data_repo.DataRepo(data_place.default().resolve())
        assert record() == {"repository": str(data_place.default().resolve()), "remote": url}
    else:
        with pytest.raises(data_repo.DataRepoError, match="nothing was changed"):
            data_place.provision()
        assert record() == {"remote": url}
    assert git(data_place.default(), "rev-parse", "HEAD") == head


@pytest.mark.parametrize("same", [True, False])
def test_data_url_adopts_the_checkout_already_in_use_and_refuses_another_repository(
    tmp_path: Path, url: str, *, same: bool
) -> None:
    mine = tmp_path / "Projects" / "owlbear-data"
    git(tmp_path, "clone", "-q", url, str(mine))
    assert data_place.point(mine) == data_repo.DataRepo(mine.resolve())
    before = record()
    asked = url if same else bare(tmp_path, "other")
    code, said = cli.show_data(asked)
    assert code == (0 if same else 1)
    assert ("Already uses" if same else "nothing was changed") in said
    assert (record(), data_place.default().exists()) == (before, False)


def test_a_path_in_or_around_owlbears_folder_is_refused_except_its_data_place(tmp_path: Path, url: str) -> None:
    for inside in ("versions/v1.70/data", "runtime/data", "projects/x"):
        (home() / inside).mkdir(parents=True)  # refused as misplaced before any git look, so no clone is needed
        with pytest.raises(data_repo.DataRepoError, match="updates and uninstalling clear"):
            data_place.point(home() / inside)
    for around in (home(), home().parent):
        with pytest.raises(data_repo.DataRepoError, match="in or around OwlBear's folder"):
            data_place.point(around)
    git(tmp_path, "clone", "-q", url, str(data_place.default()))
    assert data_place.point(data_place.default()).root == data_place.default().resolve()


def test_a_pointer_written_while_cloning_wins_and_the_clone_is_dropped(url: str, monkeypatch) -> None:
    real = subprocess.run

    def run(*args, **kwargs):
        done = real(*args, **kwargs)
        data_place.pointer().write_text(json.dumps({"repository": "/elsewhere"}))  # another writer meanwhile
        return done

    fake = SimpleNamespace(run=run, DEVNULL=subprocess.DEVNULL, TimeoutExpired=subprocess.TimeoutExpired)
    monkeypatch.setattr(git_run, "subprocess", fake)
    with pytest.raises(data_repo.DataRepoError, match="changed while cloning"):
        data_place.provision(url)
    assert (record(), clones(), data_place.default().exists()) == ({"repository": "/elsewhere"}, [], False)


@pytest.mark.parametrize("site", ["parse", "write", "move", "common"])
def test_a_pointer_or_git_folder_that_cannot_be_read_or_written_says_the_whole_error(
    tmp_path: Path, monkeypatch, whole_error: str, site: str
) -> None:
    def refused(*_args: object, **_kwargs: object) -> None:
        raise OSError(whole_error)

    monkeypatch.setattr(data_place, "atomic_write", refused)
    path = data_place.pointer()
    path.parent.mkdir(parents=True, exist_ok=True)
    old = path.with_name(data_place.OLD_POINTER)
    done = subprocess.CompletedProcess(["git", "rev-parse"], 128, "", whole_error)
    monkeypatch.setattr(data_place, "_top", lambda root: root)
    monkeypatch.setattr(data_place, "_git", lambda *_args: done)
    if site == "parse":
        path.write_text("{")
    if site == "move":
        old.write_text("{}\n")
    act = {
        "parse": lambda: data_place._parse(path),  # noqa: SLF001 - the pointer's own read
        "write": lambda: data_place._write({}),  # noqa: SLF001 - the pointer's own write
        "move": lambda: data_place._move_old(path, held=True),  # noqa: SLF001 - the old pointer's move
        "common": lambda: data_place._common(tmp_path),  # noqa: SLF001 - the Git folder lookup alone
    }[site]
    with pytest.raises(data_repo.DataRepoError) as raised:
        act()
    said = {
        "parse": f"{path} names no repository: JSONDecodeError: {raised.value.__cause__}",
        "write": f"the pointer {path} could not be written: OSError: {whole_error}",
        "move": f"the pointer {old} could not be moved to {path}: OSError: {whole_error}",
        "common": (
            f"the Git folder of {tmp_path.resolve()} cannot be found: CalledProcessError: "
            f"Command '['git', 'rev-parse']' returned non-zero exit status 128.\n{whole_error}"
        ),
    }[site]
    assert str(raised.value) == said


@pytest.mark.parametrize("where", ["mkdtemp", "rename", "lock"])
def test_a_disk_failure_while_cloning_is_said_kept_and_retried(url: str, monkeypatch, where: str) -> None:
    home().mkdir(parents=True, exist_ok=True)
    data_place.pointer().write_text(json.dumps({"remote": url}))
    failed, said, seen, done = [], [], [], []

    def once(real):
        def call(*args, **kwargs):
            if not failed:
                failed.append(where)
                raise PermissionError(13, "denied")
            return real(*args, **kwargs)

        return call

    if where == "mkdtemp":
        monkeypatch.setattr(tempfile, "mkdtemp", once(tempfile.mkdtemp))
    elif where == "rename":
        monkeypatch.setattr(Path, "rename", once(Path.rename))
    else:
        monkeypatch.setattr(data_place, "open_lock", once(open_lock))

    class Stopping:
        def is_set(self) -> bool:
            return False

        def wait(self, _seconds: float) -> bool:  # the retry pause: what the failure left
            seen.append((record(), clones(), data_place.default().exists()))
            return False

    machine = SimpleNamespace(
        stopping=Stopping(),
        say=said.append,
        carry=lambda: done.append("carry"),
        retry=lambda: done.append("retry"),
        unshared="",
    )
    serve._cloning(machine)  # noqa: SLF001
    why = {
        "mkdtemp": f"no folder to clone into in {home()}: PermissionError: [Errno 13] denied",
        "rename": f"the clone could not be renamed to {data_place.default()}: PermissionError: [Errno 13] denied",
    }.get(where)
    unset = "the shared repository could not be set up: PermissionError: [Errno 13] denied"
    shown = f"cloning {url} failed: {why}" if why else unset
    assert said == [
        f"shared data: DataRepoError: {shown}; tried again every {serve.PROVISION_RETRY // 60} minutes",
        f"shared data: cloned {url} into {data_place.default()}",
    ]
    kept = {"remote": url, "failed": why} if why else {"remote": url}
    assert (seen, done, machine.unshared) == ([(kept, [], False)], ["carry", "retry"], "")  # cleared once cloned


def test_a_checkout_named_like_a_clone_leftover_is_kept_when_the_pointer_names_it(url: str) -> None:
    leftover, named = home() / ".data-clone-gone", home() / ".data-clone-owned"
    leftover.mkdir(parents=True)
    git(home(), "clone", "-q", url, str(named))  # an older `owlbear data` accepted any checkout
    data_place.pointer().write_text(json.dumps({"repository": str(named)}))
    with data_place.pointer_lock():
        data_place.settle()
    assert (leftover.exists(), (named / "config.json").read_text()) == (False, "{}\n")


def test_the_inventory_names_all_that_only_this_checkout_holds(tmp_path: Path, url: str) -> None:
    root = tmp_path / "data"
    git(tmp_path, "clone", "-q", url, str(root))
    shared = data_repo.DataRepo(root)
    assert data_place.inventory(shared) == []
    git(root, "switch", "-qc", "side")
    git(root, "commit", "-q", "--allow-empty", "-m", "unpushed")
    git(root, "switch", "-q", "main")
    (root / "config.json").write_text('{"a": 1}\n')
    git(root, "stash", "-q")
    (root / "memory" / "global").mkdir(parents=True)
    (root / "memory" / "global" / "note.md").write_text("kept\n")
    (root / "config.json").write_text('{"b": 2}\n')
    git(root, "worktree", "add", "-q", str(tmp_path / "linked"), "side")
    assert data_place.inventory(shared) == [
        "2 file(s) not committed, 1 of them never added",
        "1 commit(s) on local branches that no remote has",
        "1 stash(es)",
        f"linked worktree: {(tmp_path / 'linked').resolve()}",
    ]


def test_a_held_pointer_lock_is_refused_at_once_and_nothing_changes(url: str) -> None:
    home().mkdir(parents=True, exist_ok=True)
    data_place.pointer().write_text(json.dumps({"remote": url}))
    fd = os.open(home(), os.O_RDONLY | os.O_DIRECTORY)
    lock = open_lock(fd, blocking=False, name=local_home.DATA_LOCK)
    os.close(fd)
    try:
        with pytest.raises(data_place.BusyError, match="try again"):
            data_place.provision(url)
        assert cli.main(["data", url]) == 1
    finally:
        os.close(lock)
    assert (record(), data_place.default().exists()) == ({"remote": url}, False)


@pytest.mark.parametrize("left", ["source", "destination", "both", "neither"])
def test_an_unfinished_move_is_finished_undone_or_refused(tmp_path: Path, url: str, left: str) -> None:
    source, dest = tmp_path / "old-data", data_place.default()
    git(tmp_path, "clone", "-q", url, str(source))
    git(source, "worktree", "add", "-q", str(tmp_path / "linked"))
    home().mkdir(parents=True, exist_ok=True)
    transition = {"remote": url, "moving_from": str(source), "moving_to": str(dest)}
    data_place.pointer().write_text(json.dumps(transition))
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
    git(tmp_path, "clone", "-q", url, str(data_place.default()))
    data_place.pointer().write_text(
        json.dumps({"repository": str(data_place.default()), "remote": url, "moved_from": str(old)})
    )
    assert data_place.describe().warning == ""
    old.mkdir()
    assert data_place.describe().warning == f"the old checkout {old} is back; OwlBear doesn't use it"
    assert "is back" in cli.show_data(None)[1]


def test_the_host_clones_a_remote_only_pointer_in_the_background_then_loads_the_projects(
    tmp_path: Path, url: str
) -> None:
    gone = (tmp_path / "late.git").as_uri()
    home().mkdir(parents=True, exist_ok=True)
    data_place.pointer().write_text(json.dumps({"remote": gone}))
    said, done = [], []

    class Stopping:
        def is_set(self) -> bool:
            return False

        def wait(self, _seconds: float) -> bool:  # the retry pause: the remote appears meanwhile
            subprocess.run(["git", "clone", "-q", "--bare", url, str(tmp_path / "late.git")], check=True)  # noqa: S603, S607
            return False

    machine = SimpleNamespace(
        stopping=Stopping(),
        say=said.append,
        carry=lambda: done.append("carry"),
        retry=lambda: done.append("retry"),
        unshared="",
    )
    assert serve._provisioned(machine) is True  # noqa: SLF001
    assert said == [f"shared data: the shared repository {gone} is not cloned yet"]
    serve._cloning(machine)  # noqa: SLF001
    assert said[1].startswith(f"shared data: DataRepoError: cloning {gone} failed")
    assert said[2:] == [f"shared data: cloned {gone} into {data_place.default()}"]
    assert done == ["carry", "retry"]
    assert record() == {"repository": str(data_place.default().resolve()), "remote": gone}


OUT = "OUT begins\nwhat git printed on stdout, in the middle\nOUT ends"


def git_whole(args: tuple[str, ...], stderr: str) -> str:
    """A failed Git command as `CalledProcessError` words it, with both streams."""
    head = f"CalledProcessError: Command '{['git', *args]}' returned non-zero exit status 128."
    return f"{head}\nstderr:\n{stderr}\nstdout:\n{OUT}"


def git_fails(monkeypatch, stderr: str, fails) -> list[tuple[str, ...]]:
    """Makes the checkout's Git commands a picker chooses fail with distinct stdout and stderr; the args they ran."""
    real, ran = data_place._git, []  # noqa: SLF001 - the checkout's own Git calls are the boundary

    def git(cwd, *args, until=None):
        if fails(args):
            ran.append(args)
            return subprocess.CompletedProcess(["git", *args], 128, OUT + "\n", stderr + "\n")
        return real(cwd, *args, until=until)

    monkeypatch.setattr(data_place, "_git", git)
    return ran


def clone_fails_once(monkeypatch, stderr: str) -> list[tuple[str, ...]]:
    real, ran = git_run.run, []

    def run(cwd, *args, **kw):
        if args[:1] == ("clone",) and not ran:
            ran.append(args)
            said = (None, None) if kw.get("show") else (OUT + "\n", stderr + "\n")  # shown: Git wrote to the terminal
            return subprocess.CompletedProcess(["git", *args], 128, *said)
        return real(cwd, *args, **kw)

    monkeypatch.setattr(git_run, "run", run)
    return ran


def reason(tmp_path: Path, monkeypatch, before=None) -> str:
    """The reason the machine's project list (the Projects page's API) gives for a project that cannot load.

    *before* gets the registered project's path before the machine loads it.
    """
    monkeypatch.setattr(project.readiness, "ready", lambda _store, _repo, **_kwargs: [])
    path = tmp_path / "shop"
    git(tmp_path, "init", "-q", str(path))
    git(path, "commit", "-q", "--allow-empty", "-m", "i")
    registry.register(path.resolve())
    if before:
        before(path.resolve())
    at = datetime.now(UTC)
    machine = Machine(HostRecord(url="http://127.0.0.1:9/", token="t", pid=1, started_at=at, code=codebase.CURRENT))  # noqa: S106
    try:
        machine.load_all()
        http = TestClient(app.create(machine), base_url="http://127.0.0.1", headers={"authorization": "Bearer t"})
        (shown,) = http.get("/api/next/projects").json()["projects"]
    finally:
        machine.stop_all()
    assert shown["state"] == "failed"
    return shown["reason"]


def test_a_failed_clone_says_git_whole_in_the_projects_reason_and_the_host_log(
    tmp_path: Path, url: str, monkeypatch, whole_error, capsys
) -> None:
    """#921: the host's failed clone, a path in it, arrives whole in the project's reason and the host log.

    `owlbear data` lets Git write to the terminal, so there the failure names the command and its exit.
    """
    stderr = f"fatal: {tmp_path / 'owlbear-data.git' / 'objects'} cannot be read\n{whole_error}"
    ran = clone_fails_once(monkeypatch, stderr)
    assert cli.main(["data", url]) == 1
    shown = f"CalledProcessError: Command '{['git', *ran[0]]}' returned non-zero exit status 128."
    assert f"cloning {url} failed: {shown}" in capsys.readouterr().out
    assert record() == {"remote": url, "failed": shown}

    ran = clone_fails_once(monkeypatch, stderr)
    said = []
    stopping = SimpleNamespace(is_set=lambda: False, wait=lambda _seconds: True)
    machine = SimpleNamespace(stopping=stopping, say=said.append, unshared="")
    serve._cloning(machine)  # noqa: SLF001
    why = git_whole(ran[0], stderr)
    every = serve.PROVISION_RETRY // 60
    unshared = f"DataRepoError: cloning {url} failed: {why}; tried again every {every} minutes"
    assert (said, machine.unshared) == ([f"shared data: {unshared}"], unshared)
    assert reason(tmp_path, monkeypatch) == (
        "its Delivery state cannot be opened: StoreError: DataRepoError: "
        f"the shared repository {url} is not cloned yet: {why}"
    )


def test_a_failed_worktree_repair_says_git_whole_at_owlbear_data_host_start_and_the_projects_reason(
    tmp_path: Path, url: str, monkeypatch, whole_error, capsys
) -> None:
    """#921: relinking after a move says the failed `git worktree repair` whole, and the pointer keeps it until done."""
    source, dest = tmp_path / "old-data", data_place.default()  # a move that stopped after its rename
    git(tmp_path, "clone", "-q", url, str(source))
    git(source, "worktree", "add", "-q", str(tmp_path / "linked"))
    home().mkdir(parents=True, exist_ok=True)
    data_place.pointer().write_text(json.dumps({"remote": url, "moving_from": str(source), "moving_to": str(dest)}))
    source.rename(dest)
    real = data_place._git  # noqa: SLF001
    ran = git_fails(monkeypatch, whole_error, lambda args: args == ("worktree", "repair"))
    why = git_whole(("worktree", "repair"), whole_error)
    moved = f"the shared repository was moved to {dest}, but {why}; fix it, then run `owlbear data` again"

    assert cli.main(["data"]) == 1
    assert capsys.readouterr().out == f"Shared data: problem: DataRepoError: {moved}\n"
    said = []
    machine = SimpleNamespace(say=said.append, curation=SimpleNamespace(shared=lambda: None))  # no cut-short apply
    assert serve._provisioned(machine) is False  # noqa: SLF001
    noticed = f"at this start, DataRepoError: {moved}; `owlbear restart` looks again"
    assert (said, machine.unshared) == ([f"shared data: DataRepoError: {moved}"], noticed)
    assert (len(ran), record()["failed"]) == (2, why)
    unfinished = f"moving the shared repository from {source} to {dest} is not finished: {why}"
    unfinished += "; `owlbear data` finishes it"
    opened = f"its Delivery state cannot be opened: StoreError: DataRepoError: {unfinished}"
    assert reason(tmp_path, monkeypatch) == opened

    monkeypatch.setattr(data_place, "_git", real)  # repaired: the next `owlbear data` finishes the move
    assert cli.main(["data"]) == 0
    assert record() == {"repository": str(dest), "remote": url, "moved_from": str(source)}


@pytest.mark.parametrize(("clone_address", "words"), [(False, "Shared data: problem:"), (True, "Not set:")])
def test_owlbear_data_prints_a_failed_move_whole_after_its_own_words(  # noqa: PLR0913, PLR0917 - fixtures
    tmp_path: Path, url: str, monkeypatch, whole_error, capsys, clone_address, words
) -> None:
    """#971: `owlbear data`, with or without a clone address, prints why the move stopped whole: the error's type,
    Git's streams and a note."""
    source, dest = tmp_path / "old-data", data_place.default()
    git(tmp_path, "clone", "-q", url, str(source))
    home().mkdir(parents=True, exist_ok=True)
    data_place.pointer().write_text(json.dumps({"remote": url, "moving_from": str(source), "moving_to": str(dest)}))
    source.rename(dest)
    git_fails(monkeypatch, whole_error, lambda args: args == ("worktree", "repair"))
    real, note = data_place.recover, "a note added on the way END"

    def recover() -> str:
        try:
            return real()
        except data_repo.DataRepoError as exc:
            exc.add_note(note)
            raise

    monkeypatch.setattr(data_place, "recover", recover)
    why = git_whole(("worktree", "repair"), whole_error)
    moved = f"the shared repository was moved to {dest}, but {why}; fix it, then run `owlbear data` again"
    assert cli.main(["data", url] if clone_address else ["data"]) == 1
    assert capsys.readouterr().out == f"{words} DataRepoError: {moved}\n{note}\n"


def test_an_unreadable_checkout_says_git_whole_in_owlbear_data_s_inventory(
    tmp_path: Path, url: str, monkeypatch, whole_error, capsys
) -> None:
    """#921: a failed inventory command arrives whole in what `owlbear data` prints."""
    root = tmp_path / "data"
    git(tmp_path, "clone", "-q", url, str(root))
    assert data_place.point(root) == data_repo.DataRepo(root.resolve())
    ran = git_fails(monkeypatch, whole_error, lambda args: args[:2] == ("status", "--porcelain=v1"))

    cli.main(["data"])

    assert len(ran) == 1
    assert f"{root.resolve()} cannot be read: {git_whole(ran[0], whole_error)}" in capsys.readouterr().out


def test_a_role_move_whose_publication_hold_git_fails_says_git_whole_in_the_projects_reason(
    tmp_path: Path, url: str, monkeypatch, failing_git, whole_error
) -> None:
    """P21: opening a project moves its old profile's roles into the shared config; the hold that write needs is
    refused by Git, and the Projects page's reason carries Git's words whole."""
    home().mkdir(parents=True, exist_ok=True)
    git(home(), "clone", "-q", url, "data")
    git(home() / "data", "config", "user.name", "t")
    git(home() / "data", "config", "user.email", "t@example.com")
    ran: list[tuple[str, ...]] = []
    hold_probe = ("ls-tree", publication_hold.UPSTREAM)
    failing_git(whole_error, lambda args, _until: args[:2] == hold_probe and not ran.append(args))

    def old_profile(path: Path) -> None:
        raw = {"format": 1, "version": 3, "roles": {"reviewer": {"model": "r-1", "effort": "max"}}, "runtime": "vscode"}
        (project_home.located(path) / "profile.json").write_text(json.dumps(raw))

    said = reason(tmp_path, monkeypatch, old_profile)
    why = f"CalledProcessError: Command '{['git', *ran[-1]]}' returned non-zero exit status 128.\n{whole_error}"
    assert said == (
        "its Delivery state cannot be opened: StoreError: the old profile's role overrides were not moved: "
        f"DataRepoError: the automatic change was not written: {why}"
    )
