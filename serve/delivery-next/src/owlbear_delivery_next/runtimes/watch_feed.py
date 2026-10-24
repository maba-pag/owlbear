"""The watcher's SDK feed (W1a; design §3.1, §3.5, §3.6 slices 2 and 3): every tool call of a session, report-only.

Each ``tool.execution_start`` opens one observation, keyed by its session and tool-call id, its time and order fixed
then; each ``permission.requested`` for the same call adds the runtime's parsed request to it, before or after the
start and as often as it comes. Every change classifies the call again (``watch_policy``) and upserts its one report,
or removes it once the call is found inside; a writer thread persists them (``watch_reports``). The callback only
classifies and queues: it never waits, never raises into the session, and changes neither a step's outcome nor the
guard's decisions. The agent is the event's ``agent_id``, else the subagent its parent call launched, else "main"
for a call under no parent (the step's own agent, as the model check counts it), else "unknown". The runtime's shell
may persist between calls: once a call may have moved a shell or changed its HOME or TMPDIR, later calls of that
shell (its ``shellId``; a call naming none, or a changer whose start is not seen: any in the session) are judged with
that change, each call's once. Calls run in their starts' order (else their first request's); equal times count as
before, and whenever a call's change is new, grows or moves in time, the session's calls are judged again. This
over-approximates on purpose: an unresolved report means the watcher cannot tell. Each shell is assumed to start in
the session's folder; one that moved before the watcher saw it is not covered.

Watched: every Change-owned session, each in its own folder: the runner's steps, the brief and plan rounds,
reconsideration, the amendment challenge, the visual and design judges and a test review's shares. Not watched: the
decision picker and lookups (read-only, no Change worktree), memory curation and design-pack runs (machine sessions),
and window steps until they reopen (slice 8).
"""

from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.change_contracts import watch_policy
from owlbear_delivery_next.change_contracts.permissions import view
from owlbear_delivery_next.local_system.mask import redact
from owlbear_delivery_next.state_store import watch_reports

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from pathlib import Path

    from owlbear_delivery_next.runtimes.subagents import Watch

NOW_LIMIT = 80  # characters of the now line's summary, and of a report's command
START, ASKED, LAUNCHED = "tool.execution_start", "permission.requested", "subagent.started"


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

    at: str  # its start's time, else its first permission request's: the order calls ran in
    shell: str = ""  # the bash tool's shell id; "" for its default shell or when not seen
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
        self.launched: dict[str, str] = {}  # launcher call id to the subagent it started, as this feed saw it
        self.changers: dict[tuple[str, str], tuple[str, str, bool, frozenset[str]]] = {}  # at, shell, moves, changes
        self.open = True
        self.writer = watching.writer()

    def seen(self, kind: str, ev: Any) -> None:  # noqa: ANN401 - an SDK session event
        """Observe one event; a start or a permission request updates its call's report."""
        if kind == LAUNCHED:
            self._launched(ev)
            return
        if kind not in {START, ASKED}:
            return
        if not self.open:  # the runtime is stopped; a late callback is counted, never written
            self.writer.late()
            return
        try:
            key, _ = self._observed(kind, ev)
            self._judged(key)
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
            seen = self._call(cid, stamp)
            tool, args = getattr(data, "tool_name", "") or "", getattr(data, "arguments", None)
            shell = args.get("shellId") if isinstance(args, dict) else None
            seen.shell = shell if isinstance(shell, str) else ""
            info = getattr(data, "shell_tool_info", None)
            redirect = bool(getattr(info, "has_write_file_redirection", False))
            seen.call = replace(seen.call, tool=tool, arguments=args, redirect=redirect)
            seen.at, seen.started, seen.command = stamp, True, summary(tool, args)
            seen.parent = getattr(data, "parent_tool_call_id", None) or ""
        else:
            request = data.permission_request  # one without a call id is a call of its own
            cid = getattr(request, "tool_call_id", None) or f"request {getattr(data, 'request_id', '')}"
            seen = self._call(cid, stamp)
            seen.call = replace(seen.call, asked=(*seen.call.asked, asked(request)))
            seen.command = seen.command or _command(request)
            seen.agent_id = seen.agent_id or getattr(data, "owner_agent_id", None) or ""  # the agent it asked for
        seen.agent_id = seen.agent_id or getattr(ev, "agent_id", None) or ""
        return (self.session(), cid), seen

    def _call(self, cid: str, stamp: str) -> _Seen:
        key = (self.session(), cid)
        if key not in self.calls:
            self.calls[key] = _Seen(stamp)
        return self.calls[key]

    def _shares(self, changer: tuple[str, str], key: tuple[str, str]) -> bool:
        """Whether *changer* may have run before *key* in its shell: a call naming no shell id, or a changer whose
        start is not seen, shares any; equal times cannot be told apart, so they count as before."""  # noqa: D205, D209
        if changer == key or changer[0] != key[0]:
            return False
        before, after = self.calls[changer], self.calls[key]
        shared = not after.shell or not before.started or before.shell == after.shell
        return shared and before.at <= after.at

    def _shell_state(self, key: tuple[str, str], seen: _Seen) -> watch_policy.Call:
        """The call with what earlier calls of its shell may have changed there."""
        earlier = [(moves, changes) for k, (_, _, moves, changes) in self.changers.items() if self._shares(k, key)]
        moved = any(m for m, _ in earlier)
        return replace(seen.call, moved=moved, changed=frozenset().union(*(c for _, c in earlier)))

    def _launched(self, ev: Any) -> None:  # noqa: ANN401 - an SDK session event
        """Name a subagent's launcher, and report again the calls already reported under it as "unknown"."""
        launcher, name = getattr(ev.data, "tool_call_id", "") or "", getattr(ev.data, "agent_name", "") or ""
        if not (launcher and name) or not self.open:
            return
        self.launched[launcher] = name
        try:
            for key, seen in list(self.calls.items()):
                if seen.reported and launcher in {seen.parent, seen.agent_id}:
                    self._judged(key)
        except Exception as exc:  # noqa: BLE001 - an observation never ends the step
            self.writer.lost(f"{type(exc).__name__}: {exc}"[:200])

    def _judged(self, key: tuple[str, str]) -> None:
        """Judge the call; when what it may change in its shell is new, grew or moved in time, judge the calls of its
        session again, from their kept observations."""  # noqa: D205, D209 - two facts per line
        pending = [key]
        while pending:
            k = pending.pop(0)
            if self._judged_once(k, self.calls[k]):
                pending += [o for o in self.calls if o not in pending and o != k and o[0] == k[0]]

    def _judged_once(self, key: tuple[str, str], seen: _Seen) -> bool:
        """Judge one call and upsert or drop its report; whether its record of shell changes is new or changed."""
        outcome = watch_policy.judge(self._shell_state(key, seen), self.own, self.places)
        old = self.changers.get(key)
        if outcome.moves or outcome.changes or old:  # by call id: a call judged again changes its shell once
            _, _, moves, changes = old or ("", "", False, frozenset())
            self.changers[key] = (seen.at, seen.shell, moves or outcome.moves, changes | outcome.changes)
        self._report(key, seen, outcome)
        return self.changers.get(key) != old

    def _report(self, key: tuple[str, str], seen: _Seen, outcome: watch_policy.Outcome) -> None:
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

        A started call under no parent call is the step's own agent's, as the model check counts it (TD-94); one
        under a parent this session never saw launch, or seen only in a permission request naming no agent, is
        "unknown".
        """
        if seen.agent_id:
            return self._named(seen.agent_id) or seen.agent_id
        if not seen.started:  # only a start shows whether a call has a parent
            return "unknown"
        if not seen.parent:
            return "main"
        return self._named(seen.parent) or "unknown"

    def _named(self, launcher: str) -> str:
        """The subagent *launcher* started, by the step's subagent record or this feed's; "" when neither saw it."""
        found = self.agents.seen.get(launcher)
        return (found.agent if found else "") or self.launched.get(launcher, "")


def asked(request: Any) -> watch_policy.Asked:  # noqa: ANN401 - one of the SDK's permission request classes
    """One SDK permission request as the policy reads it: the guard's view plus a shell request's evidence.

    That is its command text, the runtime's segments and commands with their read-only marks, its possible and
    resolved paths and its resolved working directory.
    """
    req = view(request)
    commands = tuple((str(c.identifier), bool(c.read_only)) for c in getattr(request, "commands", None) or ())
    segments = getattr(request, "command_segments", None) or ()
    resolved = getattr(request, "resolved_paths", None) or {}
    return watch_policy.Asked(
        req.kind, req.paths if req.kind == "write" else (), bool(commands) and all(r for _, r in commands),
        bool(getattr(request, "has_write_file_redirection", False)),
        str(getattr(request, "full_command_text", "") or "") if req.kind == "shell" else "",
        tuple((str(s.full_command_text), str(s.identifier)) for s in segments), commands,
        tuple(str(p) for p in getattr(request, "possible_paths", None) or ()),
        tuple((str(k), str(v)) for k, v in resolved.items()),
        str(getattr(request, "resolved_working_directory", "") or ""),
    )  # fmt: skip


def _command(request: Any) -> str:  # noqa: ANN401 - one of the SDK's permission request classes
    req = view(request)
    if whole := getattr(request, "full_command_text", None):  # the command as given, not its programs' names
        return summary("bash", {"command": whole})
    if req.commands:
        return summary("bash", {"command": req.commands[0]})
    return summary(req.kind, {"path": req.paths[0] if req.paths else ""})


async def around[T](feed: Feed | None, work: Awaitable[T]) -> T:
    """Await *work*, then close *feed* off the loop; a cancellation meanwhile waits until its writer is gone.

    So no writer outlives the session's run: a cancellation is raised once the close finished, unless an error or
    cancellation was already on its way out.
    """
    propagating = False
    try:
        return await work
    except BaseException:
        propagating = True
        raise
    finally:
        if feed is not None and await _closed(feed) and not propagating:
            raise asyncio.CancelledError


async def _closed(feed: Feed) -> bool:
    """Close *feed* in a thread, whatever cancels the caller meanwhile; whether it was cancelled."""
    closing, cancelled = asyncio.ensure_future(asyncio.to_thread(feed.close)), False
    while not closing.done():
        try:
            await asyncio.shield(closing)
        except asyncio.CancelledError:
            cancelled = True
    closing.result()
    return cancelled


def opened(watching: Watching | None, own: Path, session: Callable[[], str], agents: Watch) -> Feed | None:
    """The session's watcher; None when the master switch is off, or when it cannot start: the step goes on."""
    if watching is None:
        return None
    try:
        return Feed(watching, own, session, agents)
    except Exception as exc:  # noqa: BLE001 - a watcher that cannot start never ends the step
        sys.stderr.write(f"watcher {watching.slug}: not started ({type(exc).__name__}: {exc})\n")  # the runner's log
        return None
