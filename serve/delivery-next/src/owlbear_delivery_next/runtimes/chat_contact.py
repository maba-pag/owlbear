"""Exact contact with an existing editor chat, and the runtime call that saved a brief."""

from __future__ import annotations

import contextlib
import json
import sqlite3
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

from owlbear_delivery_next.git.command_failure import failure
from owlbear_delivery_next.improvement import chatlogs
from owlbear_delivery_next.runtimes import ahp

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_delivery_next.runtimes.ahp import Transport

GONE = "VS Code's agent host is not running"
CHATS = "SELECT owner_session_uri, chat_uri, provider_data FROM chats_v2 WHERE tombstoned = 0 AND provider_data LIKE ?"


class ChatError(RuntimeError):
    """The chat to act on is not known for certain."""


def store() -> Path:
    """VS Code's agent-host database, opened read-only by the mapper."""
    return Path.home() / "Library/Application Support/Code/User/globalStorage/agent-host.db"


def chat_of(session: str, db: Path | None = None) -> tuple[str, str]:
    """The unique editor owner/chat naming the runtime session, never a title or latest-chat match."""
    path = db or store()
    with contextlib.closing(sqlite3.connect(f"file:{quote(str(path))}?mode=ro", uri=True)) as conn:
        rows = conn.execute(CHATS, (f"%{session}%",)).fetchall()
    found = {(owner, chat) for owner, chat, data in rows if _sdk(data) == session}
    if len(found) != 1:
        msg = f"no exact chat for session {session}: {len(found)} matches"
        raise ChatError(msg)
    return found.pop()


def _sdk(data: str | None) -> str:
    try:
        said = json.loads(data or "")
    except ValueError:
        return ""
    return str(said.get("sdkSessionId") or "") if isinstance(said, dict) else ""


def channel(conn: Transport, owner: str, chat: str, *, timeout: float = 60) -> str:
    """Resolve the database's chat URI to exactly the channel the host currently lists."""
    sid = owner.split(":/", 1)[-1]
    head = chat.removeprefix("ahp-chat://").split("/", 1)[0]
    items = conn.request("listSessions", {"channel": ahp.ROOT}, timeout=timeout).get("items") or []
    sessions = [s for s in items if s.get("resource", "").split(":/", 1)[-1] == sid]
    listed = [c.get("resource", "") for s in sessions for c in s.get("chats") or []]
    if head == "default":
        found = [c for c in listed if c.startswith("ahp-chat://default/")] or [
            d for s in sessions if (d := s.get("defaultChat")) and d in listed
        ]
    else:
        found = [c for c in listed if c in {chat, f"ahp-chat:/{head}"}]
    if len(found) != 1:
        msg = f"the agent host lists {len(found)} chats for {chat} of session {owner}, not one"
        raise ChatError(msg)
    return found[0]


def opened() -> Transport:
    """Connect only to a running host; never launch or sign in to the editor."""
    if (entry := ahp.endpoint()) is None:
        raise ahp.HostError(GONE)
    try:
        return ahp.connect(entry, f"owlbear-chat-{uuid.uuid4().hex[:8]}")
    except OSError as exc:
        msg = f"{GONE}: its published endpoint failed: {failure(exc)}"
        raise ahp.HostError(msg) from exc


def saving_call(
    workspace: Path, tool: str, body: object, normalize: Callable[[object], object], *, sessions: Path | None = None
) -> tuple[str, str]:
    """Find one open save invocation, checking workspace/client metadata before reading its events."""
    wanted, matches = normalize(body), []
    root = sessions or chatlogs.state()
    for folder in root.iterdir() if root.is_dir() else ():
        if not folder.is_dir():
            continue
        meta = chatlogs.metadata(folder)
        if meta.get("client_name") != "vscode-agent-host" or not isinstance(cwd := meta.get("cwd"), str):
            continue
        if Path(cwd).resolve() != workspace.resolve():
            continue
        for cid, args in _calls(folder / "events.jsonl", tool).items():
            try:
                same = normalize(args) == wanted
            except TypeError, ValueError:  # an unrelated/invalid call is not this accepted save
                same = False
            if same:
                matches.append((folder.name, cid))
    if len(matches) != 1:
        msg = f"no unique in-flight {tool} call in {workspace}: {len(matches)} matches"
        raise ChatError(msg)
    return matches[0]


def _calls(path: Path, tool: str) -> dict[str, Any]:
    calls = {}
    with path.open() as stream:
        for line in stream:
            if not line.endswith("\n"):
                break
            event = json.loads(line)
            data, kind = event.get("data") or {}, event.get("type")
            cid = str(data.get("toolCallId") or "")
            if kind in {"abort", "session.abort", "session.shutdown", "user.message"}:
                calls.clear()
            elif kind == "tool.execution_complete":
                calls.pop(cid, None)
            elif kind == "tool.execution_start":
                named = (data.get("mcpServerName"), data.get("mcpToolName")) == ("owlbear-delivery", tool)
                legacy = not data.get("mcpServerName") and data.get("toolName") in {
                    f"owlbear-delivery-{tool}",
                    f"owlbear-delivery/{tool}",
                }
                if cid and (named or legacy):
                    calls[cid] = data.get("arguments")
    return calls
