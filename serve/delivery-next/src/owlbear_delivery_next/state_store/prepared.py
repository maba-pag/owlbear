"""A check's preparation and outstanding cleanup, stored beside its setup patch."""

import hashlib
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from owlbear_delivery_next.change_contracts.preparation import Preparation
from owlbear_delivery_next.local_system.storage_io import atomic_write

if TYPE_CHECKING:
    from pathlib import Path

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


def write(store: Store, slug: str, rec: Prepared, patch: bytes | None = None) -> None:
    """Keep cleanup owed before any command runs; a setup patch is replaced before its record."""
    folder(store, slug).mkdir(mode=0o700, parents=True, exist_ok=True)
    if patch is not None:
        path = file(store, slug, rec.check, ".patch")
        path.with_suffix(".tmp").write_bytes(patch)
        path.with_suffix(".tmp").replace(path)
    atomic_write(file(store, slug, rec.check, ".json"), rec.model_dump_json())
