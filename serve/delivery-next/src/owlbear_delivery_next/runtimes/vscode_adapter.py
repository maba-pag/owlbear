"""Open the owner's shaping chat in a VS Code window, over the editor's agent host (TD-35, TD-83).

New Change's shaping chat runs as the user-level shaper agent, with auto-approve. Without that agent it does not open,
since an agentless chat would have every tool (TD-93, TD-102). Delivery steps never run in a window
(D-01M5WG8RGCBKADW6XPGP0E2FAP).
"""

from __future__ import annotations

import logging
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
_log = logging.getLogger(__name__)


def connect(folder: Path) -> ahp.Connection:
    """Connect to the editor's agent host; start VS Code on ``folder`` when no host answers (TD-35).

    A host that answers with a refusal ends the attempt at once: starting VS Code again cannot change its answer.
    VS Code's windows sign that host in; OwlBear never does.
    """
    entry = ahp.endpoint()
    client = f"owlbear-delivery-{uuid.uuid4().hex[:8]}"
    stale = "no agent host was published"
    if entry is not None:
        try:
            return ahp.connect(entry, client)
        except ahp.HostRefusedError:
            raise
        except (OSError, ahp.HostError) as exc:  # a stale endpoint: the editor that published it is gone
            stale = f"the published agent host failed: {type(exc).__name__}: {exc}"
            _log.warning("%s; starting VS Code on %s", stale, folder)
    launch_code_chat(["code", str(folder)], folder)
    end = time.monotonic() + START
    while time.monotonic() < end:
        time.sleep(1)
        fresh = ahp.endpoint()
        if fresh is not None and fresh != entry:
            return ahp.connect(fresh, client)
    why = f"VS Code published no agent host within {START:.0f} s; before that, {stale}"
    raise ahp.HostError(why)


@dataclass(frozen=True)
class Env:
    """The shaping chat's contact with the editor and the machine; tests replace it."""

    connect: Callable[[Path], ahp.Transport] = connect
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
        hooks = Hooks(launch=env.launch, clock=env.clock, settings=harness)
        out = Step(conn, spec, hooks).open()
    except (OSError, wf.SettingsError, ahp.HostError, subprocess.SubprocessError) as exc:
        out = Outcome("error", f"{type(exc).__name__}: {exc}")
        _log.exception("the shaping chat in %s did not open", folder)
    finally:
        if close := getattr(conn, "close", None):
            close()
        warning = wf.remove_harness(folder, added[0]) if added else ""
    if out.end not in {"started", "error"}:
        _log.warning("the shaping chat in %s ended %s: %s", folder, out.end, out.detail)
    return out, warning
