"""One bounded worker session on the installed Copilot CLI; it ends at a result-tool call or deadline (D4 §3.2, P4)."""

from __future__ import annotations

import asyncio
import contextlib
import os
import shutil
import signal
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import partial
from importlib.resources import files
from typing import TYPE_CHECKING, Any

import psutil
from copilot import CopilotClient, RuntimeConnection
from copilot.rpc import PermissionDecisionApproveOnce, PermissionDecisionReject, TasksCancelRequest
from copilot.tools import Tool, ToolInvocation, ToolResult

from owlbear_delivery_next import processes, prompts, tools
from owlbear_delivery_next.mask import redact
from owlbear_delivery_next.models import StepKind
from owlbear_delivery_next.permissions import decide, identities, view
from owlbear_delivery_next.processes import Termination, verdict
from owlbear_delivery_next.results import ENDED, Gate
from owlbear_delivery_next.session_result import Run, note_quota

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Iterable
    from pathlib import Path

    from copilot.session import CopilotSession

    from owlbear_delivery_next.models import ItemRef
    from owlbear_delivery_next.permissions import Policy
    from owlbear_delivery_next.processes import Pids
    from owlbear_delivery_next.session_result import Ending

DEADLINES = {StepKind.PLAN: 900.0, StepKind.BUILD: 1200.0, StepKind.REVIEW: 600.0, StepKind.CHECK: 900.0}
ROLES = {StepKind.PLAN: "planner", StepKind.BUILD: "builder", StepKind.REVIEW: "reviewer", StepKind.CHECK: "builder"}
POLL = 5.0
SETTLE = 10.0
START = 60.0  # runtime start, session create or resume
CALL = 30.0  # one request while the step runs
STOP_CALL = 10.0  # one teardown request
GRACE = 5.0  # between terminate and kill
NOW_LIMIT = 80  # characters of the now line's summary
NOW_EVERY = 1.0  # seconds between now-line writes
USAGE_PAUSE = 2.0  # seconds before the one repeated usage read (TD-54)


def cli_path() -> str:
    """Return the installed Copilot CLI; the SDK's own runtime download fails behind the proxy (P3, S02)."""
    if not (path := os.environ.get("COPILOT_CLI_PATH") or shutil.which("copilot")):
        msg = "Copilot CLI not found; install it or set COPILOT_CLI_PATH"
        raise FileNotFoundError(msg)
    return path


def agent(kind: StepKind) -> dict[str, Any]:
    """Return the role's custom agent from the package's ``agents/`` prose."""
    text = files("owlbear_delivery_next").joinpath("agents", f"{ROLES[kind]}.md").read_text(encoding="utf-8")
    _, front, body = text.split("---", 2)
    meta = dict(line.split(":", 1) for line in front.strip().splitlines())
    return {"name": meta["name"].strip(), "description": meta["description"].strip(), "prompt": body.strip()}


@dataclass(frozen=True)
class Journal:
    """Durable writes the runner makes under the Change lock as the step goes, so a killed runner leaves them."""

    event: Callable[[dict[str, Any]], None] = lambda _e: None
    delivered: Callable[[], None] = lambda: None
    replaced: Callable[[], str | None] = lambda: None
    now: Callable[[dict[str, Any]], None] = lambda _e: None  # the latest tool call, overwritten; not activity


def summary(tool: str, arguments: Any) -> str:  # noqa: ANN401 - the SDK's JSON tool arguments
    """One short, redacted line for a tool call: ``ran <command>`` or ``<tool> <target>``."""
    args = arguments if isinstance(arguments, dict) else {}
    if command := args.get("command"):
        text = f"ran {command}"
    else:
        target = next((args[k] for k in ("path", "file_path", "pattern", "query", "url") if args.get(k)), "")
        text = f"{tool} {target}"
    text = " ".join(redact(str(text)).split())
    return text if len(text) <= NOW_LIMIT else text[: NOW_LIMIT - 1] + "…"


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
    model: str | None = None
    effort: str | None = None  # the SDK's reasoning effort
    fresh: str = ""  # first message of a replacement session: stored context plus the pending answer
    previous: Pids = field(default_factory=dict)  # PIDs earlier runners recorded for this session
    journal: Journal = field(default_factory=Journal)
    attachments: tuple[dict[str, str], ...] = ()  # blob attachments sent with the first message


def sent(events: Iterable[Any], message: str) -> bool:
    """Whether a session transcript already holds *message* as a user message."""
    users = (getattr(e.data, "content", "") or "" for e in events if getattr(e.type, "value", e.type) == "user.message")
    return any(message.strip() in c for c in users)


class _Step:
    def __init__(self, cfg: Session, loop: asyncio.AbstractEventLoop) -> None:
        self.cfg, self.loop, self.run, self.proc = cfg, loop, Run(cfg.session_id), None
        self.turn = self.idle = False
        self.subagent_models: set[str] = set()
        self.billed: dict[str, Any] = {"error": "not read"}  # usage before this invocation's first send
        self.session: CopilotSession | None = None  # kept as soon as it opens, even if the first send fails
        self.sending = False  # a first message was sent or attempted, so a model may have run
        self.gate = Gate(cfg, self.run, self.log, self._wake)
        self.changed = asyncio.Event()
        self.shown = float("-inf")  # monotonic time of the last now-line write

    @property
    def done(self) -> bool:
        return self.gate.done

    def _wake(self) -> None:
        self.loop.call_soon_threadsafe(self.changed.set)

    def log(self, **event: Any) -> None:  # noqa: ANN401 - JSON values; the SDK calls handlers on this loop
        self.cfg.journal.event({"at": datetime.now(UTC).isoformat(timespec="seconds"), **event})

    def finish(self, ending: Ending, payload: tools.Args | None = None, detail: str = "") -> None:
        self.gate.finish(ending, payload, detail)

    def on_event(self, ev: Any) -> None:  # noqa: ANN401 - SDK session event
        kind = getattr(ev.type, "value", str(ev.type))
        if kind == "assistant.turn_start":
            self.turn = True
            self.model_seen(getattr(ev.data, "model", None), getattr(ev.data, "parent_tool_call_id", None))
        elif kind == "session.idle" and self.turn:
            self.turn, self.idle = False, True
            self._wake()
        elif kind == "tool.execution_start":
            self.now(getattr(ev.data, "tool_name", "") or "tool", getattr(ev.data, "arguments", None))
        elif kind in {"session.quota_observation", "session.error"}:
            note_quota(self.run, kind, ev.data)
        elif kind == "session.auto_mode_resolved":
            self.gate.revoke("wrong model: the runtime resolved auto")
        elif kind == "assistant.message":
            self.model_seen(getattr(ev.data, "model", None), getattr(ev.data, "parent_tool_call_id", None))
        elif kind == "assistant.usage":
            self.call_seen(ev.data)
        elif kind == "subagent.started":
            source = getattr(ev.data, "model_selection_source", None)
            model = getattr(ev.data, "model", None)
            if model and model.lower() == "auto":
                self.gate.revoke("wrong model: a subagent ran on auto")
            else:  # logged only; the subagent's own calls and messages decide what it may use
                self.log(event="subagent-start", model=model, source=getattr(source, "value", source))

    def call_seen(self, data: Any) -> None:  # noqa: ANN401 - SDK usage event data
        """One billed call: Auto voids the step for anyone (TD-53); the main agent's own calls name its model."""
        parent = getattr(data, "parent_tool_call_id", None)
        if getattr(data, "is_auto", None):
            self.gate.revoke(f"wrong model: a {'subagent ' if parent else ''}call ran on auto")
            return
        self.model_seen(getattr(data, "model", None), parent)

    def model_seen(self, model: str | None, parent: str | None) -> None:
        """Void the step when its own agent runs on another model; a subagent may use any named model (TD-53)."""
        if model and parent and model.lower() == "auto":
            self.gate.revoke("wrong model: a subagent ran on auto")
            return
        if not model or not self.cfg.model or model == self.cfg.model:
            return
        if parent:
            self.subagent_models.add(model)
            self.log(event="subagent-model", model=model)
        else:
            self.gate.revoke(f"wrong model: a turn ran on {model}, the step needs {self.cfg.model}")

    def now(self, tool: str, arguments: Any) -> None:  # noqa: ANN401 - the SDK's JSON tool arguments
        """Overwrite the now line with this tool call, at most once per ``NOW_EVERY`` seconds."""
        if (t := time.monotonic()) - self.shown < NOW_EVERY:
            return
        self.shown = t
        at = datetime.now(UTC).isoformat(timespec="seconds")
        with contextlib.suppress(OSError):  # the now line is a hint; a failed write never ends the step
            self.cfg.journal.now({"tool": tool, "summary": summary(tool, arguments), "at": at})

    def permission(self, request: Any, _invocation: Any) -> Any:  # noqa: ANN401 - SDK types
        req = view(request)
        reason = decide(self.cfg.policy, req)
        if reason is None:
            for name in identities(req):  # a later allowed use supersedes an earlier denial of the same program
                self.run.denied.pop(name, None)
            return PermissionDecisionApproveOnce()
        reason = redact(reason)
        self.run.denials.append(reason)
        self.run.denied |= dict.fromkeys(identities(req), reason)
        request = [redact(t) for t, _ in req.commands] or [redact(str(p)) for p in req.paths]
        self.log(event="denied", kind=req.kind, request=request, reason=reason)
        return PermissionDecisionReject(feedback=f"Denied: {reason}")

    def _handle(self, spec: tools.Spec, inv: ToolInvocation) -> ToolResult:
        text, ok = self.gate.call(spec, inv.arguments)
        if ok:
            return ToolResult(text_result_for_llm=text)
        return ToolResult(text_result_for_llm=text, result_type="rejected" if text == ENDED else "failure")

    def tools(self) -> list[Tool]:
        return [
            Tool(
                s.name, s.description, partial(self._handle, s), tools.schema(s), skip_permission=True, is_terminal=True
            )
            for s in self.gate.specs
        ]

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

    async def snapshot(self, session: CopilotSession) -> None:
        with contextlib.suppress(Exception):
            listed = (await _call(session.rpc.tasks.list(), "tasks.list")).tasks
            self.record(*(getattr(t, "pid", None) for t in listed))
        self.record_tree()

    def options(self) -> dict[str, Any]:
        role = agent(self.cfg.kind)
        return {
            "on_permission_request": self.permission,
            "tools": self.tools(),
            "custom_agents": [role],
            "agent": role["name"],
            "excluded_tools": ["ask_user"],  # autopilot: the owner is asked only through ask_question (N4, N10)
            "working_directory": str(self.cfg.worktree),
            "model": self.cfg.model,
            "reasoning_effort": self.cfg.effort,
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
        end, reminded = time.monotonic() + DEADLINES.get(self.cfg.kind, 1200.0), False
        while not self.done:
            left = end - time.monotonic()
            if left <= 0:
                self.finish("deadline", detail="step deadline")
                break
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(self.changed.wait(), min(POLL, left))
            self.changed.clear()
            if self.done:
                break
            await self.snapshot(session)
            if self.idle and not self.done:
                self.idle = False
                if reminded:
                    self.finish("no-result")
                else:
                    reminded = True
                    self.log(event="reminder")
                    await _call(session.send(prompts.REMINDER), "send")


async def _call[T](aw: Awaitable[T], what: str, limit: float = CALL) -> T:
    try:
        return await asyncio.wait_for(aw, limit)
    except TimeoutError as exc:
        raise TimeoutError(f"{what} did not answer within {limit:.0f} s") from exc  # noqa: TRY003, EM102


def unexpected_models(
    before: dict[str, Any], after: dict[str, Any], model: str | None, subagents: set[str]
) -> list[str]:
    """Models billed during this invocation that are neither the step's nor a logged subagent's.

    An unknown baseline (a failed read on resume) or a failed final read checks nothing; the events still do.
    """
    if "error" in before or "error" in after:
        return []
    old, new = before.get("models") or {}, after.get("models") or {}
    grew = {m for m, v in new.items() if m not in old or (v or {}).get("tokens") != (old[m] or {}).get("tokens")}
    return sorted(grew - {model} - subagents)


async def _usage(session: CopilotSession, requested: str | None) -> dict[str, Any]:
    try:
        m = await _call(session.rpc.usage.get_metrics(), "usage", STOP_CALL)
    except Exception as exc:  # noqa: BLE001 - experimental RPC; usage is reported, never required
        return {"error": type(exc).__name__}
    nano = getattr(m, "total_nano_aiu", None)
    models = {
        name: {
            "credits": (getattr(mm, "total_nano_aiu", None) or 0) / 1e9,
            "tokens": mm.usage.input_tokens + mm.usage.output_tokens,
        }
        for name, mm in (getattr(m, "model_metrics", None) or {}).items()
    }
    mismatch = bool(requested and models and requested not in models)
    return {"credits": None if nano is None else nano / 1e9, "models": models, "model_mismatch": mismatch}


async def _usage_read(session: CopilotSession, requested: str | None) -> dict[str, Any]:
    """The usage, read once more after a pause when the first read fails (TD-54)."""
    usage = await _usage(session, requested)
    if "error" in usage:
        await asyncio.sleep(USAGE_PAUSE)
        usage = await _usage(session, requested)
    return usage


def unread(before: dict[str, Any], after: dict[str, Any]) -> str:
    """Why the model check cannot run for this invocation; empty when both reads it needs worked (TD-54)."""
    if "error" in before:
        return f"the usage before the resumed turn could not be read ({before['error']})"
    if "error" in after:
        return f"the usage at the step's end could not be read ({after['error']})"
    return ""


async def _settle(recorded: Pids, problems: list[str], limit: float | None = None) -> Termination:
    end = time.monotonic() + (SETTLE if limit is None else limit)
    # Polls the OS process table; there is no event to wait on.
    while (  # noqa: ASYNC110
        not (result := verdict(recorded, processes.alive, problems)).confirmed and time.monotonic() < end
    ):
        await asyncio.sleep(0.5)
    return result


async def _force(st: _Step, why: str) -> None:
    """Runtime-stop fallback: terminate, then kill the runtime (an unreaped child), recorded PIDs and their groups."""
    st.log(event="force-stop", reason=why, runtime_pid=st.run.runtime_pid)
    with contextlib.suppress(OSError, AttributeError):
        st.proc.terminate()
    processes.kill(st.run.pids, signal.SIGTERM)
    await _settle(st.run.pids, [], GRACE)
    with contextlib.suppress(OSError, AttributeError):
        st.proc.kill()
    processes.kill(st.run.pids, signal.SIGKILL)


async def _teardown(client: CopilotClient, session: CopilotSession | None, st: _Step) -> Termination:  # noqa: C901
    """(1) list, (2) cancel tasks, (3) wait, (4) disconnect, (5) stop, else signal; all bounded, then observe PIDs."""
    problems: list[str] = []
    st.runtime(client)
    if session is not None:
        listed: dict[int, float | None] = {}
        try:
            tasks = (await _call(session.rpc.tasks.list(), "tasks.list", STOP_CALL)).tasks
        except Exception as exc:  # noqa: BLE001 - any failure leaves termination unverified
            problems.append(f"tasks.list failed ({type(exc).__name__})")
            tasks = []
        for task in tasks:
            st.record(getattr(task, "pid", None))
            if pid := getattr(task, "pid", None):
                listed[pid] = st.run.pids.get(pid)
            if str(getattr(task.status, "value", task.status)) in {"running", "idle"}:
                try:
                    await _call(session.rpc.tasks.cancel(TasksCancelRequest(id=task.id)), "tasks.cancel", STOP_CALL)
                except Exception as exc:  # noqa: BLE001
                    problems.append(f"tasks.cancel {task.id} failed ({type(exc).__name__})")
        st.record_tree()
        st.log(event="tasks", listed=sorted(listed), problems=list(problems))
        await _settle(listed, [])
        try:
            await _call(session.disconnect(), "disconnect", STOP_CALL)
        except Exception as exc:  # noqa: BLE001
            problems.append(f"disconnect failed ({type(exc).__name__})")
    try:
        await _call(client.stop(), "runtime stop", STOP_CALL)
    except Exception as exc:  # noqa: BLE001 - errors and timeouts alike fall back to signals
        await _force(st, f"runtime stop failed ({type(exc).__name__})")
    rt = st.run.runtime_pid
    if rt is None:
        problems.append("runtime PID unknown")
    elif processes.alive(rt, st.run.pids.get(rt)) is not False:
        await _force(st, "runtime still present after stop")
    return await _settle(dict(st.run.pids), problems)


async def _open(client: CopilotClient, st: _Step) -> CopilotSession | None:
    """Resume or create the session and send the first message; the answer counts as delivered once acknowledged.

    A resumed session's transcript is read before its pending answer is sent, whatever was recorded locally;
    an unread transcript sends nothing.
    """
    cfg, opts = st.cfg, st.options()
    sid, message, resumed = cfg.session_id, cfg.message, False
    if cfg.resume and await _call(client.get_session_metadata(sid), "session lookup") is not None:
        session = await _call(client.resume_session(sid, **opts), "session resume", START)
        st.session, resumed = session, True
        try:
            events = await _call(session.get_events(), "transcript read")
        except Exception as exc:  # noqa: BLE001 - an unobserved transcript never authorizes a resend
            st.finish("unread", detail=f"transcript read failed ({type(exc).__name__}); the answer was not resent")
            return session
        if sent(events, message):
            message = prompts.CONTINUE
    else:
        if cfg.resume:
            if (new := st.replace()) is None:
                return None
            sid, message = new, cfg.fresh
            st.run.session_id = sid
        session = await _call(client.create_session(session_id=sid, **opts), "session create", START)
        st.session = session
    st.log(event="session", id=sid, resumed=resumed, resent=message != prompts.CONTINUE, runtime=st.run.runtime_pid)
    st.billed = await _usage_read(session, cfg.model) if resumed else {}
    extra = {"attachments": list(cfg.attachments)} if cfg.attachments else {}  # e.g. visual screenshots
    st.sending = True
    await _call(session.send(message, **extra), "send")
    cfg.journal.delivered()
    return session


async def run(cfg: Session) -> Run:
    """Open or resume the session, send the message, wait for the result boundary, then tear down within bounds."""
    st = _Step(cfg, asyncio.get_running_loop())
    if not cfg.model:
        st.finish("error", detail="wrong model: the step names no model (TD-32)")
        st.run.termination = Termination(confirmed=True)
        return st.run
    client, session = None, None
    try:
        async with asyncio.timeout(DEADLINES.get(cfg.kind, 1200.0) + START + CALL):
            client = CopilotClient(connection=RuntimeConnection.for_stdio(path=cli_path()))
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
    st.run.usage = await _usage_read(session, cfg.model) if session else {}
    st.run.usage_unread = unread(st.billed, st.run.usage) if st.sending else ""
    if st.run.usage_unread:
        st.log(event="usage-unread", reason=st.run.usage_unread)
    if wrong := unexpected_models(st.billed, st.run.usage, cfg.model, st.subagent_models):
        st.gate.revoke(f"wrong model: the usage names {', '.join(wrong)}, the step needs {cfg.model}")
    st.run.termination = await _teardown(client, session, st) if client else Termination(confirmed=True)
    return st.run
