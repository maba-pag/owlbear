"""Exact contact with an existing editor chat, and the runtime call that saved a brief."""

from __future__ import annotations

import contextlib
import json
import sqlite3
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal
from urllib.parse import quote, unquote

from owlbear_delivery_next.git.command_failure import failure
from owlbear_delivery_next.improvement import chatlogs
from owlbear_delivery_next.runtimes import ahp, readiness, vscode_message
from owlbear_delivery_next.runtimes.vscode_contract import StepSpec

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_delivery_next.change_contracts.shaper_records import SavingChat
    from owlbear_delivery_next.runtimes.ahp import Transport
    from owlbear_delivery_next.settings.config import Effective

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


@dataclass(frozen=True)
class Posted:
    """An acknowledged post, an explicit failure, or an uncertain consumed attempt."""

    state: Literal["posted", "failed", "attempted"]
    detail: str = ""


def post(folder: Path, role: Effective, caller: SavingChat, mid: str, text: str) -> Posted:
    """Queue once to a running editor; preserve its draft/active turn and never retry an uncertain dispatch."""
    if caller.reason or not caller.chat:
        return Posted("failed", caller.reason or "the saving chat was not recorded")
    agent = readiness.shaper_path(Path.home())
    if agent is None or not agent.is_file():
        return Posted("failed", "the shaping agent is not installed; run `owlbear install`")
    spec = StepSpec(folder, agent, role.model, role.effort, text, context=role.context)
    sent = False
    try:
        with contextlib.closing(opened()) as conn:
            end = time.monotonic() + 10
            target, message = _prepare(conn, caller, spec, end)
            sent = True
            seq = conn.dispatch(
                target, {"type": "chat/pendingMessageSet", "kind": "queued", "id": mid, "message": message}
            )
            return _ack(conn, target, mid, seq, end)
    except (OSError, ValueError, TypeError, KeyError, ChatError, ahp.HostError) as exc:
        return Posted("attempted" if sent else "failed", failure(exc))


def _ack(conn: Transport, target: str, mid: str, seq: int, end: float) -> Posted:
    while True:
        state = conn.request("subscribe", {"channel": target}, timeout=_left(end))["snapshot"]["state"]
        if any(m.get("id") == mid for m in state.get("queuedMessages") or []):
            return Posted("posted")
        ev = conn.next_event(min(0.1, _left(end)))
        if (why := vscode_message.rejection(ev, conn.client_id, seq)) is not None:
            return Posted("failed", f"the editor refused the shaping message: {why}")
        if ev and ev.get("method") == "closed":
            return Posted("attempted", str((ev.get("params") or {}).get("error")))
        params = (ev or {}).get("params") or {}
        action = params.get("action") or {}
        if (
            params.get("channel") == target
            and action.get("type") == "chat/turnStarted"
            and action.get("queuedMessageId") == mid
        ):
            return Posted("posted")


def _prepare(conn: Transport, caller: SavingChat, spec: StepSpec, end: float) -> tuple[str, ahp.Json]:
    owner, schema = _role(conn, spec.folder, caller, spec, end)
    target = channel(conn, caller.owner, caller.chat, timeout=_left(end))
    conn.request("subscribe", {"channel": target}, timeout=_left(end))
    session = conn.request("subscribe", {"channel": owner}, timeout=_left(end))["snapshot"]["state"]
    agents = (a for c in session.get("customizations") or [] for a in c.get("children") or [])
    uris = {unquote(u) for u in spec.agent_uris}
    found = next((a["uri"] for a in agents if a.get("type") == "agent" and unquote(a.get("uri", "")) in uris), None)
    if found is None:
        msg = f"the saving session does not list the shaping agent {spec.agent}"
        raise ChatError(msg)
    return target, vscode_message.build(spec, schema, {"uri": found})


def _left(end: float) -> float:
    left = end - time.monotonic()
    if left <= 0:
        msg = "the editor did not confirm the shaping message within 10 seconds"
        raise ahp.HostError(msg)
    return left


def _role(conn: Transport, folder: Path, caller: SavingChat, spec: StepSpec, end: float) -> tuple[str, ahp.Json | None]:
    items = conn.request("listSessions", {"channel": ahp.ROOT}, timeout=_left(end)).get("items") or []
    sid = caller.owner.split(":/", 1)[-1]
    sessions = [
        s
        for s in items
        if s.get("resource", "").split(":/", 1)[-1] == sid
        and folder.resolve().as_uri() in (s.get("workingDirectories") or [])
    ]
    if len(sessions) != 1:
        msg = f"the editor does not list exactly the saving session in {folder}"
        raise ChatError(msg)
    root = conn.request("subscribe", {"channel": ahp.ROOT}, timeout=_left(end))["snapshot"]["state"]
    models = [m for a in root.get("agents") or [] if a.get("provider") == "copilotcli" for m in a.get("models") or []]
    model = next((m for m in models if m.get("id") == spec.model), None)
    if model is None:
        msg = f"the editor does not list shaper model {spec.model}; it lists {[m.get('id') for m in models]}"
        raise ChatError(msg)
    return sessions[0]["resource"], (model.get("configSchema") or {}).get("properties")
