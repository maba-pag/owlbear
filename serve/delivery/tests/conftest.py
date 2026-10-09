"""Conftest for Delivery package tests."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import psutil
import pytest

from owlbear_delivery.git_executable import resolve_git_executable

_OPERATION_MARKERS = (
    "MERGE_HEAD",
    "CHERRY_PICK_HEAD",
    "REVERT_HEAD",
    "BISECT_LOG",
    "ORIG_HEAD",
    "rebase-merge",
    "rebase-apply",
)


def _git(repository: Path, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        (resolve_git_executable(), "-C", str(repository), *arguments),
        check=check,
        capture_output=True,
        text=True,
    )


def _admin_path(repository: Path, name: str) -> Path:
    path = Path(_git(repository, "rev-parse", "--git-path", name).stdout.strip())
    return path if path.is_absolute() else repository / path


def _tree_bytes(root: Path, excluded: tuple[Path, ...] = ()) -> tuple[tuple[str, bytes], ...]:
    excluded_paths = tuple(path.resolve() for path in excluded)
    entries: list[tuple[str, bytes]] = []
    for current_root, directories, files in os.walk(root, followlinks=False):
        current = Path(current_root).resolve()
        directories[:] = [
            name for name in directories if (current / name).resolve() not in excluded_paths and name != ".git"
        ]
        for name in files:
            path = current / name
            if path.resolve() in excluded_paths or path.is_symlink():
                continue
            relative = path.relative_to(root.resolve()).as_posix()
            entries.append((relative, path.read_bytes()))
    return tuple(sorted(entries))


def _operation_state(repository: Path) -> tuple[tuple[str, tuple[tuple[str, bytes], ...]], ...]:
    state: list[tuple[str, tuple[tuple[str, bytes], ...]]] = []
    for marker in _OPERATION_MARKERS:
        path = _admin_path(repository, marker)
        if path.is_dir():
            state.append((marker, _tree_bytes(path)))
        elif path.is_file():
            state.append((marker, ((path.name, path.read_bytes()),)))
        else:
            state.append((marker, ()))
    return tuple(state)


def _refs(repository: Path) -> tuple[tuple[str, str], ...]:
    output = _git(repository, "for-each-ref", "--format=%(refname)\t%(objectname)", "refs").stdout
    return tuple(sorted(tuple(line.split("\t", 1)) for line in output.splitlines() if line))


def _status(repository: Path, allowed_file_prefixes: tuple[str, ...]) -> str:
    output = _git(repository, "status", "--porcelain=v2", "--untracked-files=all").stdout
    retained: list[str] = []
    for line in output.splitlines():
        record_type = line[:1]
        if record_type in "?!":
            paths = (line[2:],)
        elif record_type == "1":
            paths = (line.split(maxsplit=8)[-1],)
        elif record_type == "2":
            fields, original_path = line.split("\t", 1)
            paths = (fields.split(maxsplit=9)[-1], original_path)
        elif record_type == "u":
            paths = (line.split(maxsplit=10)[-1],)
        else:
            paths = ()
        if any(path == prefix or path.startswith(f"{prefix}/") for path in paths for prefix in allowed_file_prefixes):
            continue
        retained.append(line)
    return "\n".join(retained) + ("\n" if retained else "")


def _prepare_branch_checkout_state(repository: Path, user_state: str) -> None:
    base_branch = _git(repository, "symbolic-ref", "--short", "HEAD").stdout.strip()
    _git(repository, "config", "rebase.autoStash", "false")
    branch = f"user-{user_state.removeprefix('mid-')}"
    _git(repository, "checkout", "-b", branch)
    (repository / "product.txt").write_text(f"{user_state} side\n", encoding="utf-8")
    _git(repository, "add", "product.txt")
    _git(repository, "commit", "-m", f"{user_state} side")
    _git(repository, "checkout", base_branch)
    (repository / "product.txt").write_text(f"{user_state} target\n", encoding="utf-8")
    _git(repository, "add", "product.txt")
    _git(repository, "commit", "-m", f"{user_state} target")
    _git(repository, "checkout", branch)

    if user_state in {"conflicted", "mid-merge"}:
        merge = _git(repository, "merge", base_branch, check=False)
        if merge.returncode == 0:
            message = f"expected {user_state} merge setup to conflict"
            raise AssertionError(message)
        if user_state == "conflicted":
            _git(repository, "merge", "--quit")
        return
    rebase_mode = "--apply" if user_state == "mid-rebase-apply" else "--merge"
    rebase = _git(repository, "rebase", rebase_mode, base_branch, check=False)
    if rebase.returncode == 0:
        message = f"expected {user_state} setup to conflict"
        raise AssertionError(message)


def _prepare_cherry_pick_state(repository: Path) -> None:
    base_branch = _git(repository, "symbolic-ref", "--short", "HEAD").stdout.strip()
    branch = "user-cherry-pick"
    _git(repository, "checkout", "-b", branch)
    (repository / "product.txt").write_text("mid-cherry-pick side\n", encoding="utf-8")
    _git(repository, "add", "product.txt")
    _git(repository, "commit", "-m", "mid-cherry-pick side")
    _git(repository, "checkout", base_branch)
    (repository / "product.txt").write_text("mid-cherry-pick target\n", encoding="utf-8")
    _git(repository, "add", "product.txt")
    _git(repository, "commit", "-m", "mid-cherry-pick target")
    target_commit = _git(repository, "rev-parse", "HEAD").stdout.strip()
    _git(repository, "checkout", branch)
    cherry_pick = _git(repository, "cherry-pick", target_commit, check=False)
    if cherry_pick.returncode == 0:
        message = "expected mid-cherry-pick setup to conflict"
        raise AssertionError(message)


def _prepare_revert_state(repository: Path) -> None:
    (repository / "product.txt").write_text("mid-revert target\n", encoding="utf-8")
    _git(repository, "add", "product.txt")
    _git(repository, "commit", "-m", "mid-revert target")
    target_commit = _git(repository, "rev-parse", "HEAD").stdout.strip()
    branch = "user-revert"
    _git(repository, "checkout", "-b", branch)
    (repository / "product.txt").write_text("mid-revert side\n", encoding="utf-8")
    _git(repository, "add", "product.txt")
    _git(repository, "commit", "-m", "mid-revert side")
    revert = _git(repository, "revert", "--no-edit", target_commit, check=False)
    if revert.returncode == 0:
        message = "expected mid-revert setup to conflict"
        raise AssertionError(message)


def _prepare_bisect_state(repository: Path) -> None:
    branch = "user-bisect"
    _git(repository, "checkout", "-b", branch)
    for index in range(4):
        (repository / "product.txt").write_text(f"mid-bisect-{index}\n", encoding="utf-8")
        _git(repository, "add", "product.txt")
        _git(repository, "commit", "-m", f"mid-bisect {index}")
    _git(repository, "bisect", "start")
    _git(repository, "bisect", "bad", "HEAD")
    _git(repository, "bisect", "good", "HEAD~3")


def _prepare_user_checkout_state(repository: Path, user_state: str) -> None:
    if user_state == "modified":
        (repository / "product.txt").write_text("modified user work\n", encoding="utf-8")
    elif user_state == "staged":
        (repository / "product.txt").write_text("staged user work\n", encoding="utf-8")
        _git(repository, "add", "product.txt")
    elif user_state == "untracked":
        (repository / "untracked-user.txt").write_text("untracked user work\n", encoding="utf-8")
    elif user_state == "detached":
        _git(repository, "checkout", "--detach", "HEAD")
    elif user_state in {"conflicted", "mid-merge", "mid-rebase", "mid-rebase-apply"}:
        _prepare_branch_checkout_state(repository, user_state)
    elif user_state == "mid-cherry-pick":
        _prepare_cherry_pick_state(repository)
    elif user_state == "mid-revert":
        _prepare_revert_state(repository)
    elif user_state == "mid-bisect":
        _prepare_bisect_state(repository)
    elif user_state != "clean":
        message = f"unknown user checkout state: {user_state}"
        raise ValueError(message)


def _seed_user_checkout_metadata(repository: Path) -> None:
    _git(repository, "config", "--local", "owlbear.user-preservation", "sentinel")
    hooks = _admin_path(repository, "hooks")
    hooks.mkdir(parents=True, exist_ok=True)
    (hooks / "user-preservation-hook").write_bytes(b"preserve this hook\n")
    _git(repository, "branch", "user-unrelated", "HEAD")
    stash_file = repository / "stashed-user.txt"
    stash_file.write_text("preserve this stash\n", encoding="utf-8")
    _git(repository, "stash", "push", "--include-untracked", "-m", "user preservation sentinel")


@dataclass(frozen=True)
class UserCheckoutSnapshot:
    """Semantic user-checkout state used by Delivery safety regression tests."""

    allowed_ref_prefixes: tuple[str, ...]
    allowed_file_prefixes: tuple[str, ...]
    head: tuple[str, str]
    index: str
    status: str
    files: tuple[tuple[str, bytes], ...]
    refs: tuple[tuple[str, str], ...]
    stash_reflog: str
    local_config: str
    hooks: tuple[tuple[str, bytes], ...]
    operation_state: tuple[tuple[str, tuple[tuple[str, bytes], ...]], ...]

    @classmethod
    def capture(
        cls,
        repository: Path,
        allowed_ref_prefixes: tuple[str, ...] = (),
        allowed_file_prefixes: tuple[str, ...] = (),
    ) -> UserCheckoutSnapshot:
        symbolic_head = _git(repository, "symbolic-ref", "--quiet", "--short", "HEAD", check=False).stdout.strip()
        commit = _git(repository, "rev-parse", "--verify", "HEAD", check=False).stdout.strip()
        hooks = _admin_path(repository, "hooks")
        files = _tree_bytes(
            repository,
            (
                repository / ".owlbear" / "delivery" / "runtime",
                repository / ".owlbear" / "delivery" / "worktrees",
            ),
        )
        return cls(
            allowed_ref_prefixes=allowed_ref_prefixes,
            allowed_file_prefixes=allowed_file_prefixes,
            head=(symbolic_head, commit),
            index=_git(repository, "ls-files", "--stage").stdout,
            status=_status(repository, allowed_file_prefixes),
            files=tuple(
                (name, content)
                for name, content in files
                if not any(name == prefix or name.startswith(f"{prefix}/") for prefix in allowed_file_prefixes)
            ),
            refs=_refs(repository),
            stash_reflog=_git(repository, "reflog", "show", "--format=%H %gs", "refs/stash", check=False).stdout,
            local_config=_git(repository, "config", "--local", "--null", "--list").stdout,
            hooks=_tree_bytes(hooks) if hooks.exists() else (),
            operation_state=_operation_state(repository),
        )

    def assert_unchanged(self, repository: Path) -> None:
        current = self.capture(repository, self.allowed_ref_prefixes, self.allowed_file_prefixes)
        assert current.head == self.head
        assert current.index == self.index
        assert current.status == self.status
        assert current.files == self.files
        expected_refs = {
            name: value
            for name, value in self.refs
            if not any(name == prefix or name.startswith(f"{prefix}/") for prefix in self.allowed_ref_prefixes)
        }
        actual_refs = {
            name: value
            for name, value in current.refs
            if not any(name == prefix or name.startswith(f"{prefix}/") for prefix in self.allowed_ref_prefixes)
        }
        assert actual_refs == expected_refs
        assert current.stash_reflog == self.stash_reflog
        assert current.local_config == self.local_config
        assert current.hooks == self.hooks
        assert current.operation_state == self.operation_state


@pytest.fixture
def user_checkout_snapshot() -> Callable[..., UserCheckoutSnapshot]:
    return UserCheckoutSnapshot.capture


@pytest.fixture(autouse=True)
def isolate_git_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent Delivery tests from inheriting the host Git configuration."""
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_SYSTEM", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_CONFIG_COUNT", "0")


@pytest.fixture
def prepare_user_checkout_state() -> Callable[[Path, str], None]:
    return _prepare_user_checkout_state


@pytest.fixture
def seed_user_checkout_metadata() -> Callable[[Path], None]:
    return _seed_user_checkout_metadata


@pytest.fixture
def _tmp_path(tmp_path: Path) -> Path:
    """Alias for tmp_path with underscore prefix (for tests that use _tmp_path)."""
    return tmp_path


_EXT_TRANSPORT_HELPER = """\
import os, pathlib, sys, time
service, bare, root, git = sys.argv[1], sys.argv[2], pathlib.Path(sys.argv[3]), sys.argv[4]
name = service.removeprefix("git-")
log = root / "invocations.log"
with log.open("a", encoding="utf-8") as stream:
    stream.write(f"{name} {os.getpid()}\\n")
index = sum(1 for line in log.read_text(encoding="utf-8").splitlines() if line.split()[0] == name) - 1
modes_path = root / f"{name}.modes"
modes = modes_path.read_text(encoding="utf-8").split() if modes_path.exists() else ["pass"]
mode = modes[min(index, len(modes) - 1)]
deadline = time.monotonic() + 30
if mode == "arm-hang":
    (root / "armed").touch()
if mode in {"hang", "arm-hang"} or (name == "upload-pack" and (root / "armed").exists()):
    time.sleep(300)
    sys.exit(1)
if mode == "orphan":
    os.setsid()
    time.sleep(300)
    sys.exit(1)
if mode == "gate":
    (root / "gate-blocked").touch()
    while not (root / "gate-release").exists() and time.monotonic() < deadline:
        time.sleep(0.02)
if name == "upload-pack":
    while (root / "receiving").exists() and time.monotonic() < deadline:
        time.sleep(0.02)
if mode == "detach":
    os.setsid()
    (root / "receiving").touch()
    os.dup2(os.open(root / "detached.err", os.O_WRONLY | os.O_CREAT | os.O_APPEND), 2)
os.execv(git, [git, name, bare])
"""


@dataclass(frozen=True)
class ExtRemote:
    """A local bare remote reached through a scriptable ``ext::`` transport helper.

    Modes per invocation of one service: ``pass``, ``hang`` (never answers), ``arm-hang`` (never
    answers and makes every later ``upload-pack`` hang), ``orphan`` (hangs in its own session),
    ``gate`` (waits for ``release()``) and ``detach`` (runs ``receive-pack`` outside the client's
    process group, so it survives the client's timeout).
    """

    bare: Path
    root: Path
    url: str

    def use(self, repository: Path, remote: str = "origin") -> None:
        _git(repository, "config", "protocol.ext.allow", "always")
        _git(repository, "remote", "set-url", remote, self.url)

    def modes(self, service: str, *modes: str) -> None:
        (self.root / f"{service}.modes").write_text(" ".join(modes), encoding="utf-8")

    def pids(self, service: str) -> tuple[int, ...]:
        log = self.root / "invocations.log"
        lines = log.read_text(encoding="utf-8").splitlines() if log.exists() else []
        return tuple(int(line.split()[1]) for line in lines if line.split()[0] == service)

    def wait_blocked(self, timeout: float = 20) -> None:
        deadline = time.monotonic() + timeout
        while not (self.root / "gate-blocked").exists():
            if time.monotonic() > deadline:
                message = "ext transport never reached its gate"
                raise AssertionError(message)
            time.sleep(0.02)

    def release(self) -> None:
        (self.root / "gate-release").touch()

    def assert_exited(self, service: str, timeout: float = 10) -> None:
        """Fail unless every helper process started for ``service`` has exited."""
        assert_processes_gone(self.pids(service), timeout)

    def slow_accepting_receive(self, seconds: float) -> None:
        """Make the bare remote accept pushes only after a slow ``pre-receive`` hook."""
        hooks = self.bare / "hooks"
        _write_hook(hooks / "pre-receive", f"cat >/dev/null\nsleep {seconds}\nexit 0\n")
        marker = self.root / "receiving"
        _write_hook(
            hooks / "reference-transaction",
            f'cat >/dev/null\nif [ "$1" = committed ]; then rm -f "{marker}"; fi\nexit 0\n',
        )
        _git(self.bare, "config", "receive.keepAlive", "0")


def _write_hook(path: Path, body: str) -> None:
    path.write_text(f"#!/bin/sh\n{body}", encoding="utf-8")
    path.chmod(0o755)


def assert_processes_gone(pids: tuple[int, ...], timeout: float = 10) -> None:
    """Fail unless every PID has exited (a reaped or zombie process counts as gone)."""
    deadline = time.monotonic() + timeout
    remaining = set(pids)
    while remaining:
        remaining = {pid for pid in remaining if _process_running(pid)}
        if not remaining:
            return
        if time.monotonic() > deadline:
            message = f"remote Git transport processes survived: {sorted(remaining)}"
            raise AssertionError(message)
        time.sleep(0.05)


def _process_running(pid: int) -> bool:
    try:
        return psutil.Process(pid).status() != psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        return False


@pytest.fixture
def ext_remote(tmp_path: Path) -> Callable[[Path], ExtRemote]:
    """Build an ``ext::`` transport for one local bare remote."""
    counter = iter(range(1_000))

    def build(bare: Path) -> ExtRemote:
        root = tmp_path / f"ext-transport-{next(counter)}"
        root.mkdir()
        helper = root / "helper.py"
        helper.write_text(_EXT_TRANSPORT_HELPER, encoding="utf-8")
        url = f"ext::{sys.executable} {helper} %S {bare} {root} {resolve_git_executable()}"
        return ExtRemote(bare=bare, root=root, url=url)

    return build
