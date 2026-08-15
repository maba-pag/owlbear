"""Conftest for Delivery package tests."""

from __future__ import annotations

import os
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

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
    return subprocess.run(
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
            raise AssertionError(f"expected {user_state} merge setup to conflict")
        if user_state == "conflicted":
            _git(repository, "merge", "--quit")
        return
    rebase = _git(repository, "rebase", "--merge", base_branch, check=False)
    if rebase.returncode == 0:
        message = "expected mid-rebase setup to conflict"
        raise AssertionError(message)


def _prepare_user_checkout_state(repository: Path, user_state: str) -> None:
    if user_state == "clean":
        return
    if user_state == "modified":
        (repository / "product.txt").write_text("modified user work\n", encoding="utf-8")
        return
    if user_state == "staged":
        (repository / "product.txt").write_text("staged user work\n", encoding="utf-8")
        _git(repository, "add", "product.txt")
        return
    if user_state == "untracked":
        (repository / "untracked-user.txt").write_text("untracked user work\n", encoding="utf-8")
        return
    if user_state == "detached":
        _git(repository, "checkout", "--detach", "HEAD")
        return
    if user_state in {"conflicted", "mid-merge", "mid-rebase"}:
        _prepare_branch_checkout_state(repository, user_state)
        return
    raise ValueError(f"unknown user checkout state: {user_state}")


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
