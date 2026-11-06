"""The saving-chat binding and the project's owner-directed shaping hand-off."""

from __future__ import annotations

import logging
import sqlite3
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.change_contracts.shaper_records import SavingChat
from owlbear_delivery_next.change_flow import brief_tools
from owlbear_delivery_next.git.command_failure import failure
from owlbear_delivery_next.runtimes import chat_contact

if TYPE_CHECKING:
    from pathlib import Path

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
        _log.warning("%s", reason)
        return SavingChat(reason=reason)
    return SavingChat(session=session, call=call, owner=owner, chat=chat)
