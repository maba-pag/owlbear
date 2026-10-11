"""Run one agent session as a C+ VS Code step (TD-35 "all in VS Code"), with the same contract as the SDK path.

The window runs with the owner's session settings (D2, D4, D5): every tool call is approved by the harness, so
Delivery's per-call policy does not apply; the agent's instructions carry the rules (D6). Results pass the same
gate as SDK results. A turn billed to another model discards any result (TD-32).
"""

from __future__ import annotations

import contextlib
import os
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next import ahp, leftovers, prompts
from owlbear_delivery_next import window_files as wf
from owlbear_delivery_next.processes import Termination
from owlbear_delivery_next.results import Gate
from owlbear_delivery_next.sdk_adapter import DEADLINES, ROLES
from owlbear_delivery_next.session_result import Run
from owlbear_delivery_next.step_inbox import Inbox
from owlbear_delivery_next.vscode_step import Control, Hooks, Outcome, Step, StepSpec, ToolCall, launch_code_chat

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from owlbear_delivery_next.sdk_adapter import Session

CONFIG = {"autoApprove": "autoApprove", "sandboxEnabled": "off", "mode": "autopilot"}  # the owner's D2, D4, D5
GRACE = 30.0  # seconds an agent has to end its turn after its result was accepted
START = 60.0  # seconds a started editor has to publish its agent host
ATTEMPTS = 8  # a freshly opened window's first chats have no agent until it has loaded the agent files (P11)
WARM = 10.0  # seconds between attempts while the window loads


def _token() -> str:
    user = os.environ.get("OWLBEAR_GH_USER")
    argv = ["gh", "auth", "token", *(["--user", user] if user else [])]
    return subprocess.run(argv, capture_output=True, text=True, timeout=15, check=True).stdout.strip()  # noqa: S603


def connect(folder: Path) -> ahp.Connection:
    """Open or focus ``folder``'s window, then connect to the editor's agent host (TD-35).

    ``code chat`` reaches the focused window, and only a window on ``folder`` knows the step's agent
    (live run), so the folder's window is opened even when a host already answers.
    """
    entry = ahp.endpoint()
    client = f"owlbear-delivery-{uuid.uuid4().hex[:8]}"
    launch_code_chat(["code", str(folder)], folder)
    if entry is not None:
        with contextlib.suppress(OSError, ahp.HostError):
            return ahp.connect(entry, client, _token())
    end = time.monotonic() + START
    while time.monotonic() < end:
        time.sleep(1)
        fresh = ahp.endpoint()
        if fresh is not None and fresh != entry:
            return ahp.connect(fresh, client, _token())
    raise ahp.HostError(f"VS Code published no agent host within {START:.0f} s")  # noqa: EM102, TRY003


@dataclass(frozen=True)
class Env:
    """The step's contact with the editor and the machine; tests replace it."""

    connect: Callable[[Path], ahp.Transport] = connect
    launch: Callable[[list[str], Path], None] = launch_code_chat
    clock: Callable[[], float] = time.monotonic
    settle: Callable[[Path, datetime], Termination] = leftovers.settle
    reminder: str = field(default=prompts.REMINDER)
    wait: Callable[[float], None] = time.sleep


def _grace(control: Control) -> Callable[[], None]:
    """Once the step has its result, give the agent ``GRACE`` seconds to end its turn, then stop it."""

    def ended() -> None:
        if not control.settled.is_set():
            control.settled.set()
            timer = threading.Timer(GRACE, control.stop.set)
            timer.daemon = True
            timer.start()

    return ended


class _Driver:
    def __init__(self, cfg: Session, env: Env, run: Run) -> None:
        self.cfg, self.env, self.run = cfg, env, run
        self.role = ROLES[cfg.kind]
        self.control = Control()
        self.placed: list[wf.Placed] = []
        self.gate = Gate(cfg, run, self.log, _grace(self.control))

    def log(self, **event: Any) -> None:  # noqa: ANN401 - JSON values
        self.cfg.journal.event({"at": datetime.now(UTC).isoformat(timespec="seconds"), **event})

    def pin(self, folder: Path, model: str) -> None:
        if any(p.rel == wf.SETTINGS for p in self.placed):
            return  # pinned by an earlier attempt of this step
        try:
            self.placed.append(wf.place(folder, wf.SETTINGS, wf.settings(model)))
        except OSError as exc:
            raise wf.SettingsError(str(exc)) from exc

    def deny(self, call: ToolCall) -> bool:
        """The harness asked Delivery to confirm a call: refuse it, since nothing a step needs asks (D2)."""
        self.run.denials.append(f"{call.name} asked for confirmation; Delivery refuses")
        self.log(event="denied", tool=call.name, request=call.input[:200])
        return False

    def drive(self, conn: ahp.Transport) -> Outcome:
        cfg, out = self.cfg, Outcome("error")
        hooks = Hooks(launch=self.env.launch, clock=self.env.clock, settings=self.pin)
        prompt = cfg.fresh if cfg.resume and cfg.fresh else cfg.message
        for attempt in range(1, ATTEMPTS + 1):
            spec = StepSpec(
                folder=cfg.worktree,
                agent=wf.agent_name(self.role),
                model=cfg.model or "",
                effort=cfg.effort or "",
                prompt=prompt,
                config=CONFIG,
                reminder=self.env.reminder,
            )
            out = Step(conn, spec, self.deny, hooks=hooks).run(self.control, limit=DEADLINES.get(cfg.kind, 1200.0))
            self.log(event="vscode-step", attempt=attempt, end=out.end, detail=out.detail, session=out.session)
            if out.end != "no-agent" or out.cancel_confirmed is False or attempt == ATTEMPTS:
                break
            self.env.wait(WARM)
        return out

    def step(self, inbox: Path) -> Outcome:
        """Run the attempts and close the gate before the inbox stops, so nothing is accepted afterwards."""
        cfg, conn = self.cfg, None
        try:
            self.placed.append(wf.place(cfg.worktree, wf.MCP, wf.mcp(inbox)))
            self.placed.append(wf.place(cfg.worktree, wf.agent_path(self.role), wf.agent(self.role)))
            with Inbox(self.gate, inbox):
                conn = self.env.connect(cfg.worktree)
                out = self.drive(conn)
                _ending(out, self.run, self.gate)
                return out
        except (OSError, KeyError, TypeError, wf.SettingsError, ahp.HostError, subprocess.SubprocessError) as exc:
            end = "closed" if self.control.started.is_set() else "error"
            out = Outcome(end, f"{type(exc).__name__}: {exc}"[:300])
            _ending(out, self.run, self.gate)
            return out
        finally:
            if close := getattr(conn, "close", None):
                close()
            for problem in wf.restore(cfg.worktree, self.placed):
                self.log(event="window-file", problem=problem)


def _ending(out: Outcome, run: Run, gate: Gate) -> None:
    """Close the gate with the runtime's ending; a model mismatch voids any result, else an accepted call stands."""
    if out.end == "wrong-model":
        detail = f"wrong model: {out.detail}"[:300]
        gate.finish("error", None, detail)
        run.ending, run.payload, run.head, run.detail = "error", None, None, detail
    elif out.end == "complete":
        gate.finish("no-result", None, "the turn ended without a result")
    elif out.end == "timeout":
        gate.finish("deadline", None, "step deadline")
    else:
        gate.finish("error", None, f"VS Code step {out.end}: {out.detail}"[:300])


def _usage(out: Outcome, model: str | None) -> dict[str, Any]:
    models = {name: {"credits": 0.0, "tokens": tokens} for name, tokens in out.tokens.items()}
    return {"credits": None, "models": models, "model_mismatch": bool(model and models and set(models) != {model})}


def _termination(out: Outcome, scanned: Termination, *, started: bool) -> Termination:
    problems = list(scanned.problems)
    if out.cancel_confirmed is False:
        problems.append("the host did not confirm Delivery's cancel")
    if out.end == "closed" and started:
        problems.append("the connection ended before the turn's end was seen")
    confirmed = scanned.confirmed and not problems
    return Termination(confirmed, scanned.survivors, scanned.unknown, tuple(problems))


def run(cfg: Session, inbox: Path, env: Env | None = None) -> Run:
    """Run the session in a VS Code window; ``inbox`` is this step's own path outside the worktree."""
    env, result, since = env or Env(), Run(cfg.session_id), datetime.now(UTC)
    if cfg.attachments:
        result.ending, result.detail = "error", "attachments are sent only through the SDK"
        result.termination = Termination(confirmed=True)
        return result
    driver = _Driver(cfg, env, result)
    out = driver.step(inbox)
    started = driver.control.started.is_set()
    if started:
        cfg.journal.delivered()
    result.usage = _usage(out, cfg.model)
    result.termination = _termination(out, env.settle(cfg.worktree, since), started=started)
    return result
