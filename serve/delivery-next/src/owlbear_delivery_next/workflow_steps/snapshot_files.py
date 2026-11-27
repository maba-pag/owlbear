"""A test copy's frozen snapshot on disk: plain files only, its digest, its deletion, and the option's commands."""

from __future__ import annotations

import hashlib
import os
import shlex
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.change_flow import worktree
from owlbear_delivery_next.workflow_steps import check

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from owlbear_delivery_next.workflow_steps.prepare import Prepared


def snapshots() -> Path:
    """The snapshot folder beside Delivery's worktrees, outside every repository."""
    return worktree.data_root().parent / "snapshots"


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


def _live_command(
    cmd: str, source: Path, root: Path, log: Callable[[dict[str, Any]], None], env: Mapping[str, str]
) -> str:
    argv = shlex.split(cmd)
    search = [root / p for p in env.get("PATH", os.defpath).split(os.pathsep)]
    path_env = os.pathsep.join(str(p) for p in search if not p.resolve().is_relative_to(source))
    for i, arg in enumerate(argv):
        opt, sep, word = arg.partition("=") if arg.startswith("-") and "=" in arg else ("", "", arg)
        path = Path(word)
        if path.is_absolute() and path.is_relative_to(source):
            path = root / path.relative_to(source)
            argv[i] = f"{opt}{sep}{path}"
        resolved = (root / path).resolve()
        if resolved.is_relative_to(root):
            continue
        if i == 0 and (tool := shutil.which(path.name, path=path_env)) and Path(tool).resolve() == resolved:
            continue
        return f"names {word}, outside the committed project tree"
    return check.run(argv, root, log, dict(env, PATH=path_env))


def copy_live(
    rec: Prepared, source: Path, folder: Path, log: Callable[[dict[str, Any]], None], env: Mapping[str, str]
) -> str:
    """Run export and masking from separate copies of the same commit, sharing only the data snapshot."""
    source = source.resolve()
    try:
        tree = worktree.git(source, "rev-parse", "HEAD^{tree}").strip()
        for name, cmd in (("export", rec.option.export), ("masking", rec.option.masking)):
            if not cmd:
                continue
            with tempfile.TemporaryDirectory(prefix="scripts-", dir=folder.parent) as temp:
                base = Path(temp).resolve()
                archive, root = base / "tree.tar", base / "tree"
                worktree.git(source, "archive", "--format=tar", f"--output={archive}", tree)
                with tarfile.open(archive) as material:
                    material.extractall(root, filter="data")
                archive.unlink()
                if note := _live_command(cmd, source, root, log, env):
                    return f"the {name} command {note}"
                if note := plain(folder):
                    return note
    except (OSError, subprocess.SubprocessError, tarfile.TarError) as exc:
        return f"the committed snapshot scripts could not run: {worktree.failure(exc)}"
    return ""


def gone(path: str) -> bool:
    """Delete a snapshot folder; whether it is gone."""
    if path:
        shutil.rmtree(path, ignore_errors=True)
    return not path or not Path(path).exists(follow_symlinks=False)
