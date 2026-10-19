"""A test review's shares (TD-373): the test files at the pinned commit, by package, in whole-file shares."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts.curation_records import Share
from owlbear_delivery_next.change_contracts.curation_tools import is_test
from owlbear_delivery_next.change_flow.worktree import GIT, git

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

SHARE = 5_000  # lines a share holds at most, unless one file alone is longer; a heuristic, not a context guarantee
MANIFESTS = frozenset({"pyproject.toml", "package.json", "Cargo.toml", "go.mod"})  # a package's root


@dataclass(frozen=True)
class Package:
    """One package's test files and their lines, in path order."""

    path: str
    files: dict[str, int] = field(default_factory=dict)

    @property
    def lines(self) -> int:
        """Its test lines."""
        return sum(self.files.values())


def packages(repo: Path, commit: str) -> list[Package]:
    """The packages with test files at *commit*: each file under the deepest folder holding a manifest, else ``.``."""
    blobs: dict[str, str] = {}
    for entry in git(repo, "ls-tree", "-r", "-z", commit).split("\0"):
        meta, _, path = entry.partition("\t")
        if meta.split(" ")[1:2] == ["blob"]:
            blobs[path] = meta.split(" ")[2]
    roots = sorted({str(PurePosixPath(p).parent) for p in blobs if PurePosixPath(p).name in MANIFESTS} | {"."})
    roots.sort(key=lambda r: (r == ".", -len(r)))  # the deepest first; the repository's root last
    tests = sorted(p for p in blobs if is_test(p))
    counted = _lines(repo, [blobs[p] for p in tests])
    found: dict[str, dict[str, int]] = {}
    for path, lines in zip(tests, counted, strict=True):
        root = next(r for r in roots if r == "." or path.startswith(f"{r}/"))
        found.setdefault(root, {})[path] = lines
    return [Package(root, files) for root, files in sorted(found.items())]


def _lines(repo: Path, shas: Sequence[str]) -> list[int]:
    """Each blob's lines, read in one ``git cat-file --batch``."""
    out = subprocess.run(  # noqa: S603 - fixed Git executable and argument vector.
        [GIT, "cat-file", "--batch"], input="".join(f"{s}\n" for s in shas).encode(), cwd=repo, capture_output=True,
        check=True, timeout=60,
    ).stdout  # fmt: skip
    lines, at = [], 0
    for _ in shas:
        end = out.index(b"\n", at)
        size = int(out[at:end].split()[2])
        blob = out[end + 1 : end + 1 + size]
        lines.append(blob.count(b"\n") + (not blob.endswith(b"\n") and bool(blob)))
        at = end + 2 + size
    return lines


def split(chosen: Sequence[Package]) -> list[Share]:
    """Whole files in path order, a package's files together, into shares of up to ``SHARE`` lines."""
    shares = []
    for package in chosen:
        paths, total = list[str](), 0
        for path, lines in package.files.items():
            if paths and total + lines > SHARE:
                shares.append(Share(paths=paths, lines=total))
                paths, total = [], 0
            paths.append(path)
            total += lines
        if paths:
            shares.append(Share(paths=paths, lines=total))
    return shares
