"""What the owner's shaping chat gets from its VS Code window and returns to its caller (TD-36, TD-83).

The driver in ``vscode_step`` opens the chat; this module holds only the data it shares with its callers.
"""

from __future__ import annotations

import subprocess
import time
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from owlbear_delivery_next.runtimes.ahp import Json, Transport

type End = Literal[
    "complete",
    "error",
    "unbound",
    "settings-refused",
    "busy",
    "model-unavailable",
    "config-refused",
    "no-agent",
    "bootstrap-stuck",
    "bootstrap-model",
    "bootstrap-unexpected",
    "cancel-unconfirmed",
    "started",
    "unstarted",
]


@dataclass(frozen=True)
class StepSpec:
    """One chat's window: where, which agent, which model and effort, what to send, and the session config."""

    folder: Path
    agent: Path | None  # the agent file; the host lists only agents in ``folder``'s or ~/.copilot/agents (live)
    model: str
    effort: str
    prompt: str
    config: Json = field(default_factory=dict)  # e.g. autoApprove or sandboxEnabled; the user's choice (TD-29)
    context: str = "default"  # the context tier; "long" picks the model's largest size
    nonce: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    picker: str = "agent"  # the mode ``code chat -m`` opens; the shaping chat keeps its agent for typed messages

    @property
    def marker(self) -> str:
        """The text the bootstrap echoes; its nonce identifies the session Delivery may act on."""
        return f"OWLBEAR-{self.nonce}"

    @property
    def bootstrap(self) -> str:
        """The ``code chat`` prompt: a shell-only turn that calls no model (TD-48)."""
        return f"!echo {self.marker}"

    @property
    def agent_uris(self) -> tuple[str, ...]:
        """The agent file as a session may list it: by its own path (a symlink stays one), then by its target."""
        if not self.agent:
            return ()
        return tuple(dict.fromkeys((self.agent.absolute().as_uri(), self.agent.resolve().as_uri())))


@dataclass
class Outcome:
    """How the chat's opening ended and what it touched; the chat itself is left to the owner."""

    end: End
    detail: str = ""
    session: str | None = None
    chat: str | None = None
    turns: list[str] = field(default_factory=list)
    cancel_confirmed: bool | None = None  # set when Delivery cancelled a turn: did the host confirm it?


def launch_code_chat(args: list[str], cwd: Path) -> None:
    """Start ``code chat``; it returns once the window has the prompt."""
    subprocess.Popen(args, cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)  # noqa: S603


@dataclass(frozen=True)
class Hooks:
    """The chat's contact with the machine; tests replace them."""

    settings: Callable[[Path, str], None]  # pins the folder's settings before the window opens
    launch: Callable[[list[str], Path], None] = launch_code_chat
    clock: Callable[[], float] = time.monotonic
    reconnect: Callable[[], Transport] | None = None  # a new, signed-in connection to the same host
