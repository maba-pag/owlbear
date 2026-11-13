"""A check's preparation and outstanding cleanup, stored beside its setup patch."""

import hashlib
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from owlbear_delivery_next.change_contracts.preparation import LIVE, Preparation
from owlbear_delivery_next.local_system.storage_io import atomic_write

if TYPE_CHECKING:
    from datetime import datetime
    from pathlib import Path

    from owlbear_delivery_next.change_contracts.models import Change
    from owlbear_delivery_next.state_store.store import Store


class Prepared(BaseModel):
    """A check's chosen preparation, retained setup patch and current cleanup obligation."""

    model_config = ConfigDict(extra="forbid")

    check: str
    option: Preparation
    reason: str = ""
    paths: list[str] = Field(default_factory=list)
    snapshot: str = ""
    digest: str = ""
    applied: str = ""
    ready: bool = False
    open: bool = False
    home: str = ""
    trial: bool = False  # owns a temporary proof or capture checkout until cleanup and disposal finish
    snapshot_from: str = ""  # the check owns the frozen snapshot; a before copy borrows its command environment
    snapshot_only: bool = False  # no environment cleanup is owed; only snapshot/setup cleanup remains


def folder(store: Store, slug: str) -> Path:
    """The check preparation records and setup patches for one Change."""
    return store.root / "changes" / slug / "prepare"


def file(store: Store, slug: str, check_id: str, suffix: str) -> Path:
    """One check's record or binary setup patch."""
    return folder(store, slug) / f"{hashlib.sha256(check_id.encode()).hexdigest()[:16]}{suffix}"


def read(store: Store, slug: str, check_id: str) -> Prepared | None:
    """The preparation the check last chose, if any."""
    path = file(store, slug, check_id, ".json")
    return Prepared.model_validate_json(path.read_text()) if path.is_file() else None


def records(store: Store, slug: str) -> list[Prepared]:
    """All preparation records, including cleanup obligations left by an interrupted runner."""
    at = folder(store, slug)
    return [Prepared.model_validate_json(p.read_text()) for p in sorted(at.glob("*.json"))] if at.is_dir() else []


def left(store: Store, c: Change) -> list[Prepared]:
    """Cleanup or trial disposal still owed after the owning check environment ended."""
    current = c.env.check if c.env else None
    return [r for r in records(store, c.slug) if (r.open or (r.trial and r.home)) and r.check != current]


def cleanup_records(store: Store, c: Change, now: datetime) -> list[Prepared]:
    """Ordinary cleanup and disposal are immediate; failed trial cleanup keeps its retry deadline."""
    wake = c.outcome.wake_at if c.outcome else None
    pending = left(store, c)
    borrowed = {r.snapshot_from for r in pending if r.open and r.snapshot_from}
    return [
        r for r in pending if r.check not in borrowed and (not r.trial or not r.open or wake is None or wake <= now)
    ]


def cleanup_record(store: Store, slug: str, rec: Prepared) -> Prepared:
    """Supply the borrowed snapshot to commands without transferring deletion ownership."""
    if not rec.snapshot_from:
        return rec
    source = read(store, slug, rec.snapshot_from)
    if source is None:
        msg = f"the borrowed snapshot's owner {rec.snapshot_from} is missing in {folder(store, slug)}"
        raise ValueError(msg)
    return rec.model_copy(update={"snapshot": source.snapshot, "digest": source.digest})


def snapshot_owner(store: Store, slug: str, rec: Prepared) -> Prepared:
    """Keep the one frozen source active without claiming a second environment was seeded there."""
    if not rec.snapshot_from:
        return rec
    source = read(store, slug, rec.snapshot_from)
    if source is None:
        msg = f"the snapshot owner {rec.snapshot_from} is missing in {folder(store, slug)}"
        raise ValueError(msg)
    source.open, source.snapshot_only = source.option.kind in LIVE, True
    write(store, slug, source)
    return source


def write(store: Store, slug: str, rec: Prepared, patch: bytes | None = None) -> None:
    """Keep cleanup owed before any command runs; a setup patch is replaced before its record."""
    folder(store, slug).mkdir(mode=0o700, parents=True, exist_ok=True)
    if patch is not None:
        path = file(store, slug, rec.check, ".patch")
        path.with_suffix(".tmp").write_bytes(patch)
        path.with_suffix(".tmp").replace(path)
    atomic_write(file(store, slug, rec.check, ".json"), rec.model_dump_json())
