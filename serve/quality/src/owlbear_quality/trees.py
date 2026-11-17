"""Read immutable Git trees without consulting the index, through the caller's Git runner."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    type Git = Callable[[Path, list[str]], str]


def entries(run: Git, repo: Path, commit: str) -> dict[str, tuple[str, str]]:
    """Tracked blobs at *commit*, by path with their mode and object id, including symbolic links."""
    result = {}
    for record in run(repo, ["ls-tree", "-r", "-z", commit]).split("\0"):
        if record:
            meta, path = record.split("\t", 1)
            mode, kind, oid = meta.split()
            if kind == "blob":
                result[path] = mode, oid
    return result


def files(run: Git, repo: Path, commit: str) -> dict[str, str]:
    """Regular tracked files at *commit*, by path and blob id; links and submodules are not code."""
    return {path: oid for path, (mode, oid) in entries(run, repo, commit).items() if mode in {"100644", "100755"}}


def blob(run: Git, repo: Path, oid: str) -> str:
    """Read a blob verbatim, preserving line endings and trailing whitespace."""
    return run(repo, ["cat-file", "blob", oid])
