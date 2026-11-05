"""The local Git steps of onboarding a project (#723): what a folder holds, its first commit and its first push.

Every failure is raised whole: the command, its exit status and what Git printed. A command that reaches a remote runs
through ``remote_git`` as the account the caller chose (TD-402). Git picks the identity by remote URL on this machine
(``includeIf "hasconfig:remote.*.url:…"``), so the reads before a folder has its ``origin`` name the target remote.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal, NoReturn

from owlbear_delivery_next.git.command_failure import failed, failure, output
from owlbear_delivery_next.git.git_executable import resolve_git_executable
from owlbear_delivery_next.git.remote_git import RemoteGitFailed, run_remote_git
from owlbear_delivery_next.github.account import AccountMissing, Origin
from owlbear_delivery_next.local_system.git_files import probe_in

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable, Mapping

    from owlbear_delivery_next.git.access import Access
    from owlbear_delivery_next.local_system.git_files import Probe

type History = Literal["none", "unborn", "commits"]

TIMEOUT = 120.0  # a local command; `git add -A` in a large folder is the slowest
TRANSFER_TIMEOUT = 600.0  # a clone, pull or first push carries the whole history
CI_PATH = ".github/workflows/ci.yml"
CI_WORKFLOW = """name: CI

on:
  push:
  pull_request:

permissions:
  contents: read

jobs:
  CI:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1  # v7.0.1
      - run: echo "Add this project's build and tests here."
"""
_UNSET = 1
_NO_REPOSITORY = 128
_REPOSITORY_VARIABLES = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE")


class LocalGitError(RuntimeError):
    """A local Git command failed or could not run; the message holds the command, its exit status and output."""


@dataclass(frozen=True)
class FolderState:
    """What a project folder holds before onboarding changes it."""

    exists: bool
    empty: bool  # no entries, or only a `.git` without commits
    has_files: bool  # an entry besides `.git`
    git: History  # of the folder's own repository: "none" for a folder inside another's
    origin: str | None  # as configured, before any URL rewrite
    enclosing: Path | None  # another work tree the folder lies in, or would be made in
    has_workflows: bool  # any file under `.github/workflows/`


def _git(
    cwd: Path, *args: str, ok: Collection[int] = (0,), timeout: float = TIMEOUT
) -> subprocess.CompletedProcess[str]:
    """Run ``git *args`` in *cwd*, never prompting; an exit status outside *ok* raises ``LocalGitError``."""
    environment = {k: v for k, v in os.environ.items() if k not in _REPOSITORY_VARIABLES}
    try:
        done = subprocess.run(  # noqa: S603 - fixed Git executable and code-owned argument vector
            [resolve_git_executable(), *args],
            cwd=cwd,
            env=environment,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        msg = f"git could not finish in {cwd}:\n{failure(exc)}"
        raise LocalGitError(msg) from exc
    if done.returncode not in ok:
        _raise(cwd, done)
    return done


def _raise(cwd: Path, done: subprocess.CompletedProcess[str]) -> NoReturn:
    msg = f"git failed in {cwd}:\n{failed(done)}"
    raise LocalGitError(msg)


def nearest_existing(path: Path) -> Path:
    """*path* when it is a folder, else its nearest parent that is one."""
    return next(p for p in (path, *path.parents) if p.is_dir())


def _toplevel(cwd: Path) -> Path | None:
    """The work tree *cwd* lies in, or ``None`` outside any."""
    done = _git(cwd, "rev-parse", "--show-toplevel", ok=(0, _NO_REPOSITORY))
    if done.returncode == 0:
        return Path(done.stdout.strip())
    if "not a git repository" in done.stderr:
        return None
    _raise(cwd, done)


def _history(path: Path) -> History:
    done = _git(path, "rev-parse", "--verify", "--quiet", "HEAD", ok=(0, 1))
    return "unborn" if done.returncode else "commits"


def _origin(path: Path) -> str | None:
    done = _git(path, "config", "--get", "remote.origin.url", ok=(0, _UNSET))
    return None if done.returncode else done.stdout.strip()


def folder_state(path: Path) -> FolderState:
    """Read what *path* holds; for an absent folder, the work tree is looked up from its nearest existing parent."""
    if path.exists() and not path.is_dir():
        msg = f"{path} is a file, not a folder"
        raise NotADirectoryError(msg)
    exists = path.is_dir()
    toplevel = _toplevel(path if exists else nearest_existing(path))
    own = exists and toplevel is not None and toplevel.samefile(path)
    git = _history(path) if own else "none"
    files = exists and any(entry.name != ".git" for entry in path.iterdir())
    workflows = path / ".github" / "workflows"
    return FolderState(
        exists=exists,
        empty=exists and not files and git != "commits",
        has_files=files,
        git=git,
        origin=_origin(path) if own else None,
        enclosing=None if own else toplevel,
        has_workflows=workflows.is_dir() and any(p.is_file() for p in workflows.rglob("*")),
    )


def target_probe(path_or_parent: Path, target_url: str) -> Probe:
    """``probe_in`` the folder or its nearest existing parent, every ``git config`` reading *target_url* as ``origin``.

    Readiness's identity and signing checks run through it as they would in a folder whose ``origin`` is the target.
    """
    inner = probe_in(nearest_existing(path_or_parent))

    def run(argv: list[str], env: Mapping[str, str] | None = None, /) -> tuple[int, str]:
        if target_url and len(argv) > 1 and Path(argv[0]).name == "git" and argv[1] == "config":
            argv = [argv[0], "-c", f"remote.origin.url={target_url}", *argv[1:]]
        return inner(argv, env)

    return run


def init(path: Path) -> None:
    """Make *path* a repository on ``main``, creating the folder when it is absent."""
    path.mkdir(parents=True, exist_ok=True)
    _git(path, "init", "-b", "main")


def set_origin(path: Path, url: str) -> None:
    """Point ``origin`` at *url*, adding the remote when it is missing."""
    present = "origin" in _git(path, "remote").stdout.split()
    _git(path, "remote", "set-url" if present else "add", "origin", url)


def write_author(path: Path, name: str, email: str) -> None:
    """Set the commit author in the repository's own configuration."""
    _git(path, "config", "--local", "user.name", name)
    _git(path, "config", "--local", "user.email", email)


def starter_files(path: Path, name: str, ci: bool, *, readme: bool = True) -> None:  # noqa: FBT001 - the tick
    """Write a first commit's starter files; never a ``.gitignore``.

    ``README.md`` holds ``# <name>`` (skipped with *readme* off, for a folder that has files); with *ci*, ``CI_PATH``
    holds one job ``CI`` run on ``push`` and ``pull_request``.
    """
    if readme:
        (path / "README.md").write_text(f"# {name}\n", encoding="utf-8")
    if ci:
        workflow = path / CI_PATH
        workflow.parent.mkdir(parents=True, exist_ok=True)
        workflow.write_text(CI_WORKFLOW, encoding="utf-8")


def finish_checkout(path: Path) -> None:
    """Write the files a clone stopped before checking out, from HEAD; a file already there is never overwritten."""
    _git(path, "read-tree", "HEAD")
    if missing := [f for f in _git(path, "ls-files", "--deleted", "-z").stdout.split("\0") if f]:
        _git(path, "checkout-index", "--", *missing)


def head(path: Path) -> str:
    """The sha of *path*'s HEAD."""
    return _git(path, "rev-parse", "HEAD").stdout.strip()


def first_commit(path: Path, message: str) -> str:
    """Commit every file ``.gitignore`` doesn't exclude, from an emptied index, and return the commit's sha.

    A file staged by hand before it was ignored stays on disk and out of the commit. Existing history is never added
    to: a repository that already has commits raises ``LocalGitError``.
    """
    if _history(path) == "commits":
        msg = f"{path} already has commits; OwlBear makes only a repository's first commit"
        raise LocalGitError(msg)
    _git(path, "read-tree", "--empty")
    _git(path, "add", "-A")
    _git(path, "commit", "-m", message)
    return head(path)


def _transfer_failed(what: str, done: subprocess.CompletedProcess[bytes]) -> NoReturn:
    said = output(done.stderr, done.stdout)
    msg = f"{what} failed (exit {done.returncode})" + (f":\n{said}" if said else "")
    raise RemoteGitFailed(msg, retry_safe=False, result=done)


def push_first(path: Path, access: Access) -> None:
    """Push the current branch to ``origin`` and track it; raises ``RemoteGitWriteUnknown`` or ``PushRefused``."""
    run_remote_git(path, ("push", "-u", "origin", "HEAD"), kind="write", access=access, timeout=TRANSFER_TIMEOUT)


def clone(parent: Path, url: str, name: str, access: Access) -> Path:
    """Clone *url* into ``parent / name`` and return that folder; a failed clone raises ``RemoteGitFailed`` whole."""
    parent.mkdir(parents=True, exist_ok=True)
    done = run_remote_git(parent, ("clone", "--", url, name), kind="read", access=access, timeout=TRANSFER_TIMEOUT)
    if done.returncode:
        _transfer_failed(f"cloning {url} into {parent / name}", done)
    return parent / name


def pull_default(path: Path, branch: str, access: Access) -> None:
    """Pull ``origin``'s *branch* into the clone and track it; a failed pull raises ``RemoteGitFailed`` whole."""
    arguments = ("pull", "--set-upstream", "origin", branch)
    done = run_remote_git(path, arguments, kind="read", access=access, timeout=TRANSFER_TIMEOUT)
    if done.returncode:
        _transfer_failed(f"pulling origin's {branch} into {path}", done)


def push_urls(path: Path, remote: str = "origin", timeout: float = TIMEOUT) -> list[str]:
    """Every URL a push to *remote* goes to: its push URLs, else its URLs, after Git's rewrites."""
    return _git(path, "remote", "get-url", "--push", "--all", remote, timeout=timeout).stdout.splitlines()


def _names(url: str) -> tuple[str, str, str] | None:
    """The GitHub repository *url* names, case-folded, or ``None`` for a local URL or one that names none."""
    try:
        origin = Origin.url(url)
    except AccountMissing:
        return None
    return None if origin == Origin.LOCAL else (origin.host, origin.owner.casefold(), origin.name.casefold())


def foreign_urls(urls: Iterable[str], repository_url: str) -> list[str]:
    """The URLs among *urls* that don't name *repository_url*'s GitHub repository, local ones included.

    HTTPS, SSH and scp-like forms, with or without ``.git``, name the same repository; owner and name match
    case-insensitively.
    """
    target = _names(repository_url)
    if target is None:
        msg = f"{repository_url} names no GitHub repository (https://<host>/<owner>/<name>)"
        raise ValueError(msg)
    return [url for url in urls if _names(url) != target]


def push_urls_name(path: Path, remote: str, repository_url: str, timeout: float = TIMEOUT) -> list[str]:
    """The URLs a push to *remote* would go to that don't name *repository_url*'s repository; empty when all do."""
    return foreign_urls(push_urls(path, remote, timeout), repository_url)
