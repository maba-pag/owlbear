"""Read immutable Git trees without consulting the index."""

from __future__ import annotations

import asyncio
import shutil
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


async def _git(repo: Path, args: tuple[str, ...]) -> str:
    proc = await asyncio.create_subprocess_exec(
        shutil.which("git") or "git",
        *args,
        cwd=repo,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()
    if proc.returncode:
        msg = f"git {' '.join(args)} in {repo} exited {proc.returncode}: {err.decode(errors='replace')}"
        raise RuntimeError(msg)
    return out.decode("utf-8", errors="replace")


def git(repo: Path, *args: str) -> str:
    """Run Git with an argument vector; report its full error on failure."""
    return asyncio.run(_git(repo, args))


def entries(repo: Path, commit: str) -> dict[str, tuple[str, str]]:
    """Tracked blobs at *commit*, by path with their mode and object id, including symbolic links."""
    result = {}
    for record in git(repo, "ls-tree", "-r", "-z", commit).split("\0"):
        if record:
            meta, path = record.split("\t", 1)
            mode, kind, oid = meta.split()
            if kind == "blob":
                result[path] = mode, oid
    return result


def files(repo: Path, commit: str) -> dict[str, str]:
    """Regular tracked files at *commit*, by path and blob id; links and submodules are not code."""
    return {path: oid for path, (mode, oid) in entries(repo, commit).items() if mode in {"100644", "100755"}}


def blob(repo: Path, oid: str) -> str:
    """Read a blob verbatim, preserving line endings and trailing whitespace."""
    return git(repo, "cat-file", "blob", oid)
