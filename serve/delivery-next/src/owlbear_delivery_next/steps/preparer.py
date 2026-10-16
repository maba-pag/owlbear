"""TD-107: a preparer session's start, and what each of its endings puts back besides its uncommitted edits.

The start records HEAD and the ignored files the declared options' setup globs name, and backs those files up. Every
ending (an accepted recipe, a rejected one, a runner that died) resets a HEAD the preparer moved back to that start,
deletes the ignored setup files it created and restores the ones it changed. The worktree is the Change's own, so
resetting to the recorded start undoes only the preparer's commits.
"""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next import preparation
from owlbear_delivery_next.steps import worktree

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

BACKUP = "ignored"  # the start's ignored setup files, beside the session marker


def ignored(root: Path, globs: Sequence[str]) -> list[str]:
    """The ignored files under *globs*, links included, each as Git names it."""
    if not globs:
        return []
    spec = [f":(glob){g}" for g in globs]
    out = worktree.git(root, "ls-files", "-z", "--others", "--ignored", "--exclude-standard", "--", *spec)
    return sorted(p for p in out.split("\0") if p and preparation.setup(p, globs))


def start(root: Path, folder: Path, globs: Sequence[str]) -> dict[str, Any]:
    """Record HEAD and back the ignored setup files up into *folder*; what the session marker keeps."""
    found, backup = ignored(root, globs), folder / BACKUP
    shutil.rmtree(backup, ignore_errors=True)
    for p in found:
        (backup / p).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / p, backup / p, follow_symlinks=False)
    return {"head": worktree.head(root), "ignored": found, "globs": list(globs)}


def _same(kept: Path, now: Path) -> bool:
    if kept.is_symlink() or now.is_symlink():
        return kept.is_symlink() and now.is_symlink() and kept.readlink() == now.readlink()
    return now.is_file() and kept.read_bytes() == now.read_bytes()


def end(root: Path, folder: Path, started: dict[str, Any]) -> dict[str, Any]:
    """Reset a moved HEAD to the start and put the ignored setup files back; what was undone, for the log."""
    done: dict[str, Any] = {}
    if (head := started.get("head")) and (now := worktree.head(root)) != head:
        worktree.git(root, "reset", "--quiet", "--soft", head)  # its commits' edits are then edits, discarded after
        done["reset"] = now
    before, backup = set(started.get("ignored", [])), folder / BACKUP
    made = [p for p in ignored(root, started.get("globs", [])) if p not in before]
    for p in made:
        (root / p).unlink()
    restored = []
    for p in sorted(before):
        if (backup / p).exists(follow_symlinks=False) and not _same(backup / p, root / p):
            (root / p).unlink(missing_ok=True)
            (root / p).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup / p, root / p, follow_symlinks=False)
            restored.append(p)
    shutil.rmtree(backup, ignore_errors=True)
    return done | ({"removed": made[:20]} if made else {}) | ({"restored": restored[:20]} if restored else {})
