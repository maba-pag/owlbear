"""How often and how early each agent of a session compacted its context, read from the runtime's own log.

The log is ``~/.copilot/session-state/<id>/events.jsonl``, else Retro's copy. A compaction counts when it applied: a
``session.compaction_start`` whose ``session.compaction_complete`` (same attempt) succeeded with outcome ``applied`` or
none. How early is the agent's model calls (``assistant.turn_start``) started before its first applied compaction
completed (D-01M69C82SQMBHZ8FBKJBX42H3Y). Each ``subagent.started`` is one invocation; its events carry its
``agentId``, its model calls also its ``parentToolCallId``. A log read before and unchanged since is not read again.
"""

from __future__ import annotations

import gzip
import json
import logging
import threading
import zlib
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

from owlbear_delivery_next.improvement import chatlogs
from owlbear_delivery_next.runtimes import spend_logs

if TYPE_CHECKING:
    from pathlib import Path

LOG = logging.getLogger(__name__)
WANTED = frozenset({"assistant.turn_start", "subagent.started", "session.compaction_start",
                    "session.compaction_complete"})  # fmt: skip


@dataclass(frozen=True)
class Actor:
    """One agent's counts: the main agent, or one subagent invocation."""

    calls: int = 0  # its assistant.turn_start events
    compactions: int = 0  # applied ones
    before: int | None = None  # its calls started before its first applied compaction completed


@dataclass(frozen=True)
class Log:
    """A session's counts, or why it has none."""

    state: Literal["found", "missing", "error"]
    main: Actor = Actor()
    subagents: tuple[tuple[str, Actor], ...] = ()  # (agentName, counts), one per invocation, in launch order
    error: str = ""  # "<path>: <ExcType>: <message>"


@dataclass
class _Tally:
    calls: int = 0
    compactions: int = 0
    before: int | None = None

    def actor(self) -> Actor:
        return Actor(self.calls, self.compactions, self.before)


@dataclass
class _Session:
    main: _Tally = field(default_factory=_Tally)
    launched: list[tuple[str, _Tally]] = field(default_factory=list)
    children: dict[str, _Tally] = field(default_factory=dict)  # by the child's agentId
    calls: dict[str, _Tally] = field(default_factory=dict)  # by the launching toolCallId
    starts: dict[str, _Tally] = field(default_factory=dict)  # compaction attempts, by attempt id

    def launch(self, name: str, tool_call: str, child: str) -> _Tally:
        tally = _Tally()
        self.launched.append((name, tally))
        if child:
            self.children[child] = tally
        if tool_call:
            self.calls[tool_call] = tally
        return tally

    def of(self, event: dict[str, Any], data: dict[str, Any]) -> _Tally:
        child = str(event.get("agentId") or "")
        if child in self.children:
            return self.children[child]
        parent = str(data.get("parentToolCallId") or "")
        if parent in self.calls:
            return self.calls[parent]
        return self.launch("subagent", "", child) if child else self.main


_lock = threading.Lock()
_cache: dict[str, tuple[Path, int, int, Log]] = {}


def read(session: str) -> Log:
    """The session's counts from its live log, else Retro's copy; ``missing`` without either, ``error`` unreadable."""
    for path in (chatlogs.state() / session / "events.jsonl", chatlogs.root() / "chatlogs" / session / "log.jsonl.gz"):
        try:
            seen = path.stat()
            with _lock:
                hit = _cache.get(session)
            if hit is not None and hit[:3] == (path, seen.st_size, seen.st_mtime_ns):
                return hit[3]
            log = _parse(path)
        except FileNotFoundError:
            continue
        except (OSError, EOFError, ValueError, TypeError, zlib.error) as exc:  # gzip.BadGzipFile is an OSError
            error = f"{path}: {type(exc).__name__}: {exc}"
            LOG.warning("compaction log unreadable: %s", error)
            return Log("error", error=error)
        with _lock:
            _cache[session] = (path, seen.st_size, seen.st_mtime_ns, log)
        return log
    return Log("missing")


def _parse(path: Path) -> Log:
    found = _Session()
    with (gzip.open(path, "rt", encoding="utf-8", errors="replace") if path.suffix == ".gz"
          else path.open(encoding="utf-8", errors="replace")) as f:  # fmt: skip
        for raw in f:
            kind = spend_logs.kind(raw)
            if kind not in WANTED:
                continue
            try:
                event = json.loads(raw)
            except ValueError:
                if raw.endswith("\n"):
                    raise
                continue  # the last line, which the runtime is still writing
            data = event.get("data", {}) if isinstance(event, dict) else None
            if not isinstance(data, dict):
                raise TypeError(kind)
            if kind == "subagent.started":
                found.launch(str(data.get("agentName") or "subagent"), str(data.get("toolCallId") or ""),
                             str(event.get("agentId") or ""))  # fmt: skip
            elif kind == "assistant.turn_start":
                found.of(event, data).calls += 1
            elif kind == "session.compaction_start":
                found.starts[str(data.get("compactionAttemptId"))] = found.of(event, data)
            else:
                _complete(found, data)
    return Log("found", found.main.actor(), tuple((name, t.actor()) for name, t in found.launched))


def _complete(found: _Session, data: dict[str, Any]) -> None:
    """An applied compaction counts for the agent its start named; one without its start is no compaction."""
    tally = found.starts.pop(str(data.get("compactionAttemptId")), None)
    if tally is None or data.get("success") is not True or data.get("outcome") not in {None, "applied"}:
        return
    tally.compactions += 1
    if tally.before is None:
        tally.before = tally.calls
