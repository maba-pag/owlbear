"""The chats follower's settings (Improvement design §4, "Where: Chats"): Global's under this machine's, read each pass.

A chat is no project's, so its looks take the Spotter's settings from Global under this machine's, and the enrolled
chats from the machine's settings. Off, unset or unreadable, no chat is read (``machine_host.chats``).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from owlbear_delivery_next.improvement import spotter
from owlbear_delivery_next.local_system import data_repo
from owlbear_delivery_next.settings.config import SettingsUnset
from owlbear_delivery_next.state_store import machine_settings
from owlbear_delivery_next.state_store.store import StoreError
from owlbear_delivery_next.workflow_steps import lookup, watched

CHAT = (
    "a chat has no Change, plan or decisions here: its workspace folder and the requester's messages stand in for the "
    "task's scope (a marked assumption)"
)


@dataclass(frozen=True)
class Plan:
    """What a pass reads with: the looks' settings, and the enrolled folders."""

    ctx: spotter.Context
    folders: tuple[str, ...]


def settings_now() -> Plan | str:
    """The settings the chats are followed with now, else why none is followed."""
    try:
        shared = data_repo.locate()
        if shared is None:
            return "no shared repository is set up, so the Spotter's settings cannot be read"
        settings = lookup.machine(shared)
        limit = watched.needed(settings)  # each look's credit limit
        if limit is None:
            return "the Spotter is switched off"
        folders = machine_settings.current().enrolled_chats
        s, role = settings.spotter, settings.agent("spotter")
    except SettingsUnset as exc:
        return f"the Spotter's settings are not complete ({exc})"
    except (StoreError, data_repo.DataRepoError, OSError, ValueError) as exc:
        return f"the Spotter's settings cannot be read ({type(exc).__name__}: {exc})"
    if not folders:
        return "no chats are enrolled"
    ctx = spotter.Context(
        project="", change="", step="chat", looks=tuple(s.looks or ()), sample_rate=s.sample_rate or 0,
        verbose=s.verbose_on(datetime.now(UTC).date()), model=role.model or "", effort=role.effort or "",
        limit=limit, context=role.context or "", actions=s.actions(), gaps=(CHAT,),
    )  # fmt: skip
    return Plan(ctx, tuple(folders))  # no prompt: each chat takes its own at each turn's start (``Follower._snapped``)
