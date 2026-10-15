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
from pathlib import Path
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next import ahp, leftovers, prompts, setup
from owlbear_delivery_next import window_files as wf
from owlbear_delivery_next.processes import Termination
from owlbear_delivery_next.results import Gate
from owlbear_delivery_next.sdk_adapter import DEADLINES, role_of
from owlbear_delivery_next.session_result import PROVEN, Run
from owlbear_delivery_next.step_inbox import Inbox
from owlbear_delivery_next.vscode_contract import Control, Hooks, Outcome, StepSpec, ToolCall, launch_code_chat
from owlbear_delivery_next.vscode_step import Step

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_delivery_next.ahp import Json
    from owlbear_delivery_next.config import Effective
    from owlbear_delivery_next.sdk_adapter import Session

CONFIG = {"autoApprove": "autoApprove", "sandboxEnabled": "off", "mode": "autopilot"}  # the owner's D2, D4, D5
SHAPING = CONFIG | {"mode": "interactive"}  # the owner's chat: allow-all, but it waits for the owner (TD-83)
GRACE = 30.0  # seconds an agent has to end its turn after its result was accepted
START = 60.0  # seconds a started editor has to publish its agent host


def _token() -> str:
    user = os.environ.get("OWLBEAR_GH_USER")
    argv = ["gh", "auth", "token", *(["--user", user] if user else [])]
    return subprocess.run(argv, capture_output=True, text=True, timeout=15, check=True).stdout.strip()  # noqa: S603


def connect(folder: Path) -> ahp.Connection:
    """Connect to the editor's agent host; start VS Code on ``folder`` when no host answers (TD-35)."""
    entry = ahp.endpoint()
    client = f"owlbear-delivery-{uuid.uuid4().hex[:8]}"
    if entry is not None:
        with contextlib.suppress(OSError, ahp.HostError):
            return ahp.connect(entry, client, _token())
    launch_code_chat(["code", str(folder)], folder)
    end = time.monotonic() + START
    while time.monotonic() < end:
        time.sleep(1)
        fresh = ahp.endpoint()
        if fresh is not None and fresh != entry:
            return ahp.connect(fresh, client, _token())
    raise ahp.HostError(f"VS Code published no agent host within {START:.0f} s")  # noqa: EM102, TRY003


def reopen(conn: ahp.Transport) -> ahp.Transport:
    """Sign in again on the step's own host (TD-48): a new window lists no models until then (P14)."""
    if not isinstance(conn, ahp.Connection):
        raise ahp.HostError("only a host connection can be reopened")  # noqa: EM101, TRY003
    return conn.reopen(_token())


def embedded(attachments: tuple[dict[str, str], ...]) -> tuple[Json, ...]:
    """The session's image blobs as the agent host's embedded images, which reach the model (P14, C7)."""
    return tuple(
        {
            "type": "embeddedResource",
            "label": blob.get("displayName") or f"image-{number}.png",
            "displayKind": "image",
            "data": blob["data"],
            "contentType": blob["mimeType"],
        }
        for number, blob in enumerate(attachments, 1)
    )


@dataclass(frozen=True)
class Env:
    """The step's contact with the editor and the machine; tests replace it."""

    connect: Callable[[Path], ahp.Transport] = connect
    reconnect: Callable[[ahp.Transport], ahp.Transport] = reopen
    launch: Callable[[list[str], Path], None] = launch_code_chat
    clock: Callable[[], float] = time.monotonic
    settle: Callable[[Path, datetime], Termination] = leftovers.settle
    reminder: str | None = None  # None: the session role's own reminder
    shaper: Path | None = field(default_factory=lambda: setup.shaper_path(Path.home()))  # the chat's agent (TD-93)


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
        self.role = role_of(cfg)
        self.control = Control()
        self.placed: list[wf.Placed] = []
        self.gate = Gate(cfg, run, self.log, _grace(self.control))

    def log(self, **event: Any) -> None:  # noqa: ANN401 - JSON values
        self.cfg.journal.event({"at": datetime.now(UTC).isoformat(timespec="seconds"), **event})

    def pin(self, folder: Path, model: str) -> None:
        try:
            self.placed.append(wf.place(folder, wf.SETTINGS, wf.settings(model)))
        except OSError as exc:
            raise wf.SettingsError(str(exc)) from exc

    def deny(self, call: ToolCall) -> bool:
        """The harness asked Delivery to confirm a call: refuse it, since nothing a step needs asks (D2)."""
        self.run.denials.append(text := f"{call.name} asked for confirmation; Delivery refuses")
        self.run.denied[call.name.lower()] = text
        self.log(event="denied", tool=call.name, request=call.input[:200])
        return False

    def drive(self, conn: ahp.Transport) -> Outcome:
        cfg = self.cfg
        hooks = Hooks(
            launch=self.env.launch,
            clock=self.env.clock,
            settings=self.pin,
            reconnect=lambda: self.env.reconnect(conn),
        )
        spec = StepSpec(
            folder=cfg.worktree,
            agent=cfg.worktree / wf.agent_path(self.role),
            model=cfg.model or "",
            effort=cfg.effort or "",
            prompt=cfg.fresh if cfg.resume and cfg.fresh else cfg.message,
            config=CONFIG,
            context=cfg.context,
            reminder=prompts.reminder(self.role) if self.env.reminder is None else self.env.reminder,
            attachments=embedded(cfg.attachments),
        )
        out = Step(conn, spec, self.deny, hooks=hooks).run(self.control, limit=DEADLINES.get(cfg.kind, 1200.0))
        self.log(event="vscode-step", end=out.end, detail=out.detail, session=out.session)
        return out

    def step(self, inbox: Path) -> Outcome:
        """Run the attempts and close the gate before the inbox stops, so nothing is accepted afterwards."""
        cfg, conn = self.cfg, None
        try:
            for rel, render in wf.skills(self.role, ui=cfg.ui):
                self.placed.append(wf.place(cfg.worktree, rel, render))
            self.placed.append(wf.place(cfg.worktree, wf.MCP, wf.mcp(inbox, cfg.memory)))
            self.placed.append(
                wf.place(cfg.worktree, wf.agent_path(self.role), wf.agent(self.role, inbox, cfg.memory, ui=cfg.ui))
            )
            with Inbox(self.gate, inbox):
                conn = self.env.connect(cfg.worktree)
                out = self.drive(conn)
                _ending(out, self.gate)
                return out
        except (OSError, KeyError, TypeError, wf.SettingsError, ahp.HostError, subprocess.SubprocessError) as exc:
            end = "closed" if self.control.started.is_set() else "error"
            out = Outcome(end, f"{type(exc).__name__}: {exc}"[:300])
            _ending(out, self.gate)
            return out
        finally:
            if close := getattr(conn, "close", None):
                close()
            for problem in wf.restore(cfg.worktree, self.placed):
                self.log(event="window-file", problem=problem)


def _ending(out: Outcome, gate: Gate) -> None:
    """Close the gate with the runtime's ending; a model mismatch voids any result, else an accepted call stands."""
    if out.end == "wrong-model":
        gate.wrong_model(out.detail)
    elif out.end == "complete":
        gate.finish("no-result", None, "the turn ended without a result")
    elif out.end == "timeout":
        gate.finish("deadline", None, "step deadline")
    else:
        gate.finish("error", None, f"VS Code step {out.end}: {out.detail}"[:300])


def _usage(out: Outcome, model: str | None) -> dict[str, Any]:
    """The window's usage reports: tokens per billed model; it reports no credits, so they stay unknown (TD-94)."""
    models = {name: {"credits": None, "tokens": tokens} for name, tokens in out.tokens.items()}
    return {"credits": None, "models": models, "model_mismatch": bool(model and models and set(models) != {model})}


def _proven(result: Run, out: Outcome, model: str | None) -> None:
    """Only a usage report naming the step's model proves it; a processed ending without one is unknown (TD-94)."""
    if result.model_check == "mismatch":
        return
    proven = bool(model and out.tokens.get(model))
    if result.ending in PROVEN and not proven:
        result.usage_unread = f"no usage report of the window named the step's model {model}"
    result.model_check = "verified" if proven else "unknown"


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
    env, result, since = env or Env(), Run(cfg.session_id, runtime="window"), datetime.now(UTC)
    driver = _Driver(cfg, env, result)
    out = driver.step(inbox)
    started = driver.control.started.is_set()
    if started:
        cfg.journal.delivered()
    result.usage = _usage(out, cfg.model)
    _proven(result, out, cfg.model)
    result.termination = _termination(out, env.settle(cfg.worktree, since), started=started)
    return result


def open_chat(folder: Path, role: Effective, prompt: str, env: Env | None = None) -> tuple[Outcome, str]:
    """Open an interactive Copilot chat in ``folder``'s window with ``prompt`` as its first model turn (TD-83).

    The chat runs on the role's model, effort and context tier with auto-approve, as the user-level shaper agent;
    without that agent it does not open, since an agentless chat would have every tool (TD-93, TD-102).
    Returns how it went and what Delivery could not take out of the owner's settings again, or ''.
    """
    env, added, conn = env or Env(), list[wf.Added](), None
    agent = env.shaper
    if agent is not None and not agent.is_file():
        return Outcome("no-agent", f"the shaper agent is not installed at {agent}; run `owlbear-next setup`"), ""
    spec = StepSpec(
        folder=folder, agent=agent, model=role.model, effort=role.effort, prompt=prompt, config=SHAPING,
        context=role.context,
    )  # fmt: skip

    def harness(where: Path, _model: str) -> None:
        try:
            if (line := wf.add_harness(where)) is not None:
                added.append(line)
        except OSError as exc:
            raise wf.SettingsError(str(exc)) from exc

    try:
        conn = env.connect(folder)
        hooks = Hooks(launch=env.launch, clock=env.clock, settings=harness, reconnect=lambda: env.reconnect(conn))
        out = Step(conn, spec, lambda _call: False, hooks=hooks).open(Control())
    except (OSError, wf.SettingsError, ahp.HostError, subprocess.SubprocessError) as exc:
        out = Outcome("error", f"{type(exc).__name__}: {exc}"[:300])
    finally:
        if close := getattr(conn, "close", None):
            close()
        warning = wf.remove_harness(folder, added[0]) if added else ""
    return out, warning
