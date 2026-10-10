"""One worker session on the installed Copilot CLI: agent, model, tools, permissions, result boundary and teardown.

The step ends at an accepted result-tool call or its deadline, never on ``session.idle`` alone (D4 §3.2, P4).
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import shutil
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from importlib.resources import files
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

import psutil
from copilot import CopilotClient, RuntimeConnection
from copilot.rpc import PermissionDecisionApproveOnce, PermissionDecisionReject, TasksCancelRequest
from copilot.tools import Tool, ToolInvocation, ToolResult

from owlbear_delivery_next import prompts, tools
from owlbear_delivery_next.loop import StepResult, cause_key
from owlbear_delivery_next.models import ErrorKind, Exit, Option, Question, StepKind, Stop

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

    from copilot.session import CopilotSession

DEADLINES = {StepKind.BUILD: 1200.0}
ROLES = {StepKind.BUILD: "builder"}
POLL = 5.0
SETTLE = 10.0
GIT_BUILD = tuple(
    f"git {c}" for c in ("add", "commit", "merge", "status", "diff", "log", "restore", "show", "rev-parse")
)
DENIED = ("git push", "git config", "git -c", "gh", "sudo")
type Ending = Literal["result", "ask", "premise", "invalid", "no-result", "deadline", "error"]


@dataclass(frozen=True)
class Policy:
    """Allow list of one step kind; every other request is denied and logged (D4 §3.6)."""

    root: Path
    commands: tuple[str, ...]
    write: bool = True


@dataclass(frozen=True)
class Request:
    """The parts of a permission request the policy judges; shell commands carry the runtime's read-only flag."""

    kind: str
    commands: tuple[tuple[str, bool], ...] = ()
    paths: tuple[str, ...] = ()
    urls: bool = False
    tool: str = ""


def _matches(text: str, prefixes: Sequence[str]) -> bool:
    words = text.split()
    return any(words[: len(p.split())] == p.split() for p in prefixes)


def _inside(root: Path, path: str) -> bool:
    p = Path(path).expanduser()
    try:
        return (p if p.is_absolute() else root / p).resolve().is_relative_to(root.resolve())
    except OSError, ValueError:
        return False


def decide(policy: Policy, req: Request) -> str | None:  # noqa: PLR0911 - one answer per request kind
    """Return None to allow, or the denial reason the agent and the activity log see."""
    if req.kind == "custom-tool":
        return None if req.tool in {s.name for s in tools.SPECS} else f"tool {req.tool} is not allowed"
    if req.kind in {"read", "write"}:
        if req.kind == "write" and not policy.write:
            return "writes are not allowed in this step"
        outside = [p for p in req.paths if not _inside(policy.root, p)]
        return f"{req.kind} outside the worktree: {outside[0]}" if outside else None if req.paths else "no path"
    if req.kind != "shell":
        return f"{req.kind} requests are not allowed in this step"
    if req.urls:
        return "shell commands that reach URLs are not allowed"
    for text, read_only in req.commands or (("", False),):
        if _matches(text, DENIED):
            return f"`{text}` is denied"
        if _matches(text, policy.commands) or (read_only and all(_inside(policy.root, p) for p in req.paths)):
            continue
        return f"`{text}` is not in this step's allow list"
    return None


def _view(r: Any) -> Request:  # noqa: ANN401 - one of the SDK's permission request classes
    kind = getattr(r, "kind", type(r).__name__)
    if kind == "shell":
        ro = tuple(c.identifier for c in r.commands if c.read_only)
        texts = [s.full_command_text for s in r.command_segments or ()] or [c.identifier for c in r.commands]
        commands = tuple((t, _matches(t, ro)) for t in texts or [r.full_command_text])
        return Request(kind, commands, tuple(r.possible_paths or ()), bool(r.possible_urls))
    if kind in {"read", "write"}:
        path = r.resolved_path or getattr(r, "path", None) or getattr(r, "file_name", "")
        return Request(kind, paths=(path,) if path else ())
    return Request(kind, tool=getattr(r, "tool_name", ""))


@dataclass(frozen=True)
class Termination:
    """Whether every listed or recorded process of the step is gone; anything unobserved keeps it unverified."""

    confirmed: bool
    survivors: tuple[int, ...] = ()
    unknown: tuple[int, ...] = ()
    problems: tuple[str, ...] = ()


def verdict(
    recorded: Mapping[int, float | None],
    alive: Callable[[int, float | None], bool | None],
    problems: Sequence[str] = (),
) -> Termination:
    """Decide confirmed or unverified from one observation per recorded PID (True alive, None unknown)."""
    states = {pid: alive(pid, created) for pid, created in recorded.items()}
    survivors = tuple(sorted(p for p, s in states.items() if s))
    unknown = tuple(sorted(p for p, s in states.items() if s is None))
    return Termination(not (survivors or unknown or problems), survivors, unknown, tuple(problems))


def alive(pid: int, created: float | None) -> bool | None:
    """Observe one recorded process: a zombie or a reused PID is gone; an unreadable one is unknown."""
    try:
        p = psutil.Process(pid)
        if p.status() == psutil.STATUS_ZOMBIE:
            return False
        return created is None or abs(p.create_time() - created) < 1.0
    except psutil.NoSuchProcess:
        return False
    except psutil.Error, OSError:
        return None


def cli_path() -> str:
    """Return the installed Copilot CLI; the SDK's own runtime download fails behind the proxy (P3, S02)."""
    path = os.environ.get("COPILOT_CLI_PATH") or shutil.which("copilot")
    if not path:
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
    model: str | None = None


@dataclass
class Run:
    """What one session produced and how it ended."""

    session_id: str
    ending: Ending = "error"
    payload: tools.Args | None = None
    detail: str = ""
    runtime_pid: int | None = None
    pids: dict[int, float | None] = field(default_factory=dict)
    usage: dict[str, Any] = field(default_factory=dict)
    termination: Termination | None = None
    events: list[dict[str, Any]] = field(default_factory=list)
    delivered: bool = False
    invalid: int = 0


class _Step:
    def __init__(self, cfg: Session, loop: asyncio.AbstractEventLoop) -> None:
        self.cfg, self.loop, self.run = cfg, loop, Run(cfg.session_id)
        self.done = self.turn = self.idle = False
        self.changed = asyncio.Event()

    def _wake(self) -> None:
        self.loop.call_soon_threadsafe(self.changed.set)

    def log(self, **event: Any) -> None:  # noqa: ANN401 - JSON values
        self.run.events.append({"at": datetime.now(UTC).isoformat(timespec="seconds"), **event})

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

    def permission(self, request: Any, _invocation: Any) -> Any:  # noqa: ANN401 - SDK types
        req = _view(request)
        reason = decide(self.cfg.policy, req)
        if reason is None:
            return PermissionDecisionApproveOnce()
        self.log(event="denied", kind=req.kind, request=[t for t, _ in req.commands] or list(req.paths), reason=reason)
        return PermissionDecisionReject(feedback=f"Denied: {reason}")

    def _check_build(self, args: tools.Args) -> list[str]:
        try:
            tree = self.cfg.observe()
        except (OSError, RuntimeError, ValueError) as exc:
            return [f"commit: the worktree could not be read ({type(exc).__name__}); try again"]
        return tools.check_build(args, tree, self.cfg.checks) if isinstance(args, tools.BuildResult) else []

    def _handle(self, spec: tools.Spec, ending: Ending, inv: ToolInvocation) -> ToolResult:
        args, errors = tools.parse(spec.model, inv.arguments)
        if args is not None:
            errors = self._check_build(args) if spec is tools.SUBMIT else []
            errors += tools.check_question(args) if isinstance(args, tools.AskQuestion) else []
        self.log(event="tool", tool=spec.name, accepted=not errors, errors=errors)
        if self.done:
            return ToolResult(text_result_for_llm="The step has already ended. Stop now.", result_type="rejected")
        if errors:
            self.run.invalid += 1
            if self.run.invalid >= tools.INVALID_LIMIT:
                self.finish("invalid", detail="; ".join(errors)[:300])
            lines = "\n".join(f"- {e}" for e in errors)
            return ToolResult(
                text_result_for_llm=f"Rejected. Fix each field, then call again:\n{lines}", result_type="failure"
            )
        self.finish(ending, args)
        return ToolResult(text_result_for_llm="Accepted. Your step has ended: stop now and start nothing else.")

    def tools(self) -> list[Tool]:
        endings: dict[str, Ending] = {tools.SUBMIT.name: "result", tools.ASK.name: "ask", tools.PREMISE.name: "premise"}
        return [
            Tool(
                name=s.name,
                description=s.description,
                handler=lambda inv, s=s: self._handle(s, endings[s.name], inv),
                parameters=tools.schema(s),
                skip_permission=True,
                is_terminal=True,
            )
            for s in tools.SPECS
        ]

    def record(self, pid: int | None) -> None:
        with contextlib.suppress(psutil.Error, OSError):
            if pid and pid not in self.run.pids:
                self.run.pids[pid] = psutil.Process(pid).create_time()

    def record_tree(self) -> None:
        with contextlib.suppress(psutil.Error, OSError):
            for child in psutil.Process(self.run.runtime_pid).children(recursive=True):
                with contextlib.suppress(psutil.Error, OSError):
                    self.run.pids.setdefault(child.pid, child.create_time())

    async def snapshot(self, session: CopilotSession) -> None:
        with contextlib.suppress(Exception):
            for task in (await session.rpc.tasks.list()).tasks:
                self.record(getattr(task, "pid", None))
        self.record_tree()

    async def wait(self, session: CopilotSession) -> None:
        end, reminded = time.monotonic() + DEADLINES.get(self.cfg.kind, 1200.0), False
        while not self.done:
            left = end - time.monotonic()
            if left <= 0:
                self.finish("deadline")
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
                    await session.send(prompts.REMINDER)


async def _usage(session: CopilotSession | None, requested: str | None) -> dict[str, Any]:
    if session is None:
        return {}
    try:
        m = await session.rpc.usage.get_metrics()
    except Exception as exc:  # noqa: BLE001 - experimental RPC; usage is reported, never required
        return {"error": type(exc).__name__}
    nano = getattr(m, "total_nano_aiu", None)
    models = sorted((getattr(m, "model_metrics", None) or {}).keys())
    return {
        "credits": None if nano is None else nano / 1e9,
        "models": models,
        "model_mismatch": bool(requested and models and requested not in models),
    }


async def _settle(recorded: dict[int, float | None], problems: list[str]) -> Termination:
    end = time.monotonic() + SETTLE
    # Polls the OS process table; there is no event to wait on.
    while not (result := verdict(recorded, alive, problems)).confirmed and time.monotonic() < end:  # noqa: ASYNC110
        await asyncio.sleep(0.5)
    return result


async def _teardown(client: CopilotClient, session: CopilotSession | None, st: _Step) -> Termination:
    """(1) list tasks, (2) cancel each, (3) wait for listed PIDs, (4) disconnect, (5) runtime and recorded PIDs gone."""
    problems: list[str] = []
    if session is not None:
        listed: dict[int, float | None] = {}
        try:
            tasks = (await session.rpc.tasks.list()).tasks
        except Exception as exc:  # noqa: BLE001 - any failure leaves termination unverified
            problems.append(f"tasks.list failed ({type(exc).__name__})")
            tasks = []
        for task in tasks:
            st.record(getattr(task, "pid", None))
            if pid := getattr(task, "pid", None):
                listed[pid] = st.run.pids.get(pid)
            if str(getattr(task.status, "value", task.status)) in {"running", "idle"}:
                try:
                    await session.rpc.tasks.cancel(TasksCancelRequest(id=task.id))
                except Exception as exc:  # noqa: BLE001
                    problems.append(f"tasks.cancel {task.id} failed ({type(exc).__name__})")
        st.record_tree()
        st.log(event="tasks", listed=sorted(listed), problems=list(problems))
        await _settle(listed, [])
        try:
            await session.disconnect()
        except Exception as exc:  # noqa: BLE001
            problems.append(f"disconnect failed ({type(exc).__name__})")
    try:
        await client.stop()
    except Exception as exc:  # noqa: BLE001
        problems.append(f"runtime stop failed ({type(exc).__name__})")
    recorded = dict(st.run.pids)
    if st.run.runtime_pid is None:
        problems.append("runtime PID unknown")
    return await _settle(recorded, problems)


async def run(cfg: Session) -> Run:
    """Open or resume the session, send the message, wait for the result boundary, then tear down."""
    st = _Step(cfg, asyncio.get_running_loop())
    client = CopilotClient(connection=RuntimeConnection.for_stdio(path=cli_path()))
    session = None
    try:
        await client.start()
        proc = getattr(client, "_cli_process", None)  # The SDK exposes no public runtime PID.
        st.run.runtime_pid = getattr(proc, "pid", None)
        st.record(st.run.runtime_pid)
        role = agent(cfg.kind)
        opts: dict[str, Any] = {
            "on_permission_request": st.permission,
            "tools": st.tools(),
            "custom_agents": [role],
            "agent": role["name"],
            "working_directory": str(cfg.worktree),
            "model": cfg.model,
            "on_event": st.on_event,
        }
        if cfg.resume:
            session = await client.resume_session(cfg.session_id, **opts)
        else:
            session = await client.create_session(session_id=cfg.session_id, **opts)
        st.log(event="session", id=cfg.session_id, resumed=cfg.resume, runtime_pid=st.run.runtime_pid)
        await session.send(cfg.message)
        st.run.delivered = True
        await st.wait(session)
    except Exception as exc:  # noqa: BLE001 - any SDK failure ends the step with retry after teardown
        st.finish("error", detail=f"{type(exc).__name__}: {exc}"[:300])
    st.run.usage = await _usage(session, cfg.model)
    st.run.termination = await _teardown(client, session, st)
    return st.run


def to_result(  # noqa: PLR0911 - one exit per ending
    run: Run, kind: StepKind, now: datetime, scanned: Sequence[tuple[int, str]] = ()
) -> StepResult:
    """Map one session's ending to the loop's step result; unverified termination or a scan survivor stops."""
    t = run.termination or Termination(confirmed=False, problems=("termination did not run",))
    if not t.confirmed or scanned:
        pids = ", ".join(str(p) for p in sorted({*t.survivors, *t.unknown, *(pid for pid, _ in scanned)}))
        reason = "; ".join(([f"processes {pids} still present"] if pids else []) + list(t.problems))
        stop = Stop(
            kind=ErrorKind.LIVENESS,
            reason=f"termination unverified: {reason}",
            action=f"End processes {pids}" if pids else "Check that no process of this step remains",
            resume="No process of this step remains",
            at=now,
        )
        return StepResult(exit=Exit.STOP, reason=stop.reason, stop=stop)
    p = run.payload
    match run.ending:
        case "result" if isinstance(p, tools.BuildResult):
            return StepResult(exit=Exit.DONE, reason=p.summary[:200])
        case "ask" if isinstance(p, tools.AskQuestion):
            options = [Option(id=f"o{i}", label=f"{o.label}: {o.effect}") for i, o in enumerate(p.options, 1)]
            return StepResult(
                exit=Exit.ASK, question=Question(step=kind, text=f"{p.question} (why: {p.why})", options=options)
            )
        case "premise" if isinstance(p, tools.WrongPremise):
            cause = cause_key(ErrorKind.SCOPE, kind, p.stage)
            return StepResult(exit=Exit.BACK, back_to=StepKind.PLAN, cause=cause, reason=p.reason[:200])
        case "deadline":
            return StepResult(exit=Exit.RETRY, cause=cause_key(ErrorKind.LIVENESS, kind, "deadline"), reason="deadline")
        case "error":
            return StepResult(exit=Exit.RETRY, cause=cause_key(ErrorKind.TOOLING, kind, "sdk"), reason=run.detail)
        case _:
            return StepResult(
                exit=Exit.RETRY, cause=cause_key(ErrorKind.RESULT, kind), reason=f"no valid result: {run.detail}"
            )
