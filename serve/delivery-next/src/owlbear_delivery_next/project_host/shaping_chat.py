"""The saving-chat binding and the project's owner-directed shaping hand-off."""

from __future__ import annotations

import logging
import sqlite3
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.change_contracts.shaper_records import SavingChat
from owlbear_delivery_next.change_flow import brief_tools, shaper_wake
from owlbear_delivery_next.git.command_failure import failure
from owlbear_delivery_next.runtimes import chat_contact
from owlbear_delivery_next.settings.config import SettingsUnset
from owlbear_delivery_next.state_store import work_block
from owlbear_delivery_next.state_store.store import StoreError

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear_delivery_next.change_contracts.models import Change
    from owlbear_delivery_next.project_host.host import Host
    from owlbear_delivery_next.state_store.store import Lock

_log = logging.getLogger(__name__)
_LISTS = ("criteria", "scope", "non_goals", "decisions", "person_checks", "specified")
_BRIEF = ("title", "outcome", "change", *_LISTS)


def normalized(tool: str, body: object) -> dict[str, Any]:
    """Apply the MCP facade's nullable-list projection before the existing draft defaults."""
    if not isinstance(body, dict):
        msg = "a save invocation must contain an argument object"
        raise TypeError(msg)
    lists = ("states", "steps") if tool == "save_visual_check" else _LISTS
    args = body | {key: body.get(key) or [] for key in lists}
    if tool == "save_visual_check":
        return brief_tools.VisualDraft.model_validate(args).model_dump()
    return brief_tools.BriefDraft.model_validate(args).model_dump(include=set(_BRIEF))


def binding(repo: Path, tool: str, body: object) -> SavingChat:
    """The exact runtime-observed save caller; inability to contact it never rejects a valid brief."""
    try:
        session, call = chat_contact.saving_call(repo, tool, body, lambda args: normalized(tool, args))
        owner, chat = chat_contact.chat_of(session)
    except (OSError, ValueError, TypeError, sqlite3.Error, chat_contact.ChatError) as exc:
        reason = f"the saving chat for {tool} in {repo} could not be established: {failure(exc)}"
        if not isinstance(exc, chat_contact.ChatError):
            _log.warning("%s", reason)
        return SavingChat(reason=reason)
    return SavingChat(session=session, call=call, owner=owner, chat=chat)


def dispatch(host: Host, lock: Lock, c: Change) -> None:
    """Consume one eligible attempt before editor I/O, then save its full receipt without an automatic retry."""
    n = c.shaper_notice
    if not n or n.state != "pending" or not shaper_wake.current(c):
        return
    if (
        host.paused()
        or c.intent.paused_at
        or not host.owner_runs()
        or host.updating()
        or host.code() != host.record.code
        or work_block.of_store(host.store)
    ):
        return
    n.state = "attempted"
    host.store.write(lock, c)
    try:
        role = host.store.settings().agent("shaper")
        caller = c.brief.saving_chat or SavingChat(reason="the brief's saving chat was not recorded")
        result = host.post(host.repo, role, caller, n.message, shaper_wake.prompt(c, host.store.name or host.repo.name))
        n.state, n.detail = result.state, result.detail
    except (SettingsUnset, StoreError) as exc:
        n.state, n.detail = "failed", failure(exc)
    host.store.write(lock, c)
    host.say(f"{c.slug}: shaping message for brief v{n.version} {n.state}: {n.detail}".rstrip())


def shown(c: Change, *, paused: bool) -> dict[str, str] | None:
    """A current brief's receipt; rendering performs no editor contact or dispatch."""
    n = c.shaper_notice
    if n is None or n.version != c.brief.version:
        return None
    said = {
        "pending": "The message waits for Resume."
        if paused or c.intent.paused_at
        else "The message waits for Delivery to continue.",
        "attempted": "Delivery could not confirm the post. It will not send this message again.",
        "posted": "Message posted to the shaping chat.",
        "failed": "Could not post to the shaping chat.",
    }
    return {"state": n.state, "text": said[n.state], "detail": n.detail}
