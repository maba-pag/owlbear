"""The machine settings in force (D-01M5MZKEPPVMFC9HK795MMG91B): this machine's own value, else Global's, else unset.

Code ships no defaults (the owner, 2026-10-23): an unset setting is an error on the Settings page, and while one is
unset or can't be read no project's work starts (#808). What needs it does not run either: no update by itself without
its switches and channel, no automatic curation without its trigger, no agent session without the machine's total.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from pydantic import Field

from owlbear_delivery_next.git.command_failure import failure
from owlbear_delivery_next.local_system import data_place, data_repo, local_home
from owlbear_delivery_next.settings.config import GlobalLayer, MachineValues
from owlbear_delivery_next.state_store import registry
from owlbear_delivery_next.state_store.store import StoreError, read_layer

if TYPE_CHECKING:
    from owlbear_delivery_next.local_system.data_repo import DataRepo

FIELDS: tuple[str, ...] = tuple(MachineValues.model_fields)
NO_SHARED = "no shared repository is set up, so there are no global machine settings"
BASE: MachineValues | None = None  # a layer under Global; empty in production (no code defaults), tests set one
type Inputs = tuple[bytes | str | None, ...]


def _input(path: Path) -> bytes | str | None:
    try:
        return path.read_bytes()
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as exc:
        return failure(exc)


def update_check_inputs() -> Inputs:
    """The update snapshot's inputs, without resolving settings or probing Git; read errors are distinct tokens."""
    home, view = local_home.root(), os.environ.get(data_repo.VIEW)
    record: dict[str, str] | str | None = None
    try:
        if view is not None:
            root = Path(view) if view else None
        else:
            record = data_place.stored()
            named = record.get("repository") if record else None
            root = data_place.default() if record is None else Path(named).expanduser().resolve() if named else None
    except (OSError, ValueError, RuntimeError) as exc:
        root, record = None, failure(exc)
    return (
        str(home),
        view,
        _input(home / registry.MACHINE),
        repr(record),
        str(root) if root else None,
        _input(root / data_repo.CONFIG) if root else None,
        ("directory" if (root / ".git").is_dir() else _input(root / ".git")) if root and view is None else None,
        _input(root / ".git/config") if root and view is None else None,
        _input(Path.home() / ".gitconfig") if view is None else None,
        BASE.model_dump_json() if BASE is not None else None,
    )


class Resolved(MachineValues):
    """Each machine setting in force, ``None`` where unset; where it came from; what is unset; Global's own."""

    sources: dict[str, Literal["machine", "global", "default"]] = Field(default_factory=dict)
    missing: list[str] = Field(default_factory=list)
    shared: dict[str, Any] = Field(default_factory=dict)  # Global's values, for the page's "inherit (…)"
    notice: str = ""  # why Global's could not be read


def resolve(local: MachineValues, glob: MachineValues | None, notice: str = "") -> Resolved:
    """Each field on its own: this machine's, else Global's, else unset."""
    layers = [("machine", local), ("global", glob or MachineValues())]
    if BASE is not None:
        layers.append(("default", BASE))
    values: dict[str, Any] = {}
    sources: dict[str, Any] = {}
    for name in FIELDS:
        source, value = next(((s, v) for s, layer in layers if (v := getattr(layer, name)) is not None), (None, None))
        values[name] = value
        if source:
            sources[name] = source
    missing = [n for n in FIELDS if values[n] is None]
    shared = (glob or MachineValues()).model_dump()
    return Resolved(**values, sources=sources, missing=missing, shared=shared, notice=notice)


def shared_values(shared: DataRepo | None) -> tuple[MachineValues | None, str]:
    """Global's machine settings, and why they could not be read; none without a shared repository."""
    if shared is None:
        return None, NO_SHARED
    try:
        return read_layer(shared.global_path, GlobalLayer).machine, ""
    except StoreError as exc:
        return None, f"the global settings are unreadable: {failure(exc)}"


def current(local: registry.Settings | None = None) -> Resolved:
    """The machine settings in force now; this machine's from ``machine.json`` unless given."""
    try:
        glob, notice = shared_values(data_repo.locate())
    except data_repo.DataRepoError as exc:
        glob, notice = None, failure(exc)
    return resolve(registry.load().settings if local is None else local, glob, notice)
