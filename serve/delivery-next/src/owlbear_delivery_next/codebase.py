"""The identity of the Delivery code a process loaded: a host and the runners it starts must share it (finding 10)."""

from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).parent
UNREADABLE = "unreadable: "
SHIPPED = (
    "**/*.py",
    "design_pack.json",
    "agents/*.md",
    "golden/*.html",
    "golden/*.json",
    "skills/**/*.md",
    "worker_skills/**/*.md",
    "worker_skills/*-LICENSE",
    "web/**/*.html",
    "web/**/*.css",
    "web/**/*.mjs",
)


def shipped(root: Path = ROOT) -> list[Path]:
    """The package's modules and data files; caches, editor backups and other incidental files are not code."""
    found = {p for pattern in SHIPPED for p in root.glob(pattern) if not p.is_dir()}
    return sorted(p for p in found if not any(part.startswith(".") for part in p.relative_to(root).parts))


def identity(root: Path = ROOT) -> str:
    """sha256 over the shipped files by relative path and content; ``unreadable: <path>`` when one cannot be read."""
    digest = hashlib.sha256()
    for path in shipped(root):
        relative = path.relative_to(root).as_posix()
        try:
            data = path.read_bytes()
        except OSError:
            return f"{UNREADABLE}{relative}"
        digest.update(f"{relative}\0".encode())
        digest.update(hashlib.sha256(data).digest())
    return digest.hexdigest()


CURRENT = identity()  # at import, when this process loads its modules
