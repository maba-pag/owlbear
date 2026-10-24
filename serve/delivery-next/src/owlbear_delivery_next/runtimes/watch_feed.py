"""The watcher's SDK feed (W1a; design §3.1, §3.5, §3.6 slices 2 and 3): every tool call of a session, report-only.

Each ``tool.execution_start`` opens one observation, keyed by its session and tool-call id, its time and order fixed
then; each ``permission.requested`` for the same call adds the runtime's parsed request to it, before or after the
start and as often as it comes. Every change classifies the call again (``watch_policy``) and upserts its one report,
or removes it once the call is found inside; a writer thread persists them (``watch_reports``). The callback only
classifies and queues: it never waits, never raises into the session, and changes neither a step's outcome nor the
guard's decisions. The agent is the event's ``agent_id``, else the subagent its parent call launched, else "main"
for a call under no parent (the step's own agent, as the model check counts it), else "unknown".

Watched: every Change-owned session, each in its own folder: the runner's steps, the brief and plan rounds,
reconsideration, the amendment challenge, the visual and design judges and a test review's shares. Not watched: the
decision picker and lookups (read-only, no Change worktree), memory curation and design-pack runs (machine sessions),
and window steps until they reopen (slice 8).
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.change_contracts import watch_policy
from owlbear_delivery_next.change_contracts.permissions import view
from owlbear_delivery_next.local_system.mask import redact
from owlbear_delivery_next.state_store import watch_reports

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from owlbear_delivery_next.runtimes.subagents import Watch

NOW_LIMIT = 80  # characters of the now line's summary, and of a report's command
START, ASKED = "tool.execution_start", "permission.requested"


def summary(tool: str, arguments: Any) -> str:  # noqa: ANN401 - the SDK's JSON tool arguments
    """One short, redacted line for a tool call: ``ran <command>`` or ``<tool> <target>``."""
    args = arguments if isinstance(arguments, dict) else {}
    target = next((args[k] for k in ("path", "file_path", "pattern", "query", "url") if args.get(k)), "")
    text = f"ran {args['command']}" if args.get("command") else f"{tool} {target}"
    text = " ".join(redact(str(text)).split())
    return text if len(text) <= NOW_LIMIT else text[: NOW_LIMIT - 1] + "…"


@dataclass(frozen=True)
class Watching:
    """A Change-owned session's watcher: its Change and step, the places it judges by, where its reports go."""

    slug: str
    step: str
    places: watch_policy.Places
    writer: Callable[[], watch_reports.Writer]


@dataclass
class _Seen:
    """One call as observed so far."""

    at: str
    call: watch_policy.Call = field(default_factory=watch_policy.Call)
    agent_id: str = ""
    parent: str = ""
    started: bool = False
    command: str = ""
    reported: bool = False


class Feed:
    """One session's watcher: its observations and its report writer."""

    def __init__(self, watching: Watching, own: Path, session: Callable[[], str], agents: Watch) -> None:
        """*own* is the session's folder; *session* gives its current id; *agents* the subagents it started."""
        self.watching, self.session, self.agents = watching, session, agents
        self.places = watching.places.resolved()
        self.own = watch_policy.canonical(str(own), own, self.places)
        self.calls: dict[tuple[str, str], _Seen] = {}
        self.open = True
        self.writer = watching.writer()

    def seen(self, kind: str, ev: Any) -> None:  # noqa: ANN401 - an SDK session event
        """Observe one event; a start or a permission request updates its call's report."""
        if kind not in {START, ASKED}:
            return
        if not self.open:  # the runtime is stopped; a late callback is counted, never written
            self.writer.late()
            return
        try:
            key, seen = self._observed(kind, ev)
            self._judged(key, seen)
        except Exception as exc:  # noqa: BLE001 - an observation never ends the step
            self.writer.lost(f"{type(exc).__name__}: {exc}"[:200])

    def close(self) -> None:
        """Close the intake, then drain and stop the writer; no report is queued after this."""
        self.open = False
        step = self.watching.step
        self.writer.close(lambda said: watch_reports.summary_row(self.session(), step, said))

    def _observed(self, kind: str, ev: Any) -> tuple[tuple[str, str], _Seen]:  # noqa: ANN401 - an SDK event
        at = getattr(ev, "timestamp", None) or datetime.now(UTC)
        stamp = at.astimezone(UTC).isoformat(timespec="milliseconds")
        data = ev.data
        if kind == START:
            cid = getattr(data, "tool_call_id", "") or ""
            seen = self.calls.setdefault((self.session(), cid), _Seen(stamp))
            tool, args = getattr(data, "tool_name", "") or "", getattr(data, "arguments", None)
            info = getattr(data, "shell_tool_info", None)
            redirect = bool(getattr(info, "has_write_file_redirection", False))
            seen.call = replace(seen.call, tool=tool, arguments=args, redirect=redirect)
            seen.at, seen.started, seen.command = stamp, True, summary(tool, args)
            seen.parent = getattr(data, "parent_tool_call_id", None) or ""
        else:
            request = data.permission_request  # one without a call id is a call of its own
            cid = getattr(request, "tool_call_id", None) or f"request {getattr(data, 'request_id', '')}"
            seen = self.calls.setdefault((self.session(), cid), _Seen(stamp))
            seen.call = replace(seen.call, asked=(*seen.call.asked, asked(request)))
            seen.command = seen.command or _command(request)
        seen.agent_id = seen.agent_id or getattr(ev, "agent_id", None) or ""
        return (self.session(), cid), seen

    def _judged(self, key: tuple[str, str], seen: _Seen) -> None:
        outcome = watch_policy.judge(seen.call, self.own, self.places)
        slug, (session, cid) = self.watching.slug, key
        if outcome.inside:
            if seen.reported:
                self.writer.put(watch_reports.drop(slug, session, cid))
            seen.reported = False
            return
        source = ("enriched" if seen.call.asked else "start") if seen.started else "permission"
        report = watch_reports.Report(
            session, cid, seen.at, self.watching.step, self._agent(seen), seen.call.tool or "", seen.command,
            outcome.targets, outcome.verdict, outcome.unresolved, source,
        )  # fmt: skip
        self.writer.put(watch_reports.put(slug, report))
        seen.reported = True

    def _agent(self, seen: _Seen) -> str:
        """The event's agent id, named when it is a launcher's; else the subagent the parent call launched.

        A call under no parent call is the step's own agent's, as the model check counts it (TD-94); one under a
        parent this session never saw launch is "unknown".
        """
        if seen.agent_id:
            launched = self.agents.seen.get(seen.agent_id)
            return launched.agent if launched else seen.agent_id
        if not seen.parent:
            return "main"
        launched = self.agents.seen.get(seen.parent)
        return launched.agent if launched and launched.agent else "unknown"


def asked(request: Any) -> watch_policy.Asked:  # noqa: ANN401 - one of the SDK's permission request classes
    """One SDK permission request as the policy reads it: the guard's view plus the runtime's read-only evidence."""
    req = view(request)
    commands = getattr(request, "commands", None) or ()
    read_only = bool(commands) and all(getattr(c, "read_only", False) for c in commands)
    redirect = bool(getattr(request, "has_write_file_redirection", False))
    return watch_policy.Asked(req.kind, req.paths if req.kind == "write" else (), read_only, redirect)


def _command(request: Any) -> str:  # noqa: ANN401 - one of the SDK's permission request classes
    req = view(request)
    if req.commands:
        return summary("bash", {"command": req.commands[0]})
    return summary(req.kind, {"path": req.paths[0] if req.paths else ""})


def opened(watching: Watching | None, own: Path, session: Callable[[], str], agents: Watch) -> Feed | None:
    """The session's watcher; None when the master switch is off, or when it cannot start: the step goes on."""
    if watching is None:
        return None
    try:
        return Feed(watching, own, session, agents)
    except Exception as exc:  # noqa: BLE001 - a watcher that cannot start never ends the step
        sys.stderr.write(f"watcher {watching.slug}: not started ({type(exc).__name__}: {exc})\n")  # the runner's log
        return None
