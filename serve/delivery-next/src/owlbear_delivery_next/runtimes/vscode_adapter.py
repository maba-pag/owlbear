"""Open the owner's shaping chat in a VS Code window, over the editor's agent host (TD-35, TD-83).

New Change's shaping chat runs as the user-level shaper agent, with auto-approve. Without that agent it does not open,
since an agentless chat would have every tool (TD-93, TD-102). Delivery steps never run in a window
(D-01M5WG8RGCBKADW6XPGP0E2FAP).
"""

from __future__ import annotations

import contextlib
import os
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from owlbear_delivery_next.runtimes import ahp, readiness
from owlbear_delivery_next.runtimes import window_files as wf
from owlbear_delivery_next.runtimes.vscode_contract import Hooks, Outcome, StepSpec, launch_code_chat
from owlbear_delivery_next.runtimes.vscode_step import Step

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_delivery_next.settings.config import Effective

SHAPING = {"autoApprove": "autoApprove", "sandboxEnabled": "off", "mode": "interactive"}  # D2, D4, D5; it waits (TD-83)
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
    """Sign in again on the chat's own host (TD-48): a new window lists no models until then (P14)."""
    if not isinstance(conn, ahp.Connection):
        raise ahp.HostError("only a host connection can be reopened")  # noqa: EM101, TRY003
    return conn.reopen(_token())


@dataclass(frozen=True)
class Env:
    """The shaping chat's contact with the editor and the machine; tests replace it."""

    connect: Callable[[Path], ahp.Transport] = connect
    reconnect: Callable[[ahp.Transport], ahp.Transport] = reopen
    launch: Callable[[list[str], Path], None] = launch_code_chat
    clock: Callable[[], float] = time.monotonic
    shaper: Path | None = field(default_factory=lambda: readiness.shaper_path(Path.home()))  # the chat's agent (TD-93)


def open_chat(folder: Path, role: Effective, prompt: str, env: Env | None = None) -> tuple[Outcome, str]:
    """Open an interactive Copilot chat in ``folder``'s window with ``prompt`` as its first model turn (TD-83).

    The chat runs on the role's model, effort and context tier with auto-approve, as the user-level shaper agent;
    without that agent it does not open, since an agentless chat would have every tool (TD-93, TD-102).
    Returns how it went and what Delivery could not take out of the owner's settings again, or ''.
    """
    env, added, conn = env or Env(), list[wf.Added](), None
    agent = env.shaper
    if agent is not None and not agent.is_file():
        return Outcome("no-agent", f"the shaper agent is not installed at {agent}; run `owlbear install`"), ""
    spec = StepSpec(
        folder=folder, agent=agent, model=role.model, effort=role.effort, prompt=prompt, config=SHAPING,
        context=role.context, picker=agent.name.removesuffix(".agent.md") if agent else "agent",
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
        out = Step(conn, spec, hooks).open()
    except (OSError, wf.SettingsError, ahp.HostError, subprocess.SubprocessError) as exc:
        out = Outcome("error", f"{type(exc).__name__}: {exc}"[:300])
    finally:
        if close := getattr(conn, "close", None):
            close()
        warning = wf.remove_harness(folder, added[0]) if added else ""
    return out, warning
