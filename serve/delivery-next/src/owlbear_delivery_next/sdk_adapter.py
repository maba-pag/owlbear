"""One bounded worker session on the installed Copilot CLI; it ends at a result-tool call or deadline (D4 §3.2, P4)."""

from __future__ import annotations

import asyncio
import contextlib
import os
import shutil
import signal
import subprocess
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
from owlbear_delivery_next.permissions import decide, view
from owlbear_delivery_next.processes import Termination, verdict
from owlbear_delivery_next.session_result import Run, note_quota

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Iterable
    from pathlib import Path

    from copilot.session import CopilotSession

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
    item: str | None = None  # the conversation item kind a build task answers, if any
    model: str | None = None
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
        self.done = self.turn = self.idle = False
        self.changed = asyncio.Event()
        self.shown = float("-inf")  # monotonic time of the last now-line write

    def _wake(self) -> None:
        self.loop.call_soon_threadsafe(self.changed.set)

    def log(self, **event: Any) -> None:  # noqa: ANN401 - JSON values; the SDK calls handlers on this loop
        self.cfg.journal.event({"at": datetime.now(UTC).isoformat(timespec="seconds"), **event})

    def finish(self, ending: Ending, payload: tools.Args | None = None, detail: str = "") -> None:
        if not self.done:
            self.done, self.run.ending, self.run.payload, self.run.detail = True, ending, payload, detail
        self._wake()

    def on_event(self, ev: Any) -> None:  # noqa: ANN401 - SDK session event
        kind = getattr(ev.type, "value", str(ev.type))
        if kind == "assistant.turn_start":
            self.turn = True
        elif kind == "session.idle" and self.turn:
            self.turn, self.idle = False, True
            self._wake()
        elif kind == "tool.execution_start":
            self.now(getattr(ev.data, "tool_name", "") or "tool", getattr(ev.data, "arguments", None))
        elif kind in {"session.quota_observation", "session.error"}:
            note_quota(self.run, kind, ev.data)

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
            return PermissionDecisionApproveOnce()
        reason = redact(reason)
        self.run.denials.append(reason)
        request = [redact(t) for t, _ in req.commands] or [redact(str(p)) for p in req.paths]
        self.log(event="denied", kind=req.kind, request=request, reason=reason)
        return PermissionDecisionReject(feedback=f"Denied: {reason}")

    def _check_result(self, args: tools.Args) -> list[str]:
        try:
            tree = self.cfg.observe()
        except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
            return [f"changes: the worktree could not be read ({type(exc).__name__}); try again"]
        cfg = self.cfg
        errors = tools.check_result(
            args, tree, cfg.checks, cfg.policy.root, cfg.scope, cfg.item, visual=bool(cfg.attachments)
        )
        self.run.head = None if errors else tree.head
        return errors

    def _handle(self, spec: tools.Spec, inv: ToolInvocation) -> ToolResult:
        args, errors = tools.parse(spec.model, inv.arguments)
        if args is not None:
            errors = tools.check_question(args) if isinstance(args, tools.AskQuestion) else []
            errors += self._check_result(args) if spec is self.cfg.submit else []
        read = list(args.covered_paths) if isinstance(args, tools.ReviewResult) else []  # evidence, not coverage
        self.log(event="tool", tool=spec.name, accepted=not errors, errors=errors, **({"read": read} if read else {}))
        if self.done:
            return ToolResult(text_result_for_llm="The step has already ended. Stop now.", result_type="rejected")
        if errors:
            self.run.invalid += 1
            if self.run.invalid >= tools.INVALID_LIMIT:
                self.finish("invalid", detail="; ".join(errors)[:300])
            lines = "\n".join(f"- {e}" for e in errors)
            text = f"Rejected. Fix each field, then call again:\n{lines}"
            return ToolResult(text_result_for_llm=text, result_type="failure")
        self.finish(spec.ending, args)
        return ToolResult(text_result_for_llm="Accepted. Your step has ended: stop now and start nothing else.")

    def tools(self) -> list[Tool]:
        return [
            Tool(
                s.name, s.description, partial(self._handle, s), tools.schema(s), skip_permission=True, is_terminal=True
            )
            for s in (self.cfg.submit, tools.ASK, tools.PREMISE)
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
            "working_directory": str(self.cfg.worktree),
            "model": self.cfg.model,
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
        resumed = True
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
    st.log(event="session", id=sid, resumed=resumed, resent=message != prompts.CONTINUE, runtime=st.run.runtime_pid)
    extra = {"attachments": list(cfg.attachments)} if cfg.attachments else {}  # e.g. visual screenshots
    await _call(session.send(message, **extra), "send")
    cfg.journal.delivered()
    return session


async def run(cfg: Session) -> Run:
    """Open or resume the session, send the message, wait for the result boundary, then tear down within bounds."""
    st = _Step(cfg, asyncio.get_running_loop())
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
    st.run.usage = await _usage(session, cfg.model) if session else {}
    st.run.termination = await _teardown(client, session, st) if client else Termination(confirmed=True)
    return st.run
