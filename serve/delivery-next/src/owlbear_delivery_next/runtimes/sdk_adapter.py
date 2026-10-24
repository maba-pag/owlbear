"""One bounded worker session on the installed Copilot CLI; it ends at a result-tool call or deadline (D4 §3.2, P4)."""

from __future__ import annotations

import asyncio
import contextlib
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, Any

import psutil
from copilot import CopilotClient, RuntimeConnection
from copilot.rpc import PermissionDecisionApproveOnce, PermissionDecisionReject
from copilot.tools import Tool, ToolInvocation, ToolResult

from owlbear_delivery_next.change_contracts import tool_schema, tools
from owlbear_delivery_next.change_contracts.models import StepKind
from owlbear_delivery_next.change_contracts.permissions import decide, identities, view
from owlbear_delivery_next.local_system import preload, processes
from owlbear_delivery_next.local_system.mask import redact
from owlbear_delivery_next.local_system.processes import Termination, verdict
from owlbear_delivery_next.runtimes import sdk_teardown, step_budget, step_decisions, step_input, subagents, watch_feed
from owlbear_delivery_next.runtimes.copilot_cli import cli_path
from owlbear_delivery_next.runtimes.results import ENDED, Gate
from owlbear_delivery_next.runtimes.sdk_teardown import CALL
from owlbear_delivery_next.runtimes.sdk_teardown import call as _call
from owlbear_delivery_next.runtimes.sdk_usage import USAGE_PAUSE, unexpected_models, unproven, unread, usage_read
from owlbear_delivery_next.runtimes.session_result import PROVEN, Run, limit_reached, note_quota

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from copilot.session import CopilotSession

    from owlbear_delivery_next.change_contracts.models import ItemRef
    from owlbear_delivery_next.change_contracts.permissions import Policy
    from owlbear_delivery_next.change_contracts.preparation import Preparing
    from owlbear_delivery_next.local_system.processes import Pids
    from owlbear_delivery_next.runtimes.session_result import Ending

DEADLINES = {StepKind.PLAN: 1800.0, StepKind.BUILD: 2400.0, StepKind.REVIEW: 1200.0, StepKind.CHECK: 1800.0}  # TD-286
ROLES = {StepKind.PLAN: "planner", StepKind.BUILD: "builder", StepKind.REVIEW: "reviewer", StepKind.CHECK: "preparer"}
POLL = 5.0
START = 60.0  # runtime start, session create or resume
NOW_EVERY = 1.0  # seconds between now-line writes


def agent(kind: StepKind, *, ui: bool = False, role: str = "", judging: bool = False, job: str = "") -> dict[str, Any]:
    """Return the role's custom agent from the package's ``agents/`` prose, with its tools and preloaded skills."""
    role = role or ROLES[kind]
    meta, body = preload.agent_file(role)
    return {
        "name": meta["name"],
        "description": meta["description"],
        "prompt": body.strip(),
        "tools": [*preload.tools(role), *tools.results(role, ui=ui, judging=judging)],  # nothing else (TD-69)
        "skills": list(preload.required(role, ui=ui, job=job)),
    }


def role_of(cfg: Session) -> str:
    """The session's agent role: its own, else its step kind's."""
    return cfg.role or ROLES[cfg.kind]


@dataclass(frozen=True)
class Journal:
    """Durable writes the runner makes under the Change lock as the step goes, so a killed runner leaves them."""

    event: Callable[[dict[str, Any]], None] = lambda _e: None
    delivered: Callable[[], None] = lambda: None
    replaced: Callable[[], str | None] = lambda: None
    now: Callable[[dict[str, Any]], None] = lambda _e: None  # the latest tool call, overwritten; not activity


@dataclass(frozen=True)
class Session:
    """Everything one step session needs; tools are bound here, never by agent-supplied identity (T2)."""

    kind: StepKind
    worktree: Path
    session_id: str
    message: str
    resume: bool
    policy: Policy
    observe: Callable[[], tools.Worktree]
    checks: tuple[str, ...]
    submit: tools.Spec = tools.SUBMIT
    scope: tuple[str, ...] = ()  # the approved brief scope a plan must keep to
    item: ItemRef | None = None  # the conversation item a build task answers, if any
    rejectable: tuple[str, ...] = ()  # finding keys a review repair's builder may reject (TD-124)
    rechecks: tuple[str, ...] = ()  # keys of rejected findings a review rechecks or reconsiders (TD-176, TD-193)
    cap: int = 20  # new findings a review may return: the loop's max findings, none in a rejections-only check
    plan_tasks: tuple[str, ...] = ()  # the plan tasks each final-review finding names (TD-216)
    changed: tuple[str, ...] = ()  # the files a design pack challenger judges one by one (TD-194)
    settled: tuple[str, ...] = ()  # finding keys the owner decided to fix: never rejected (TD-193)
    amendable: tuple[str, ...] = ()  # generated criteria a premise may propose new wording for (TD-179)
    skills: Path | None = None  # the skill folder this session loads instead of the package's: a pack candidate's
    subagents: bool = False  # its role's setting: it may start built-in subagents (TD-374, TD-376)
    credit_limit: float | None = None  # the runtime's hard session limit; an experiment's ledger sets it (TD-178)
    model: str | None = None
    effort: str | None = None  # the SDK's reasoning effort
    context: str = "default"  # the model's context tier: "long" pins its long-context tier, else the runtime chooses
    limit: float | None = None  # seconds the session may run in total: its role's setting (TD-286), else its kind's
    fresh: str = ""  # first message of a replacement session: stored context plus the pending answer
    previous: Pids = field(default_factory=dict)  # PIDs earlier runners recorded for this session
    journal: Journal = field(default_factory=Journal)
    attachments: tuple[dict[str, str], ...] = ()  # blob attachments sent with the first message
    memory: Path | None = None  # the project's memory folder in the shared repository (TD-70, TD-72)
    ui: bool = False  # the Change has a user interface, so the role's design skills load too (TD-76)
    role: str = ""  # the agent role when not the step kind's, such as the design judge's
    job: str = ""  # a judge's label, when its job needs other skills than its role's (TD-166)
    judging: bool = False  # a verdict-only judgement, such as the reviewer's of screenshots: no question (TD-108)
    first_look: tools.Spec | None = None  # a judgement submitted before the final result, which does not end it
    reveal: str = ""  # what the first look's reply releases, such as the detector's findings
    helpers: tuple[tuple[tools.Spec, Callable[[tools.Args], str]], ...] = ()  # Delivery tools that answer, not end
    preparing: Preparing | None = None  # check preparation: the declared options a recipe is validated against
    watch: watch_feed.Watching | None = None  # a Change-owned session's watcher; None when the master switch is off


def sent(events: Iterable[Any], message: str) -> bool:
    """Whether a session transcript already holds *message* as a user message."""
    users = (getattr(e.data, "content", "") or "" for e in events if getattr(e.type, "value", e.type) == "user.message")
    return any(message.strip() in c for c in users)


class _Step:
    def __init__(self, cfg: Session, loop: asyncio.AbstractEventLoop) -> None:
        self.cfg, self.loop, self.run, self.proc = cfg, loop, Run(cfg.session_id), None
        self.client: CopilotClient | None = None
        self.turn = self.idle = False
        self.billed: dict[str, Any] = {"error": "not read"}  # usage before this invocation's first send
        self.session: CopilotSession | None = None  # kept as soon as it opens, even if the first send fails
        self.sending = False  # a first message was sent or attempted, so a model may have run
        self.gate = Gate(cfg, self.run, self.log, self._wake)
        self.changed = asyncio.Event()
        self.shown = float("-inf")  # monotonic time of the last now-line write
        self.created = False  # this invocation created its session, so the runtime preloads the role's skills
        self.preloaded: set[str] = set()  # skills the runtime loaded from Delivery's folder before the first turn
        self.checked = False  # the preload was checked at the first turn
        self.skills = cfg.skills or preload.directory()  # the folder its skills load from
        self.watch = subagents.Watch(allowed=cfg.subagents)
        self.feed: watch_feed.Feed | None = None  # its watcher, for the run only
        self.requests: set[asyncio.Task[None]] = set()

    @property
    def done(self) -> bool:
        return self.gate.done

    def _wake(self) -> None:
        self.loop.call_soon_threadsafe(self.changed.set)

    def log(self, **event: Any) -> None:  # noqa: ANN401 - JSON values; the SDK calls handlers on this loop
        self.cfg.journal.event({"at": datetime.now(UTC).isoformat(timespec="seconds"), **event})

    def finish(self, ending: Ending, payload: tools.Args | None = None, detail: str = "") -> None:
        self.gate.finish(ending, payload, detail)

    def on_event(self, ev: Any) -> None:  # noqa: ANN401, C901 - an SDK session event; one branch per family
        kind = getattr(ev.type, "value", str(ev.type))
        if self.feed is not None:
            self.feed.seen(kind, ev)
        if kind == "assistant.turn_start":
            self.turn = True
            self.preload_checked()
            self.model_seen(getattr(ev.data, "model", None), getattr(ev.data, "parent_tool_call_id", None))
        elif kind == "skill.invoked":
            self.skill_seen(ev.data)
        elif kind == "session.idle" and self.turn:
            self.turn, self.idle = False, True
            self._wake()
        elif kind == "tool.execution_start":
            self.now(getattr(ev.data, "tool_name", "") or "tool", getattr(ev.data, "arguments", None))
        elif kind in {"session.quota_observation", "session.error"}:
            note_quota(self.run, kind, ev.data)
        elif kind == "session.auto_mode_resolved":
            self.gate.wrong_model("the runtime resolved auto")
        elif kind == "assistant.message":
            self.model_seen(getattr(ev.data, "model", None), getattr(ev.data, "parent_tool_call_id", None))
        elif kind == "assistant.usage":
            self.call_seen(ev.data)
        elif kind.startswith("subagent."):
            self.subagent_seen(kind, ev.data)

    def subagent_seen(self, kind: str, data: Any) -> None:  # noqa: ANN401 - SDK subagent event data
        """Any built-in may run when the role allows it (TD-374); any other start voids the step; Auto is a wrong model.

        Each end is journaled as it arrives, so a runner killed later keeps what its subagents did.
        """
        if kind == "subagent.started":
            why = self.watch.started(data)
            self.log(event="subagent-started", agent=getattr(data, "agent_name", ""), allowed=not why)
            if why == "auto":
                self.gate.wrong_model("a subagent ran on auto")
            elif why:
                self.gate.revoke(why)
        elif kind in {"subagent.completed", "subagent.failed"}:
            if (ended := self.watch.ended(data, kind.removeprefix("subagent."))) is not None:
                self.log(event="subagent", **ended)

    def call_seen(self, data: Any) -> None:  # noqa: ANN401 - SDK usage event data
        """One billed call: Auto voids the step for anyone (TD-53); an allowed subagent's is counted as its own."""
        parent = getattr(data, "parent_tool_call_id", None)
        if getattr(data, "is_auto", None):
            self.gate.wrong_model(f"a {'subagent ' if parent else ''}call ran on auto")
            return
        if not self.watch.call(data):
            self.model_seen(getattr(data, "model", None), parent)

    def skill_seen(self, data: Any) -> None:  # noqa: ANN401 - SDK skill event data
        """Note a skill the runtime loaded; a preload from Delivery's folder counts toward the role's skills."""
        trigger = getattr(getattr(data, "trigger", None), "value", getattr(data, "trigger", None))
        name, path = getattr(data, "name", "") or "", getattr(data, "path", "") or ""
        if trigger == "context-load" and path and Path(path).resolve().is_relative_to(self.skills.resolve()):
            self.preloaded.add(name)
        self.log(event="skill", name=name, trigger=trigger)

    def _required(self) -> tuple[str, ...]:
        return preload.required(role_of(self.cfg), ui=self.cfg.ui, job=self.cfg.job)

    def preload_checked(self) -> None:
        """At a created session's first turn, every skill of the role is loaded, or the step ends (item 6)."""
        if self.checked or not self.created:
            return
        self.checked = True
        if absent := [s for s in self._required() if s not in self.preloaded]:
            self.gate.revoke(f"skills not preloaded: {', '.join(absent)}")

    def model_seen(self, model: str | None, parent: str | None) -> None:
        """Void the step when its own agent runs on another model (TD-94) or a subagent runs that may not (TD-374)."""
        if model and parent and model.lower() == "auto":
            self.gate.wrong_model("a subagent ran on auto")
        elif model and parent:
            if not self.watch.owns(parent):  # an allowed subagent's own turns are its model's, not the step's
                why = "no allowed start announced it" if self.watch.allowed else "no subagent may run"
                self.gate.revoke(f"a subagent ran; {why}")
        elif model and self.cfg.model and model != self.cfg.model:
            self.gate.wrong_model(f"a turn ran on {model}, the step needs {self.cfg.model}")

    def now(self, tool: str, arguments: Any) -> None:  # noqa: ANN401 - the SDK's JSON tool arguments
        """Overwrite the now line with this tool call, at most once per ``NOW_EVERY`` seconds."""
        if (t := time.monotonic()) - self.shown < NOW_EVERY:
            return
        self.shown = t
        at = datetime.now(UTC).isoformat(timespec="seconds")
        with contextlib.suppress(OSError):  # the now line is a hint; a failed write never ends the step
            self.cfg.journal.now({"tool": tool, "summary": watch_feed.summary(tool, arguments), "at": at})

    def permission(self, request: Any, _invocation: Any) -> Any:  # noqa: ANN401 - SDK types
        req = view(request)
        reason = decide(self.cfg.policy, req, frozenset(preload.tools(role_of(self.cfg))))
        if reason is None:
            for name in identities(req):  # a later allowed use supersedes an earlier denial of the same program
                self.run.denied.pop(name, None)
            return PermissionDecisionApproveOnce()
        reason = redact(reason)
        self.run.denials.append(reason)
        self.run.denied |= dict.fromkeys(identities(req), reason)
        request = [redact(t) for t in req.commands] or [redact(str(p)) for p in req.paths]
        self.log(event="denied", kind=req.kind, request=request, reason=reason)
        return PermissionDecisionReject(feedback=f"Denied: {reason}")

    def _handle(self, spec: tools.Spec, inv: ToolInvocation) -> ToolResult:
        text, ok = self.gate.call(spec, inv.arguments)
        kind = "success" if ok else "rejected" if text == ENDED else "failure"
        return ToolResult(text_result_for_llm=text, result_type=kind)

    async def _helped(self, spec: tools.Spec, inv: ToolInvocation) -> ToolResult:  # off the loop: deadlines hold
        return ToolResult(text_result_for_llm=(await asyncio.to_thread(self.gate.call, spec, inv.arguments))[0])

    async def _submitted(self, spec: tools.Spec, inv: ToolInvocation) -> ToolResult:  # lints off the loop (TD-87)
        return await asyncio.to_thread(self._handle, spec, inv)

    def tools(self) -> list[Tool]:
        helped = {spec for spec, _ in self.cfg.helpers}  # these answer, and the turn goes on; so does a first look
        made = partial(Tool, skip_permission=True)
        handlers = {
            s: self._helped if s in helped else self._submitted if s is self.cfg.submit else self._handle
            for s in self.gate.specs
        }
        return [
            made(s.name, s.description, partial(handlers[s], s), tool_schema.schema(s),
                 is_terminal=s not in helped and s is not self.cfg.first_look)
            for s in self.gate.specs
        ]  # fmt: skip

    def record(self, *pids: int | None, keep: bool = False) -> None:
        """Keep each new PID with its start time, None when unreadable, and persist it at once (F4)."""
        new: dict[int, float | None] = {}
        for pid in (p for p in pids if p and p not in self.run.pids):
            try:
                new[pid] = processes.started(pid)
            except psutil.NoSuchProcess:
                new.update({pid: None} if keep else {})
            except psutil.Error, OSError:
                new[pid] = None
        self.run.pids.update(new)
        if new:
            self.log(event="pids", session=self.run.session_id, pids={str(p): c for p, c in new.items()})

    def runtime(self, client: CopilotClient) -> None:
        self.proc = self.proc or getattr(client, "_cli_process", None)  # The SDK exposes no public runtime PID.
        self.run.runtime_pid = self.run.runtime_pid or getattr(self.proc, "pid", None)
        self.record(self.run.runtime_pid, keep=True)

    def record_tree(self) -> None:
        with contextlib.suppress(psutil.Error, OSError, ValueError):
            self.record(*(k.pid for k in psutil.Process(self.run.runtime_pid or -1).children(recursive=True)))

    async def snapshot(self, session: CopilotSession, budget: step_budget.Budget) -> None:
        with contextlib.suppress(Exception):
            if (listed := await budget.run(session.rpc.tasks.list, "tasks.list", POLL)) is not None:
                self.record(*(getattr(t, "pid", None) for t in listed.tasks))
        self.record_tree()

    def options(self) -> dict[str, Any]:
        role = agent(self.cfg.kind, ui=self.cfg.ui, role=self.cfg.role, judging=self.cfg.judging, job=self.cfg.job)
        if self.watch.allowed:
            role["tools"].append(subagents.LAUNCHER)
        return {
            "on_permission_request": self.permission,
            "tools": self.tools(),
            "custom_agents": [role | {"infer": False}],  # the role never starts itself as a subagent
            "agent": role["name"],
            "excluded_builtin_agents": [] if self.watch.allowed else list(subagents.BUILTINS),
            "excluded_tools": ["ask_user"],  # autopilot: the owner is asked only through ask_question (N4, N10)
            "skill_directories": preload.folders(
                role_of(self.cfg), ui=self.cfg.ui, job=self.cfg.job, folder=self.skills
            ),
            "mcp_servers": {preload.MEMORY: {"type": "local", **m}} if (m := preload.memory(self.cfg.memory)) else {},
            "enable_file_hooks": False,  # a project's agent hooks never run in a step (TD-142)
            "enable_config_discovery": False,  # nor its or the user's agents and skills (TD-167, TD-274)
            "included_builtin_skills": [],  # nor the runtime's bundled skills: only the role's own (TD-134)
            "working_directory": str(self.cfg.worktree),
            "model": self.cfg.model,
            "reasoning_effort": self.cfg.effort,
            "context_tier": "long_context" if self.cfg.context == "long" else None,
            "session_limits": {"max_ai_credits": self.cfg.credit_limit} if self.cfg.credit_limit else None,
            "on_event": self.on_event,
        }

    def replace(self) -> str | None:
        """The resumed session is absent: replace it only once every earlier recorded process is observed gone."""
        prior = verdict(self.cfg.previous, processes.alive)
        self.log(event="session-missing", previous=sorted(self.cfg.previous), gone=prior.confirmed)
        if not prior.confirmed:
            self.run.pids.update(self.cfg.previous)
            self.finish("missing", detail="session missing; earlier processes are not observed gone")
        elif (sid := self.cfg.journal.replaced()) is None:
            self.finish("missing", detail="session missing again")
        else:
            return sid
        return None

    async def wait(self, session: CopilotSession) -> None:
        await step_budget.wait(
            self, session, self.cfg.limit or DEADLINES.get(self.cfg.kind, 2400.0), time.monotonic, POLL
        )


async def _efforts(client: CopilotClient, model: str) -> bool:
    """Whether the model takes a reasoning effort; a model missing from the list, or an unread list, is trusted to."""
    try:
        listed = await _call(client.list_models(), "model list")
    except Exception:  # noqa: BLE001 - the session create then reports a refused effort itself
        return True
    found = next((m for m in listed if m.id == model), None)
    return found is None or bool(found.supported_reasoning_efforts)


async def _open(client: CopilotClient, st: _Step) -> CopilotSession | None:
    """Resume or create the session and send the first message; the answer counts as delivered once acknowledged.

    A resumed session's transcript is read before its pending answer is sent, whatever was recorded locally;
    an unread transcript sends nothing.
    """
    cfg, opts = st.cfg, st.options()
    if cfg.effort and not await _efforts(client, cfg.model):
        opts.pop("reasoning_effort")  # the runtime refuses any effort for such a model
        st.log(event="effort-omitted", model=cfg.model, effort=cfg.effort)
    sid, message, resumed, resent = cfg.session_id, cfg.message, False, True
    if cfg.resume and await _call(client.get_session_metadata(sid), "session lookup") is not None:
        session = await _call(client.resume_session(sid, **opts), "session resume", START)
        st.session, resumed = session, True
        try:
            events = await _call(session.get_events(), "transcript read")
        except Exception as exc:  # noqa: BLE001 - an unobserved transcript never authorizes a resend
            st.finish("unread", detail=f"transcript read failed ({type(exc).__name__}); the answer was not resent")
            return session
        if sent(events, message):
            message, resent = step_decisions.resumed(step_input.CONTINUE), False
    else:
        if cfg.resume:
            if (new := st.replace()) is None:
                return None
            sid, message = new, cfg.fresh
            st.run.session_id = sid
        session = await _call(client.create_session(session_id=sid, **opts), "session create", START)
        st.session, st.created = session, True
    st.log(event="session", id=sid, resumed=resumed, resent=resent, runtime=st.run.runtime_pid)
    st.billed = await usage_read(session, cfg.model) if resumed else {}
    extra = {"attachments": list(cfg.attachments)} if cfg.attachments else {}  # e.g. visual screenshots
    st.sending = True
    await _call(session.send(message, **extra), "send")
    cfg.journal.delivered()
    return session


def _refused(cfg: Session) -> str:
    """Why the step cannot start: it names no model (TD-32), or Delivery's skills for its role are missing."""
    if not cfg.model:
        return "wrong model: the step names no model (TD-32)"
    if gaps := preload.missing(role_of(cfg), ui=cfg.ui, job=cfg.job, folder=cfg.skills):
        return f"Delivery's worker skills are missing: {', '.join(gaps)}"
    return ""


async def run(cfg: Session) -> Run:
    """Open or resume the session, send the message, await its result, tear down within bounds, then the watcher."""
    st = _Step(cfg, asyncio.get_running_loop())
    st.feed = watch_feed.opened(cfg.watch, cfg.worktree, lambda: st.run.session_id, st.watch)
    return await watch_feed.around(st.feed, _run(st))


async def _run(st: _Step) -> Run:
    cfg = st.cfg
    if refused := _refused(cfg):
        st.finish("error", detail=refused)
        st.run.termination = Termination(confirmed=True)
        return st.run
    async with sdk_teardown.managed(st):
        try:
            async with asyncio.timeout((cfg.limit or DEADLINES.get(cfg.kind, 2400.0)) + START + CALL):
                client = st.client = CopilotClient(connection=RuntimeConnection.for_stdio(path=cli_path()))
                await _call(client.start(), "runtime start", START)
                st.runtime(client)
                session = await _open(client, st)
                if session is not None:
                    await st.wait(session)
        except TimeoutError as exc:
            st.finish("deadline", detail=str(exc) or "step deadline")
        except Exception as exc:  # noqa: BLE001 - any SDK failure ends the step with retry after teardown
            st.finish("error", detail=f"{type(exc).__name__}: {exc}"[:300])
        session = st.session
        st.run.usage = await usage_read(session, cfg.model) if session else {}
        limit_reached(st.run, cfg.credit_limit)
        st.run.subagents = st.watch.report()
        await _proven(st, session)
    return st.run


async def _proven(st: _Step, session: Any) -> None:  # noqa: ANN401 - the SDK session
    """Settle the model check from the usage alone: verified, mismatch or unknown (TD-94).

    Every usage read is checked for models nobody may use. A processed ending needs its own model's tokens to have
    grown; the usage is read once more before it counts as unknown, since one read may come before the runtime's
    metrics catch up. A mismatch, found here or by an event meanwhile, is final.
    """
    if not st.sending:
        return
    for again in (False, True):
        if wrong := sorted(set(unexpected_models(st.billed, st.run.usage, st.cfg.model)) - st.watch.child_models()):
            st.gate.wrong_model(f"the usage names {', '.join(wrong)}, the step needs {st.cfg.model}")
        if st.run.model_check == "mismatch":
            return
        why, proof = unread(st.billed, st.run.usage), unproven(st.billed, st.run.usage, st.cfg.model)
        if again or why or not proof or st.run.ending not in PROVEN:
            break
        await asyncio.sleep(USAGE_PAUSE)
        st.run.usage = await usage_read(session, st.cfg.model)
    st.run.usage_unread = why or (proof if st.run.ending in PROVEN else "")
    st.run.model_check = "unknown" if why or proof else "verified"
    if st.run.usage_unread:
        st.log(event="usage-unread", reason=st.run.usage_unread)
