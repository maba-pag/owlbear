"""One bounded worker session on the installed Copilot CLI; it ends at a result-tool call or deadline (D4 §3.2, P4)."""

from __future__ import annotations

import asyncio
import contextlib
import os
import re
import shlex
import shutil
import signal
import subprocess
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import partial
from importlib.resources import files
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

import psutil
from copilot import CopilotClient, RuntimeConnection
from copilot.rpc import PermissionDecisionApproveOnce, PermissionDecisionReject, TasksCancelRequest
from copilot.tools import Tool, ToolInvocation, ToolResult

from owlbear_delivery_next import prompts, tools
from owlbear_delivery_next.loop import StepResult, cause_key
from owlbear_delivery_next.models import ErrorKind, Exit, Option, Question, StepKind, Stop, Waiting

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Iterable, Mapping, Sequence

    from copilot.session import CopilotSession

DEADLINES = {StepKind.BUILD: 1200.0, StepKind.REVIEW: 600.0, StepKind.CHECK: 900.0}
ROLES = {StepKind.BUILD: "builder", StepKind.REVIEW: "reviewer", StepKind.CHECK: "builder"}
POLL = 5.0
SETTLE = 10.0
START = 60.0  # runtime start, session create or resume
CALL = 30.0  # one request while the step runs
STOP_CALL = 10.0  # one teardown request
GRACE = 5.0  # between terminate and kill
DENIED = ("git push", "git config", "git -c", "gh", "sudo")
DIR_OPTIONS = frozenset({"-C", "--prefix", "--cwd", "--dir", "--git-dir", "--work-tree"})
NULL_PATHS = frozenset({"/dev/null"})
VALUE_FLAGS = "mFCctSuo"  # short options of git commit and push that take a value
_REDIRECT = re.compile(r"^\d*[<>]+&?")
type Ending = Literal["result", "ask", "premise", "invalid", "no-result", "deadline", "missing", "error"]
type Pids = Mapping[int, float | None]
type Observe = Callable[[int, float | None], bool | None]


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


def _resolve(base: Path, path: str) -> Path:
    p = Path(path).expanduser()
    return (p if p.is_absolute() else base / p).resolve()


def _inside(root: Path, path: str, base: Path | None = None) -> bool:
    try:
        return _resolve(base or root, path).is_relative_to(root.resolve())
    except OSError, ValueError, RuntimeError:
        return False


def _bypass(words: Sequence[str]) -> str | None:
    """Return the flag of a git command that skips hooks or signing, or forces a push."""
    sub = next((w for w in words if w in {"commit", "push"}), "") if words[:1] == ["git"] else None
    for w in words[1:] if sub is not None else ():
        short = re.fullmatch(r"-([a-zA-Z]+)", w)  # a cluster sets a flag only before an option taking a value
        flags = re.split(f"[{VALUE_FLAGS}]", short[1])[0] if short else ""
        if w in {"--no-verify", "--no-gpg-sign"} or (sub == "commit" and "n" in flags):
            return w
        if sub == "push" and (w.startswith(("--force", "+")) or "f" in flags):
            return w
    return None


def _escape(root: Path, base: Path, words: Sequence[str], *, mutating: bool) -> str | None:
    """Return a ``cd`` target, directory option or mutating path argument that lies outside the worktree."""
    if words[:1] == ["cd"]:
        return None if _inside(root, target := (words[1:] or ["~"])[0], base) else target
    for i, word in enumerate(words[1:], 1):
        flag, eq, value = word.partition("=")
        if flag in DIR_OPTIONS:
            value = value if eq else (words[i + 1 : i + 2] or [""])[0]
        elif mutating and re.match(r"[/~]|\.\.(/|$)|.*/\.\./", value := _REDIRECT.sub("", value if eq else word)):
            value = "" if value in NULL_PATHS else value
        else:
            continue
        if value and not _inside(root, value, base):
            return value
    return None


def _shell(policy: Policy, req: Request) -> str | None:  # noqa: PLR0911 - one reason per check
    if req.urls:
        return "shell commands that reach URLs are not allowed"
    base = policy.root
    for text, read_only in req.commands or (("", False),):
        try:
            words = shlex.split(text)
        except ValueError:
            return f"`{text}` cannot be parsed"
        if flag := _bypass(words):
            return f"`{text}` uses {flag}, which skips hooks or signing or forces history"
        if (outside := _escape(policy.root, base, words, mutating=not read_only)) is not None:
            return f"`{text}` reaches {outside}, outside the worktree"
        base = _resolve(base, words[1]) if words[:1] == ["cd"] and len(words) > 1 else base
        if _matches(text, DENIED):
            return f"`{text}` is denied"
        if not (_matches(text, policy.commands) or (read_only and all(_inside(policy.root, p) for p in req.paths))):
            return f"`{text}` is not in this step's allow list"
    return None


def decide(policy: Policy, req: Request) -> str | None:
    """Return None to allow, or the denial reason the agent and the activity log see."""
    if req.kind == "custom-tool":
        return None if req.tool in {s.name for s in tools.SPECS} else f"tool {req.tool} is not allowed"
    if req.kind in {"read", "write"}:
        if req.kind == "write" and not policy.write:
            return "writes are not allowed in this step"
        outside = [p for p in req.paths if not _inside(policy.root, p)]
        return f"{req.kind} outside the worktree: {outside[0]}" if outside else None if req.paths else "no path"
    return _shell(policy, req) if req.kind == "shell" else f"{req.kind} requests are not allowed in this step"


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


def verdict(recorded: Pids, alive: Observe, problems: Sequence[str] = ()) -> Termination:
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


def _started(pid: int) -> float:
    return psutil.Process(pid).create_time()


def _pgid(pid: int) -> int:
    with contextlib.suppress(OSError):
        return os.getpgid(pid)
    return -1


def targets(recorded: Pids, seen: Observe, group: Callable[[int], int], own: int) -> tuple[list[int], list[int]]:
    """Return live PIDs whose start time proves identity, and groups they lead; an unknown start is never signalled."""
    live = sorted(p for p, c in recorded.items() if c is not None and seen(p, c))
    return live, [p for p in live if p != own and group(p) == p]


def kill(recorded: Pids, sig: signal.Signals) -> list[int]:
    """Signal recorded PIDs whose start time proves identity, and the groups they lead; return the live ones."""
    live, groups = targets(recorded, alive, _pgid, os.getpgrp())
    for g, send in [*((g, os.killpg) for g in groups), *((p, os.kill) for p in live)]:
        with contextlib.suppress(OSError):
            send(g, sig)
    return live


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
    model: str | None = None
    fresh: str = ""  # first message of a replacement session: stored context plus the pending answer
    readback: bool = False  # the answer was delivered before: read the transcript before sending it again
    previous: Pids = field(default_factory=dict)  # PIDs earlier runners recorded for this session
    journal: Journal = field(default_factory=Journal)


@dataclass
class Run:
    """What one session produced and how it ended; ``head`` is the worktree HEAD of the accepted result."""

    session_id: str
    ending: Ending = "error"
    payload: tools.Args | None = None
    detail: str = ""
    head: str | None = None
    runtime_pid: int | None = None
    pids: dict[int, float | None] = field(default_factory=dict)
    usage: dict[str, Any] = field(default_factory=dict)
    termination: Termination | None = None
    denials: list[str] = field(default_factory=list)
    invalid: int = 0


def missing_cause(kind: StepKind) -> str:
    """Cause key counted each time a resumed session is reported absent."""
    return cause_key(ErrorKind.STATE, kind, "session-missing")


def effect_seen(run: Run) -> bool:
    """An answer's effect is observed only when the step ends with an accepted result or a new question."""
    return run.ending in {"result", "ask"} and run.payload is not None


def sent(events: Iterable[Any], message: str) -> bool:
    """Whether a session transcript already holds *message* as a user message."""
    users = (getattr(e.data, "content", "") or "" for e in events if getattr(e.type, "value", e.type) == "user.message")
    return any(message.strip() in c for c in users)


class _Step:
    def __init__(self, cfg: Session, loop: asyncio.AbstractEventLoop) -> None:
        self.cfg, self.loop, self.run, self.proc = cfg, loop, Run(cfg.session_id), None
        self.done = self.turn = self.idle = False
        self.changed = asyncio.Event()

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

    def permission(self, request: Any, _invocation: Any) -> Any:  # noqa: ANN401 - SDK types
        req = _view(request)
        reason = decide(self.cfg.policy, req)
        if reason is None:
            return PermissionDecisionApproveOnce()
        self.run.denials.append(reason)
        self.log(event="denied", kind=req.kind, request=[t for t, _ in req.commands] or list(req.paths), reason=reason)
        return PermissionDecisionReject(feedback=f"Denied: {reason}")

    def _check_result(self, args: tools.Args) -> list[str]:
        try:
            tree = self.cfg.observe()
        except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
            return [f"changes: the worktree could not be read ({type(exc).__name__}); try again"]
        errors = tools.check_result(args, tree, self.cfg.checks, self.cfg.policy.root)
        self.run.head = None if errors else tree.head
        return errors

    def _handle(self, spec: tools.Spec, inv: ToolInvocation) -> ToolResult:
        args, errors = tools.parse(spec.model, inv.arguments)
        if args is not None:
            errors = tools.check_question(args) if isinstance(args, tools.AskQuestion) else []
            errors += self._check_result(args) if spec is self.cfg.submit else []
        self.log(event="tool", tool=spec.name, accepted=not errors, errors=errors)
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
                new[pid] = _started(pid)
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
        prior = verdict(self.cfg.previous, alive)
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
    models = sorted((getattr(m, "model_metrics", None) or {}).keys())
    mismatch = bool(requested and models and requested not in models)
    return {"credits": None if nano is None else nano / 1e9, "models": models, "model_mismatch": mismatch}


async def _settle(recorded: Pids, problems: list[str], limit: float | None = None) -> Termination:
    end = time.monotonic() + (SETTLE if limit is None else limit)
    # Polls the OS process table; there is no event to wait on.
    while not (result := verdict(recorded, alive, problems)).confirmed and time.monotonic() < end:  # noqa: ASYNC110
        await asyncio.sleep(0.5)
    return result


async def _force(st: _Step, why: str) -> None:
    """Runtime-stop fallback: terminate, then kill the runtime (an unreaped child), recorded PIDs and their groups."""
    st.log(event="force-stop", reason=why, runtime_pid=st.run.runtime_pid)
    with contextlib.suppress(OSError, AttributeError):
        st.proc.terminate()
    kill(st.run.pids, signal.SIGTERM)
    await _settle(st.run.pids, [], GRACE)
    with contextlib.suppress(OSError, AttributeError):
        st.proc.kill()
    kill(st.run.pids, signal.SIGKILL)


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
    elif alive(rt, st.run.pids.get(rt)) is not False:
        await _force(st, "runtime still present after stop")
    return await _settle(dict(st.run.pids), problems)


async def _open(client: CopilotClient, st: _Step) -> CopilotSession | None:
    """Resume or create the session and send the first message; the answer counts as delivered once acknowledged."""
    cfg, opts = st.cfg, st.options()
    sid, message, resumed = cfg.session_id, cfg.message, False
    if cfg.resume and await _call(client.get_session_metadata(sid), "session lookup") is not None:
        session = await _call(client.resume_session(sid, **opts), "session resume", START)
        resumed = True
        if cfg.readback and sent(await _call(session.get_events(), "transcript read"), message):
            message = prompts.CONTINUE
    else:
        if cfg.resume:
            if (new := st.replace()) is None:
                return None
            sid, message = new, cfg.fresh
            st.run.session_id = sid
        session = await _call(client.create_session(session_id=sid, **opts), "session create", START)
    st.log(event="session", id=sid, resumed=resumed, resent=message != prompts.CONTINUE, runtime=st.run.runtime_pid)
    await _call(session.send(message), "send")
    cfg.journal.delivered()
    return session


async def run(cfg: Session) -> Run:
    """Open or resume the session, send the message, wait for the result boundary, then tear down within bounds."""
    st = _Step(cfg, asyncio.get_running_loop())
    client = CopilotClient(connection=RuntimeConnection.for_stdio(path=cli_path()))
    session = None
    try:
        async with asyncio.timeout(DEADLINES.get(cfg.kind, 1200.0) + START + CALL):
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
    st.run.termination = await _teardown(client, session, st)
    return st.run


def to_result(run: Run, kind: StepKind, now: datetime) -> StepResult:
    """Map one session's ending to the loop's step result, carrying the last permission denial."""
    result = _exit(run, kind, now)
    return result.model_copy(update={"denial": run.denials[-1][:300]}) if run.denials else result


def _exit(run: Run, kind: StepKind, now: datetime) -> StepResult:  # noqa: PLR0911
    """One exit per ending; unverified termination stops whatever the session reported; the host scans after."""
    t = run.termination or Termination(confirmed=False, problems=("termination did not run",))
    if not t.confirmed:
        pids = ", ".join(str(p) for p in sorted({*t.survivors, *t.unknown}))
        found = [f"processes {pids} still present"] if pids else []
        stop = Stop(
            kind=ErrorKind.LIVENESS,
            reason="termination unverified: " + "; ".join([*found, *t.problems]),
            action=f"End processes {pids}" if pids else "Check that no process of this step remains",
            resume="No process of this step remains",
            at=now,
        )
        return StepResult(exit=Exit.STOP, reason=stop.reason, stop=stop)
    p = run.payload
    match run.ending:
        case "result" if isinstance(p, tools.BuildResult):
            return StepResult(exit=Exit.DONE, reason=p.summary[:200])
        case "result" if isinstance(p, tools.ReviewResult):
            found = "; ".join(f"{f.place}: {f.problem} - fix: {f.fix}" for f in p.findings)[:1500]
            return StepResult(exit=Exit.DONE if p.verdict == "pass" else Exit.RETRY, reason=found or "review passed")
        case "result" if isinstance(p, tools.CheckRecipe):
            reason = f"starting `{p.command}` for the check"
            return StepResult(exit=Exit.PENDING, waiting=Waiting.PERSON_CHECK, reason=reason)
        case "ask" if isinstance(p, tools.AskQuestion):
            options = [Option(id=f"o{i}", label=f"{o.label}: {o.effect}") for i, o in enumerate(p.options, 1)]
            question = Question(step=kind, text=f"{p.question} (why: {p.why})", options=options)
            return StepResult(exit=Exit.ASK, question=question)
        case "premise" if isinstance(p, tools.WrongPremise):
            cause = cause_key(ErrorKind.SCOPE, kind, p.stage)
            back = StepKind.BUILD if kind == StepKind.CHECK else StepKind.PLAN
            return StepResult(exit=Exit.BACK, back_to=back, cause=cause, reason=p.reason[:200])
        case "deadline":
            cause = cause_key(ErrorKind.LIVENESS, kind, "deadline")
            return StepResult(exit=Exit.RETRY, cause=cause, reason=run.detail or "deadline")
        case "missing":
            return StepResult(exit=Exit.RETRY, cause=missing_cause(kind), reason=run.detail)
        case "error":
            return StepResult(exit=Exit.RETRY, cause=cause_key(ErrorKind.TOOLING, kind, "sdk"), reason=run.detail)
        case _:
            reason = f"no valid result: {run.detail}"
            return StepResult(exit=Exit.RETRY, cause=cause_key(ErrorKind.RESULT, kind), reason=reason)
