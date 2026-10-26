"""The machine settings in force (D-01M5MZKEPPVMFC9HK795MMG91B): this machine's own value, else Global's, else unset.

Code ships no defaults (the owner, 2026-10-23): an unset setting is an error on the Settings page, and what needs it
does not run: no update by itself without its switches and channel, no automatic curation without its trigger, no
agent session without the machine's total.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from pydantic import Field

from owlbear_delivery_next.change_contracts.models import Record
from owlbear_delivery_next.local_system import data_repo
from owlbear_delivery_next.settings.config import GlobalLayer, MachineValues
from owlbear_delivery_next.state_store import registry
from owlbear_delivery_next.state_store.store import StoreError, read_layer

if TYPE_CHECKING:
    from owlbear_delivery_next.local_system.data_repo import DataRepo

FIELDS: tuple[str, ...] = tuple(MachineValues.model_fields)
BASE: MachineValues | None = None  # a layer under Global; empty in production (no code defaults), tests set one


class Resolved(Record):
    """Each machine setting in force, ``None`` where unset; where it came from; what is unset; Global's own."""

    channel: Literal["minor", "major"] | None = None
    update_when_idle: bool | None = None
    update_while_paused: bool | None = None
    curate_after_merge: Literal["off", "on", "paused"] | None = None
    curate_when_idle: Literal["off", "on", "paused"] | None = None
    sessions: int | None = None
    spotter_budget: int | None = None
    retro_budget: int | None = None
    retro_verbose_cap: int | None = None
    retro_after_change: Literal["off", "on", "paused"] | None = None
    retro_when_idle: Literal["off", "on", "paused"] | None = None
    enrolled_chats: list[str] | None = None
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
        return None, "no shared repository is set up, so there are no global machine settings"
    try:
        return read_layer(shared.global_path, GlobalLayer).machine, ""
    except StoreError as exc:
        return None, f"the global settings are unreadable: {exc}"


def current(local: registry.Settings | None = None) -> Resolved:
    """The machine settings in force now; this machine's from ``machine.json`` unless given."""
    try:
        glob, notice = shared_values(data_repo.locate())
    except data_repo.DataRepoError as exc:
        glob, notice = None, str(exc)
    return resolve(registry.load().settings if local is None else local, glob, notice)
