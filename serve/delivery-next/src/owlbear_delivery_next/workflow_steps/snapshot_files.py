"""A test copy's frozen snapshot on disk: plain files only, its digest, its deletion, and the option's commands."""

from __future__ import annotations

import hashlib
import shlex
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.workflow_steps import check

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from owlbear_delivery_next.workflow_steps.prepare import Prepared


def plain(folder: Path) -> str:
    """Why the snapshot is not only plain files and folders inside itself; masking must write nothing beyond it."""
    top = folder.resolve()
    for p in folder.rglob("*"):
        file = p.is_file(follow_symlinks=False)
        if (
            not (file or p.is_dir(follow_symlinks=False))
            or (file and p.stat().st_nlink > 1)
            or not p.resolve().is_relative_to(top)
        ):
            return f"the snapshot holds {p.relative_to(folder)}, a link or special file"
    return ""


def digest(folder: Path) -> str:
    """The snapshot's content, read without following a link."""
    h = hashlib.sha256()
    for p in sorted(folder.rglob("*")):
        h.update(str(p.relative_to(folder)).encode() + b"\0")
        if p.is_file(follow_symlinks=False):
            h.update(hashlib.sha256(p.read_bytes()).digest())
        elif not p.is_dir(follow_symlinks=False):
            h.update(b"\0not a plain file")  # never read through a link
    return h.hexdigest()


def command(rec: Prepared, name: str, root: Path, log: Callable[[dict[str, Any]], None], env: Mapping[str, str]) -> str:
    """Run the option's *name* command in *root*; a note if it failed, else empty."""
    cmd = getattr(rec.option, name)
    return f"the {name} command {note}" if cmd and (note := check.run(shlex.split(cmd), root, log, env)) else ""


def gone(path: str) -> bool:
    """Delete a snapshot folder; whether it is gone."""
    if path:
        shutil.rmtree(path, ignore_errors=True)
    return not path or not Path(path).exists(follow_symlinks=False)
