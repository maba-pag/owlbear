"""The agent host's own record of a window step's session: ``~/.copilot/session-state/<id>/events.jsonl``.

The host writes every session's events there, the window's included; Delivery reads it after the step for what its
connection does not carry: which tools the step's agent was given and what each subagent did (window-step gate,
item 8). The record's session id is not the protocol's, so the step's record is the one that started in the step's
folder after its launch and selected the step's agent.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any

STATE = Path.home() / ".copilot/session-state"
# the runtime adds these to any agent, whatever its allowlist (runtime research P18, P25)
ALWAYS = frozenset({"skill", "sql", "task_complete", "parallel", "multi_tool_use"})

type Event = dict[str, Any]


@dataclass
class Record:
    """What the step's record says; ``found`` is False when no single record matched."""

    found: bool
    why: str = ""
    tools: list[str] | None = None  # the tools the step's agent was given, None when the record does not say
    subagents: list[tuple[str, SimpleNamespace]] = field(default_factory=list)  # (event type, data) in record order


def _events(path: Path) -> list[Event]:
    events = []
    for line in path.read_text(errors="replace").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue  # a line the host is still writing
        if isinstance(event, dict):
            events.append(event)
    return events


def _started(events: list[Event], folder: Path, since: datetime) -> bool:
    first = events[0] if events else {}
    data = first.get("data") or {}
    if first.get("type") != "session.start" or not isinstance(data, dict):
        return False
    cwd = (data.get("context") or {}).get("cwd")
    try:
        at = datetime.fromisoformat(str(data.get("startTime")))
    except ValueError:
        return False
    return bool(cwd) and Path(cwd).resolve() == folder.resolve() and at >= since - timedelta(seconds=5)


def _selected(events: list[Event], agent: str) -> list[str] | None:
    """Every tool any selection of *agent* gave it, in first-seen order; None when it was never selected."""
    tools: dict[str, None] | None = None
    for event in events:
        data = event.get("data") or {}
        if event.get("type") == "subagent.selected" and data.get("agentName") == agent:
            tools = (tools or {}) | dict.fromkeys(str(t) for t in data.get("tools") or [])
    return None if tools is None else list(tools)


def _subagent(data: dict[str, Any]) -> SimpleNamespace:
    """The record's camelCase fields under the SDK event's names, so ``subagents.Watch`` reads both alike."""
    ms = data.get("durationMs")
    return SimpleNamespace(
        tool_call_id=data.get("toolCallId") or "",
        agent_name=data.get("agentName") or "",
        model=data.get("model"),
        total_tokens=data.get("totalTokens"),
        total_tool_calls=data.get("totalToolCalls"),
        duration=timedelta(milliseconds=ms) if isinstance(ms, int | float) else None,
    )


def read(folder: Path, since: datetime, agent: str, state: Path = STATE) -> Record:
    """The record of the session that started in *folder* after *since* and selected *agent*."""
    matches = []
    for path in state.glob("*/events.jsonl") if state.is_dir() else []:
        try:
            if path.stat().st_mtime < since.timestamp() - 5:
                continue
            events = _events(path)
        except OSError:
            continue
        if _started(events, folder, since) and (tools := _selected(events, agent)) is not None:
            matches.append((events, tools))
    if len(matches) != 1:
        return Record(found=False, why=f"{len(matches)} host records match the step" if matches else "no host record")
    events, tools = matches[0]
    kinds = {"subagent.started", "subagent.completed", "subagent.failed"}
    subagents = [(e["type"], _subagent(e.get("data") or {})) for e in events if e.get("type") in kinds]
    return Record(found=True, tools=tools, subagents=subagents)


def unexpected(given: list[str], allowed: list[str]) -> list[str]:
    """The tools the host gave the agent beyond its allowlist and the runtime's own."""
    return sorted(set(given) - set(allowed) - ALWAYS)
