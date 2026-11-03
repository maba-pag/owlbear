"""The record of an accepted curation run's apply (#875): while it exists, nothing of the run is published.

`Tree.accept` writes it before the first of the run's files is copied into the shared checkout and clears it once the
set is committed. A stop in between leaves it: no push of the checkout runs, no memory entry or project folder moves,
and the next start, or the next curation run, finishes the set from it. It sits in the checkout's Git folder beside
the repository lock, so no commit or push can carry it; the memory server finds it there by its name.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING

from owlbear_delivery_next.local_system.storage_io import atomic_write

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear_delivery_next.local_system.data_repo import DataRepo


def digest(raw: bytes | None) -> str | None:
    """The seed's identity in a record: the SHA-256 of its bytes; None for a path the seed did not hold."""
    return None if raw is None else hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class Step:
    """One path of the set: its seed (`digest`), its text after the run (None: absent), and whether it is committed.

    `removed` says the run's own commits removed it, so its deletion is committed; one they did not make stays
    uncommitted.
    """

    seed: str | None
    target: str | None
    removed: bool


@dataclass(frozen=True)
class Apply:
    """The folder whose run is being applied, and each path it touches by its repository-relative name."""

    folder: str
    steps: dict[str, Step]


def where(repo: DataRepo, until: float | None = None) -> Path:
    """The record's file, beside the repository lock; `DataRepoError` when Git names no Git folder for the checkout.

    *until* is the caller's deadline (monotonic): a push asks within its own.
    """
    return repo._lock_file(until).parent / "owlbear-curation-apply.json"  # noqa: SLF001 - found as the lock is


def write(repo: DataRepo, apply: Apply) -> None:
    """Keep *apply*, whole or not at all."""
    atomic_write(where(repo), json.dumps(asdict(apply), indent=2, sort_keys=True))


def read(repo: DataRepo, until: float | None = None) -> Apply | None:
    """The kept record; None when there is none. Written atomically, so it is whole; an unreadable one raises."""
    path = where(repo, until)
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return Apply(data["folder"], {rel: Step(**step) for rel, step in data["steps"].items()})


def clear(repo: DataRepo) -> None:
    """Forget the record: the set it names is committed."""
    where(repo).unlink(missing_ok=True)


def cut_short(repo: DataRepo, until: float | None = None) -> str:
    """Why the checkout's work may not leave it or move: an apply a stop cut short; nothing when there is none."""
    if (apply := read(repo, until)) is None:
        return ""
    return (
        f"the memory curation of {apply.folder} was cut short while its files were copied in; OwlBear finishes it at "
        f"its next start, or before its next curation run (record: {where(repo)})"
    )
