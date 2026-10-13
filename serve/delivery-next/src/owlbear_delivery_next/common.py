"""Delivery's settings in the shared documents repository (TD-57, TD-59, TD-64).

A pointer file names the repository. The global layer lives at its root, each project's layer in a folder named
after the project's repository, claimed by that repository's identity. Every save is committed and pushed under one
repository-wide lock; a failed commit or push is reported, never hidden. A running host passes its view to its
runners through ``OWLBEAR_COMMON``, so the settings page and the runners always read the same layers.
"""

from __future__ import annotations

import contextlib
import fcntl
import json
import os
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

CONFIG, CLAIM, MEMORY = "config.json", "repository", "memory"
VIEW = "OWLBEAR_COMMON"  # the host's view for its runners: the repository's path, or empty for none
EXCLUDE = (".*.lock", ".tmp-*", "*/visual/*/*.png")  # Delivery's locks, temporary files and calibration screenshots
GIT_SECONDS, LOCK_SECONDS, SAVE_SECONDS, PENDING_SECONDS = 10, 20, 45, 4  # a save answers within the page's 60 s
_UNSAFE = re.compile(r"[^A-Za-z0-9._-]+")


class CommonError(ValueError):
    """The pointer names no usable repository, or a project folder belongs to another repository."""


def pointer() -> Path:
    """Where the machine records the shared repository; ``OWLBEAR_HOME`` moves it (tests)."""
    return Path(os.environ.get("OWLBEAR_HOME") or Path.home() / ".owlbear") / "common.json"


def _git(cwd: Path, *args: str, until: float | None = None) -> subprocess.CompletedProcess[str]:
    """One git command, ended by ``until`` (monotonic) at the latest; a timeout is a failed command. Never prompts."""
    quiet = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    seconds = GIT_SECONDS if until is None else max(0.5, min(GIT_SECONDS, until - time.monotonic()))
    try:
        return subprocess.run(  # noqa: S603
            ["git", *args],  # noqa: S607
            cwd=cwd,
            env=quiet,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=seconds,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return subprocess.CompletedProcess(["git", *args], 1, "", str(exc))


def _top(root: Path) -> Path | None:
    out = _git(root, "rev-parse", "--show-toplevel") if root.is_dir() else None
    return Path(out.stdout.strip()).resolve() if out and out.returncode == 0 else None


@dataclass(frozen=True)
class Common:
    """The shared repository's checkout on this machine."""

    root: Path

    @property
    def global_path(self) -> Path:
        """The global layer, at the repository's root."""
        return self.root / CONFIG

    def project_path(self, name: str) -> Path:
        """A project's layer, in the folder named after its repository."""
        return self.root / name / CONFIG

    def memory_path(self, name: str) -> Path:
        """A project's agent memory, beside its layer (TD-72); memory curation commits it."""
        return self.root / name / MEMORY

    @contextlib.contextmanager
    def locked(self, wait: float | None = None) -> Iterator[None]:
        """Hold the repository-wide lock that serializes every write, commit, push and rebase; wait a bounded time."""
        wait = LOCK_SECONDS if wait is None else wait
        found = _git(self.root, "rev-parse", "--absolute-git-dir")
        admin = Path(found.stdout.strip())
        if found.returncode or not admin.is_dir():
            msg = f"the git folder of {self.root} cannot be found: {found.stderr.strip()[:200]}"
            raise CommonError(msg)
        fd = os.open(admin / "owlbear-delivery.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            end = time.monotonic() + wait
            while True:
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() > end:
                        msg = "another settings save is still running; try again"
                        raise CommonError(msg) from None
                    time.sleep(0.1)
            self._exclude(admin)
            yield
        finally:
            os.close(fd)

    def _exclude(self, admin: Path) -> None:
        path = admin / "info" / "exclude"
        text = path.read_text() if path.exists() else ""
        if missing := [p for p in EXCLUDE if p not in text.splitlines()]:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text + ("" if not text or text.endswith("\n") else "\n") + "\n".join(missing) + "\n")

    def claim(self, name: str, identity: str) -> bool:
        """Bind the project folder to one repository; True when this call wrote the claim.

        Another repository of the same name is refused.
        """
        path = self.root / name / CLAIM
        held = path.read_text().strip() if path.exists() else ""
        if held and held != identity:
            msg = f"the shared settings folder {name} belongs to {held}, not {identity}; rename one repository"
            raise CommonError(msg)
        if held:
            return False
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(identity + "\n")
        return True

    def publish(self, path: Path, message: str, until: float | None = None) -> str:
        """Commit ``path`` alone if it changed and push; what the owner should know when that fails, else nothing.

        The caller holds ``locked``. Unpushed earlier commits are pushed too, so an unchanged save retries them.
        """
        until = time.monotonic() + SAVE_SECONDS if until is None else until
        rel = path.relative_to(self.root).as_posix()
        if (added := _git(self.root, "add", "--", rel, until=until)).returncode:
            return f"saved, but not committed: {added.stderr.strip()[:200]}"
        staged = _git(self.root, "diff", "--cached", "--quiet", "--", rel, until=until).returncode
        if staged and (made := _git(self.root, "commit", "-q", "-m", message, "--", rel, until=until)).returncode:
            return f"saved, but not committed: {made.stderr.strip()[:200]}"
        return self._push(until)

    def _push(self, until: float) -> str:
        """Push; once rejected, rebase on the remote and push again; a failed rebase is undone, never left half done."""
        if _git(self.root, "push", "-q", until=until).returncode == 0:
            return ""
        if _git(self.root, "-c", "rebase.autoStash=false", "pull", "-q", "--rebase", until=until).returncode:
            admin = Path(_git(self.root, "rev-parse", "--absolute-git-dir", until=until).stdout.strip() or self.root)
            if any((admin / d).exists() for d in ("rebase-merge", "rebase-apply")):
                _git(self.root, "rebase", "--abort", until=until + PENDING_SECONDS)
            return f"saved and committed in {self.root}, but it could not be merged with the remote; push it by hand"
        sent = _git(self.root, "push", "-q", until=until)
        if sent.returncode:
            return f"saved and committed in {self.root}, but the push failed: {sent.stderr.strip()[:200]}"
        return ""

    def pending(self) -> str:
        """What in the shared checkout is not yet committed or pushed, as a notice; nothing when all is published."""
        until = time.monotonic() + PENDING_SECONDS
        status = _git(self.root, "status", "--porcelain", "--", ".", f":(exclude)*/{MEMORY}/*", until=until)
        if status.returncode:
            return f"the shared settings repository {self.root} cannot be read: {status.stderr.strip()[:200]}"
        files = status.stdout.splitlines()
        unpushed = _git(self.root, "rev-list", "--count", "HEAD", "--not", "--remotes", until=until).stdout.strip()
        parts = [f"{len(files)} file(s) not committed"] if files else []
        if unpushed.isdigit() and int(unpushed):
            parts.append(f"{unpushed} commit(s) not pushed")
        return f"unpublished in {self.root}: {', '.join(parts)}; the next save retries" if parts else ""


def locate() -> Common | None:
    """The shared repository: the host's view when one is passed down, else the pointer's; None without either."""
    if (view := os.environ.get(VIEW)) is not None:
        return Common(Path(view)) if view else None
    path = pointer()
    try:
        data = json.loads(path.read_text())
        root = Path(data["repository"]).expanduser().resolve()
    except FileNotFoundError:
        return None
    except (OSError, ValueError, KeyError, TypeError) as exc:
        msg = f"{path} names no repository"
        raise CommonError(msg) from exc
    if _top(root) != root:
        msg = f"{root}, named in {path}, is not a git repository's top folder"
        raise CommonError(msg)
    return Common(root)


def point(root: Path) -> Common:
    """Record ``root`` as this machine's shared repository; it must be a git checkout's top folder."""
    root = root.expanduser().resolve()
    if _top(root) != root:
        msg = f"{root} is not a git repository's top folder"
        raise CommonError(msg)
    path = pointer()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"repository": str(root)}) + "\n")
    return Common(root)


def identity(repo: Path) -> str:
    """Who a project is: its origin remote without scheme, user and ``.git``, else its main checkout's path."""
    url = _git(repo, "config", "--get", "remote.origin.url").stdout.strip()
    if url:
        bare = re.sub(r"^[a-z+]+://", "", url).split("@", 1)[-1].replace(":", "/", 1)
        return bare.removesuffix("/").removesuffix(".git")
    top = _git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir").stdout.strip()
    return str(Path(top).parent) if top else str(repo.resolve())


def project_name(repo: Path) -> str:
    """The project's repository name (TD-64): the last part of its identity, made safe for a folder name."""
    safe = _UNSAFE.sub("-", identity(repo).rsplit("/", 1)[-1]).strip(".-")
    return safe or "project"
