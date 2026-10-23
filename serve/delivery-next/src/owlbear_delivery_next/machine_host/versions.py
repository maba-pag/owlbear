"""OwlBear's versions on this machine (self-update build §3, §4, §5.1; TD-239, TD-300, TD-354, TD-369).

Every fetch goes through ``~/.owlbear/repo.git``, a bare clone of OwlBear's repository. A version is an annotated
tag ``vMAJOR.MINOR`` or ``vMAJOR``, installed beside the others as a detached worktree ``~/.owlbear/versions/<tag>``
with its own environment, never moved. The machine takes the newest version of its channel above the highest one
ever active whose commit descends from the active one: never backwards. Preparing a version installs it and runs
its own ``selfcheck``; nothing here switches the runtime.
"""

from __future__ import annotations

import contextlib
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from owlbear_delivery_next.local_system import codebase, leases, local_home
from owlbear_delivery_next.machine_host import machine_settings, registry

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from pathlib import Path

    type Descends = Callable[[str, str], bool]  # (older, newer): whether newer descends from older

REPO = "repo.git"
TAG = re.compile(r"v(\d+)(?:\.(\d+))?")
FREE = 2 * 1024**3  # bytes an install needs free (§3)
FETCH, SYNC, CHECK = 120, 900, 300  # seconds a fetch, an environment and a selfcheck may take
FIRST_MAJOR = "v0.1"  # a major-only machine's version until v1.0 exists (TD-369)
ACTIVATED = ".activated"  # in a version's folder once the alias named it
type Number = tuple[int, int]


class VersionError(Exception):
    """A version that cannot be fetched, chosen, installed or checked; the text says why."""


@dataclass(frozen=True)
class Choice:
    """The version to take, or why none is taken."""

    tag: str
    commit: str
    notes: tuple[str, ...] = ()


def number(tag: str) -> Number | None:
    """A version tag's number, ``vN`` as ``(N, 0)``; None for any other name."""
    found = TAG.fullmatch(tag)
    return (int(found[1]), int(found[2] or 0)) if found else None


def versions(tags: Mapping[str, str]) -> tuple[dict[str, str], list[str]]:
    """The version tags among *tags* (name to commit), and what was left out: ``vN`` and ``vN.0`` must agree."""
    found = {t: c for t, c in tags.items() if number(t) is not None}
    notes = []
    for tag in [t for t in found if "." not in t]:
        twin = f"{tag}.0"
        if twin in found and found[twin] != found[tag]:
            notes.append(f"{tag} and {twin} name different commits; neither is taken")
            found.pop(tag)
            found.pop(twin)
    return found, notes


def candidates(tags: Mapping[str, str], channel: Literal["minor", "major"]) -> dict[str, str]:
    """The versions a machine on *channel* may take: every one, or the major ones (``v0.1`` until ``v1``)."""
    if channel == "minor":
        return dict(tags)
    majors = {t: c for t, c in tags.items() if "." not in t}
    return majors or {t: c for t, c in tags.items() if t == FIRST_MAJOR}


def choose(
    tags: Mapping[str, str], channel: Literal["minor", "major"], mark: Number | None, active: str, descends: Descends
) -> Choice | None:
    """The newest version to take, never backwards: above *mark* and descending from the *active* commit.

    A runtime ahead of the newest version waits for a later one.
    """
    found, notes = versions(tags)
    allowed = candidates(found, channel)
    newest = max(allowed, key=lambda t: number(t) or (0, 0), default="")
    if not newest or (mark is not None and (number(newest) or (0, 0)) <= mark):
        return Choice("", "", tuple(notes)) if notes else None
    if active and not descends(active, allowed[newest]):
        notes.append(f"{newest} does not descend from the running commit {active[:12]}; a later version is taken")
        return Choice("", "", tuple(notes))
    return Choice(newest, allowed[newest], tuple(notes))


def _git(*args: str, cwd: Path | None = None, timeout: float = FETCH) -> str:
    env = os.environ | {"GIT_TERMINAL_PROMPT": "0", "GIT_ASKPASS": "", "SSH_ASKPASS": ""}
    verb = args[2] if args[0] == "-C" else args[0]
    try:
        done = subprocess.run(  # noqa: S603 - a fixed git argument vector
            [shutil.which("git") or "git", *args], cwd=cwd, env=env, capture_output=True, text=True, check=True,
            timeout=timeout,
        )  # fmt: skip
    except subprocess.CalledProcessError as exc:
        msg = f"git {verb} failed: {(exc.stderr or exc.stdout).strip()[:400]}"
        raise VersionError(msg) from exc
    except (OSError, subprocess.TimeoutExpired) as exc:
        msg = f"git {verb} failed: {exc}"
        raise VersionError(msg) from exc
    return done.stdout.strip()


def repo() -> Path:
    """``~/.owlbear/repo.git``, cloned from OwlBear's repository the first time."""
    path = local_home.root() / REPO
    if not (path / "HEAD").is_file():
        shutil.rmtree(path, ignore_errors=True)
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        _git("clone", "--bare", "--quiet", codebase.URL, str(path), timeout=FETCH * 5)
    return path


def fetch(path: Path) -> dict[str, str]:
    """Fetch ``main`` and every tag; each annotated version tag's name and the commit it peels to."""
    _git("-C", str(path), "fetch", "--quiet", "--force", "--tags", "origin", "+refs/heads/main:refs/heads/main")
    listed = _git("-C", str(path), "for-each-ref", "refs/tags", "--format=%(refname:short) %(objecttype)")
    named = [p[0] for p in (line.split() for line in listed.splitlines()) if p[1:] == ["tag"] and number(p[0])]
    found = {}
    for tag in named:  # peeled through every tag level; one naming no commit is no version
        with contextlib.suppress(VersionError):
            found[tag] = _git("-C", str(path), "rev-parse", "--verify", "--quiet", f"refs/tags/{tag}^{{commit}}")
    return found


def descends(path: Path) -> Descends:
    """Whether a commit descends from another, in *path*."""

    def check(older: str, newer: str) -> bool:
        try:
            _git("-C", str(path), "merge-base", "--is-ancestor", older, newer)
        except VersionError:
            return False
        return True

    return check


def active() -> tuple[str, str]:
    """The active version's tag (empty for a runtime that is no installed version) and commit; none without one.

    Raises:
        VersionError: A runtime is there but its commit cannot be read: nothing may be taken then.
    """
    runtime = local_home.root() / local_home.RUNTIME
    if not runtime.exists():
        return "", ""
    target = runtime.resolve()
    folder = local_home.root() / local_home.VERSIONS
    tag = target.name if runtime.is_symlink() and target.parent == folder.resolve() else ""
    return tag, _git("-C", str(runtime), "rev-parse", "HEAD")


def mark(tag: str) -> Number | None:
    """The highest version ever active: the alias's and ``machine.json``'s record of it, whichever is higher."""
    known = [n for n in (number(tag), number(registry.load().active)) if n is not None]
    return max(known) if known else None


def target() -> Choice | None:
    """Fetch, then the version this machine would take now; None when it is up to date."""
    channel = machine_settings.current().channel
    if channel is None:
        msg = "the versions this machine takes are unset; choose them on the Settings page"
        raise VersionError(msg)
    path = repo()
    tags = fetch(path)
    tag, commit = active()
    return choose(tags, channel, mark(tag), commit, descends(path))


def install(choice: Choice) -> Path:
    """Install *choice* beside the others with its own environment and check it there; its folder.

    A failure removes what it made.

    Raises:
        VersionError: Too little free disk, or its worktree, environment or selfcheck failed.
    """
    home = local_home.root()
    folder = home / local_home.VERSIONS / choice.tag
    if _installed(folder, choice.commit) and selfcheck(folder) == "":
        return folder  # installed and checked before
    remove(folder)  # a partial or other install first, so it never holds the disk an install needs
    if shutil.disk_usage(home).free < FREE:
        msg = f"an update needs {FREE // 1024**3} GB free on {home}; it waits until there is"
        raise VersionError(msg)
    folder.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        _build(choice, folder)
    except VersionError:
        remove(folder)
        raise
    return folder


def _installed(folder: Path, commit: str) -> bool:
    """Whether *folder* is a worktree of ``repo.git`` at *commit* with its environment."""
    if not (folder / ".venv").is_dir():
        return False
    try:
        listed = _git("-C", str(local_home.root() / REPO), "worktree", "list", "--porcelain")
        head = _git("-C", str(folder), "rev-parse", "HEAD")
    except VersionError:
        return False
    return head == commit and f"worktree {folder.resolve()}" in listed.splitlines()


def _build(choice: Choice, folder: Path) -> None:
    _git("-C", str(repo()), "worktree", "add", "--quiet", "--detach", str(folder), choice.commit)
    _sync(folder)
    if said := selfcheck(folder):
        msg = f"{choice.tag} failed its selfcheck: {said}"
        raise VersionError(msg)


def _sync(folder: Path) -> None:
    uv = shutil.which("uv")
    if uv is None:
        msg = "uv is not on this machine's PATH"
        raise VersionError(msg)
    env = {k: v for k, v in os.environ.items() if k not in {"VIRTUAL_ENV", "UV_PROJECT_ENVIRONMENT"}}
    command = [uv, "sync", "--locked", "--quiet"]  # every workspace member, as the runtime is deployed
    try:
        subprocess.run(  # noqa: S603 - uv and fixed arguments
            command, cwd=folder, env=env, capture_output=True, text=True, check=True, timeout=SYNC
        )
    except subprocess.CalledProcessError as exc:
        msg = f"its environment could not be made: {(exc.stderr or exc.stdout).strip()[-400:]}"
        raise VersionError(msg) from exc
    except (OSError, subprocess.TimeoutExpired) as exc:
        msg = f"its environment could not be made: {exc}"
        raise VersionError(msg) from exc


def selfcheck(folder: Path) -> str:
    """Run the version's own ``selfcheck`` with its own interpreter; empty when it passed, else what failed."""
    python = folder / ".venv" / "bin" / "python"
    try:
        done = subprocess.run(  # noqa: S603 - the version's own interpreter and a fixed module
            [str(python), "-m", "owlbear_delivery_next", "selfcheck"], cwd=folder, capture_output=True, text=True,
            check=False, timeout=CHECK,
        )  # fmt: skip
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"it could not run: {exc}"
    return "" if done.returncode == 0 else (done.stdout + done.stderr).strip()[-600:] or f"exit {done.returncode}"


def remove(folder: Path) -> None:
    """Remove an installed version's worktree and folder, if there is one."""
    with contextlib.suppress(VersionError):
        _git("-C", str(local_home.root() / REPO), "worktree", "remove", "--force", str(folder))
    shutil.rmtree(folder, ignore_errors=True)
    with contextlib.suppress(VersionError):
        _git("-C", str(local_home.root() / REPO), "worktree", "prune")


def prune() -> list[str]:
    """Remove each version two newer ones were active after, unless a live lease holds it (§3); their tags."""
    folder = local_home.root() / local_home.VERSIONS
    current = (local_home.root() / local_home.RUNTIME).resolve()
    installed = {p: n for p in folder.glob("v*") if p.is_dir() and (n := number(p.name)) is not None}
    active = [n for p, n in installed.items() if (p / ACTIVATED).exists()]
    removed = []
    for path, found in sorted(installed.items(), key=lambda item: item[1]):
        if path.resolve() == current or sum(n > found for n in active) < 2 or leases.held(path):  # noqa: PLR2004
            continue
        retired = path.with_name(f".{path.name}-removing")  # a process starting from it from now on finds nothing
        path.rename(retired)
        if leases.held(retired):  # a lease taken between the look and the rename keeps it
            retired.rename(path)
            continue
        remove(retired)
        removed.append(path.name)
    return removed


def legacy() -> list[Path]:
    """The runtime folders the first update put away; the owner removes them (§3)."""
    return sorted(p for p in (local_home.root() / local_home.VERSIONS).glob("legacy-*") if p.is_dir())


def running() -> str:
    """The installed version the alias names, without asking git; empty for a runtime that is no such version."""
    runtime = local_home.root() / local_home.RUNTIME
    return runtime.resolve().name if runtime.is_symlink() and number(runtime.resolve().name) else ""


def report(say: Callable[[str], None], *, prepare: bool = False) -> int:
    """``owlbear versions``: the running version and the next one; with *prepare*, that one installed and checked."""
    tag, commit = active()
    say(f"running: {tag or 'no installed version'} at {commit[:12] or 'an unknown commit'}")
    try:
        choice = target()
    except (VersionError, registry.RegistryError) as exc:
        say(f"the versions could not be read: {exc}")
        return 1
    for note in choice.notes if choice else ():
        say(f"  {note}")
    if choice is None:
        say("up to date: no newer version of this machine's channel")
        return 0
    if not choice.tag:
        say("no version to take now")
        return 0
    say(f"next: {choice.tag} at {choice.commit[:12]}")
    if not prepare:
        return 0
    try:
        folder = install(choice)
    except VersionError as exc:
        say(str(exc))
        return 1
    say(f"{choice.tag} is installed and checked in {folder}; nothing switched to it")
    return 0
