"""The Change's read-only worktree ``<slug>.ro`` beside its own under the data root (folder trust).

One per Change, so a VS Code window opened on it is reused: before each read-only session (each judge in the window,
each SDK judge batch) it is reset to the judged commit, which discards whatever an earlier session wrote. Refs a
session creates or moves in the shared repository void its result. It goes when the Change's own worktree goes.
Accepted limit: a window turn that survives an unconfirmed cancel could still write here after the host cleared its
mark; the next preparation resets that.
"""

from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from owlbear_delivery_next.steps import ro_installs, worktree
from owlbear_delivery_next.storage_io import atomic_write
from owlbear_delivery_next.store import StoreError, git_common_dir

if TYPE_CHECKING:
    from collections.abc import Collection

    from owlbear_delivery_next.store import Store

NAME = re.compile(r"[a-z0-9][a-z0-9_-]*\.ro")  # a Change slug never holds a dot
OWN = "refs/heads/owlbear/"  # Delivery's Change branches: concurrent runners move them
LIVE = "read-only.live"  # in the Change's store folder from a session's start until its processes are confirmed gone


@dataclass(frozen=True)
class Copy:
    """The read-only worktree of *source*'s repository, and the repository's refs and shared Git settings before."""

    source: Path
    path: Path
    refs: dict[str, str]
    shared: frozenset[str] = frozenset()


def path(source: Path, slug: str) -> Path:
    """Where the Change's read-only worktree belongs: beside the Change worktree under the data root."""
    return worktree.path_for(git_common_dir(source), f"{slug}.ro")


def prepare(source: Path, store: Store, slug: str) -> Copy | str:
    """The read-only worktree detached at *source*'s HEAD, created or reset; else why it was refused, untouched.

    A mark in the Change's store folder means the last session's processes may still use it.
    """
    try:
        if left := live(store.root / "changes" / slug):
            return f"the processes of the last read-only session in {left} are not confirmed gone"
        at, commit = path(source, slug), worktree.head(source)
        if at.exists() or at.is_symlink():
            if problem := custody(source, at, owned(store)):
                return problem
            worktree.git(at, "checkout", "--quiet", "--detach", "--force", commit)
            worktree.git(at, "clean", "-ffdq")  # ignored files stay: installed dependencies serve the next session
        else:
            ro_installs.forget(store.root / "changes" / slug)
            at.parent.mkdir(parents=True, exist_ok=True)
            worktree.git(source, "worktree", "prune")
            worktree.git(source, "worktree", "add", "--quiet", "--detach", str(at), commit)
        return Copy(source, at, _refs(source), _shared(source))
    except (OSError, subprocess.SubprocessError) as exc:
        return f"the read-only worktree could not be prepared: {_why(exc)}"


def live(folder: Path) -> Path | None:
    """The read-only worktree whose last session's processes are not confirmed gone, if any."""
    try:
        return Path((folder / LIVE).read_text(encoding="utf-8").strip())
    except FileNotFoundError:
        return None


def begin(folder: Path, at: Path) -> None:
    """Mark *at* as used by a session until its processes are confirmed gone."""
    folder.mkdir(parents=True, exist_ok=True)
    atomic_write(folder / LIVE, str(at))


def settled(folder: Path) -> None:
    """Every process of the last read-only session is confirmed gone."""
    (folder / LIVE).unlink(missing_ok=True)


def _why(exc: BaseException) -> str:
    return str(getattr(exc, "stderr", "") or exc).strip()[:300]


def _refs(cwd: Path) -> dict[str, str]:
    out = worktree.git(cwd, "for-each-ref", "--format=%(refname) %(objectname)", "refs/heads", "refs/tags")
    return dict(line.split(" ", 1) for line in out.splitlines() if line)


def _shared(cwd: Path) -> frozenset[str]:
    """The shared config entries but ``branch.*``, which pushes write, and a fingerprint of each shared hook."""
    common = git_common_dir(cwd)
    listed = worktree.git(cwd, "config", "--file", str(common / "config"), "--list")
    config = {f"config {line}" for line in listed.splitlines() if line and not line.startswith("branch.")}
    hooks = common / "hooks"
    found = sorted(hooks.iterdir()) if hooks.is_dir() else []
    return frozenset(config | {f"hook {p.name} {hashlib.sha256(p.read_bytes()).hexdigest()[:12]}" for p in found})


def tampered(copy: Copy) -> list[str]:
    """Shared config entries and hooks added, changed or removed since the copy was made (TD-146)."""
    try:
        now = _shared(copy.source)
    except (OSError, subprocess.SubprocessError) as exc:
        return [f"the shared Git config and hooks could not be read ({type(exc).__name__})"]
    return [f"added {e}" for e in sorted(now - copy.shared)] + [f"removed {e}" for e in sorted(copy.shared - now)]


def _listed(cwd: Path) -> list[dict[str, str]]:
    """The repository's worktrees as ``git worktree list --porcelain`` reports them, one mapping each."""
    entries: list[dict[str, str]] = []
    for block in worktree.git(cwd, "worktree", "list", "--porcelain").split("\n\n"):
        fields = dict([*line.split(" ", 1), ""][:2] for line in block.splitlines() if line)
        if "worktree" in fields:
            entries.append(fields)
    return entries


def changed(copy: Copy) -> list[str]:
    """Refs created or moved since the copy was made, except Change branches and branches other worktrees hold."""
    try:
        now = _refs(copy.source)
        held = {e["branch"] for e in _listed(copy.source) if "branch" in e and not _same(e["worktree"], copy.path)}
    except (OSError, subprocess.SubprocessError) as exc:
        return [f"its refs could not be read ({type(exc).__name__})"]
    found = []
    for ref, oid in sorted(now.items()):
        if copy.refs.get(ref) == oid or ref.startswith(OWN) or ref in held:
            continue
        kind = "tag" if ref.startswith("refs/tags/") else "branch"
        name = ref.removeprefix("refs/tags/").removeprefix("refs/heads/")
        found.append(f"{'moved' if ref in copy.refs else 'created'} {kind} {name}")
    return found


def _same(listed: str, path: Path) -> bool:
    return Path(listed).resolve() == path.resolve()


def owned(store: Store) -> list[Path]:
    """The own worktree of every Change the store can read."""
    found = []
    for slug in store.slugs():
        try:
            found.append(store.read(slug).names.worktree)
        except StoreError:
            continue
    return [Path(w) for w in found if w]


def custody(source: Path, at: Path, changes: Collection[Path]) -> str:
    """Why Delivery may not reset or remove *at*; empty when it is a read-only worktree of *source*'s repository.

    Git itself must place *at* as one linked worktree of that repository, with its own administrative folder: never
    *source*'s, the main checkout's or any of the *changes* worktrees. A worktree a session switched to a branch stays
    Delivery's: the reset detaches it again.
    """
    if at.is_symlink():
        return f"{at} is a symlink"
    if not NAME.fullmatch(at.name):
        return f"{at} is not named as a read-only worktree"
    if not at.resolve().is_relative_to(worktree.data_root().resolve()):
        return f"{at} is not under {worktree.data_root()}"
    if any(_same(str(c), at) for c in changes):
        return f"{at} is a Change's own worktree"
    return "" if _linked(source, at) else f"{at} is not a worktree of {source}'s repository"


def _linked(source: Path, at: Path) -> bool:
    """Whether Git places *at* as a linked worktree of *source*'s repository with its own administrative folder."""
    if not (at / ".git").is_file() or (at / ".git").is_symlink():  # else Git would act on a repository above
        return False
    try:
        top, own, common = _dirs(at, "--show-toplevel")
        theirs, repository = _dirs(source)
        back = (own / (own / "gitdir").read_text(encoding="utf-8").strip()).resolve()
    except OSError, subprocess.SubprocessError, ValueError:
        return False
    placed = top == at.resolve() and back == (at / ".git").resolve()
    return placed and common == repository and own.parent == common / "worktrees" and own != theirs


def _dirs(cwd: Path, *first: str) -> list[Path]:
    """The absolute, resolved folders ``git rev-parse`` reports in *cwd*: *first*, the Git folder, the common one."""
    out = worktree.git(cwd, "rev-parse", "--path-format=absolute", *first, "--git-dir", "--git-common-dir")
    return [Path(line).resolve() for line in out.splitlines()]


def remove(source: Path, store: Store, slug: str) -> str:
    """Remove the Change's read-only worktree once custody holds and no session may use it; what kept it, if any."""
    try:
        at, left = path(source, slug), live(store.root / "changes" / slug)
    except (OSError, subprocess.SubprocessError) as exc:
        return f"the read-only worktree of {source} could not be located: {_why(exc)}"
    if not (at.exists() or at.is_symlink()):
        return ""
    if left:
        return f"the processes of the last read-only session in {left} are not confirmed gone"
    if problem := custody(source, at, owned(store)):
        return problem
    try:
        worktree.git(source, "worktree", "remove", "--force", str(at))
    except (OSError, subprocess.SubprocessError) as exc:
        problem = f"git worktree remove failed: {_why(exc)}"
    if at.exists() and not at.is_symlink():
        shutil.rmtree(at, ignore_errors=True)
    return problem or (f"{at} remains after its removal" if at.exists() else "")
