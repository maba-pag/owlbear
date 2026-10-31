"""Why no work may start for a project: a setting it reads is unset or can't be read (D-01M61SBWK4VE4MNTD35TR0VPS8).

This machine's settings count for every project, the three update-check intervals included. Every call reads the
settings fresh, so setting the value lifts the block at the next check; work already running goes on
(D-01M64WBZ5D45N6PV2SGZGSX232).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from owlbear_delivery_next.local_system import local_home
from owlbear_delivery_next.settings.config import SettingsUnset
from owlbear_delivery_next.state_store import machine_settings, registry
from owlbear_delivery_next.state_store.database import StoreError
from owlbear_delivery_next.state_store.layers import layered
from owlbear_delivery_next.state_store.store import MACHINE_SETTINGS

if TYPE_CHECKING:
    from owlbear_delivery_next.local_system.data_repo import DataRepo
    from owlbear_delivery_next.settings.config import Settings
    from owlbear_delivery_next.state_store.store import Store

UNREADABLE = "settings can't be read: "


@dataclass(frozen=True)
class Block:
    """The unset keys, or why the settings can't be read; falsy when work may start."""

    keys: tuple[str, ...] = ()
    reason: str = ""

    def __bool__(self) -> bool:
        return bool(self.keys or self.reason)

    def __add__(self, other: Block) -> Block:
        return Block((*self.keys, *other.keys), "; ".join(r for r in (self.reason, other.reason) if r))

    def text(self) -> str:
        """What the owner reads: the unreadable reason first, else the unset keys; empty when not blocked."""
        if self.reason:
            return f"{UNREADABLE}{self.reason}"
        return str(SettingsUnset(list(self.keys))) if self.keys else ""


def outside(shared: DataRepo) -> Settings:
    """The settings outside any project: this machine's layer over the global one; ``StoreError`` when unreadable."""
    return layered(shared.global_path, None, local_home.root() / MACHINE_SETTINGS)


def machine() -> Block:
    """This machine's settings in force; "no shared repository" is no block (D-01M5MZKEPPVMFC9HK795MMG91B)."""
    try:
        resolved = machine_settings.current()
    except registry.RegistryError as exc:
        return Block(reason=str(exc))
    notice = "" if resolved.notice == machine_settings.NO_SHARED else resolved.notice
    return Block(tuple(f"machine.{k}" for k in resolved.missing), notice)


def of_settings(settings: Settings, here: Block | None = None) -> Block:
    """Resolved settings' unset keys, with this machine's (*here*, read now unless given)."""
    return Block(tuple(settings.missing)) + (machine() if here is None else here)


def of_store(store: Store, here: Block | None = None) -> Block:
    """A registered project's block."""
    try:
        own = Block(tuple(store.settings().missing))
    except StoreError as exc:
        own = Block(reason=str(exc))
    return own + (machine() if here is None else here)


def of_folder(shared: DataRepo, folder: str, here: Block | None = None) -> Block:
    """A shared folder's block: Global, the folder's project layer and this machine's; no registration needed."""
    try:
        settings = layered(shared.global_path, shared.project_path(folder), local_home.root() / MACHINE_SETTINGS)
        own = Block(tuple(settings.missing))
    except StoreError as exc:
        own = Block(reason=str(exc))
    return own + (machine() if here is None else here)
