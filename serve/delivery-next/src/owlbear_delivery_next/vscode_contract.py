"""What a VS Code step is given and what it returns (TD-36, TD-48): the spec, the levers, the outcome and the hooks.

The driver in ``vscode_step`` runs the step; this module holds only the data it shares with its callers.
"""

from __future__ import annotations

import queue
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from owlbear_delivery_next.window_files import write_window_settings

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from owlbear_delivery_next.ahp import Json, Transport

type End = Literal[
    "complete",
    "cancelled",
    "error",
    "timeout",
    "stopped",
    "closed",
    "unbound",
    "wrong-model",
    "config-refused",
    "settings-refused",
    "cancel-unconfirmed",
    "bootstrap-stuck",
    "bootstrap-model",
    "bootstrap-unexpected",
    "model-unavailable",
    "no-agent",
    "folder-busy",
    "busy",
    "user-turn",
    "steering-unrun",
    "started",
    "unstarted",
]


@dataclass(frozen=True)
class StepSpec:
    """One VS Code step: where, which agent, which model and effort, what to do, and the session config."""

    folder: Path
    agent: Path | None  # the agent file; the host lists only agents in ``folder``'s or ~/.copilot/agents (live)
    model: str
    effort: str
    prompt: str
    config: Json = field(default_factory=dict)  # e.g. autoApprove or sandboxEnabled; the user's choice (TD-29)
    context: str = "default"  # the context tier; "long" picks the model's largest size
    nonce: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    reminder: str = ""  # sent once as a new turn when the real turn completes before Delivery stops it
    attachments: tuple[Json, ...] = ()  # sent with the prompt's turn only, e.g. screenshots (C7)

    @property
    def marker(self) -> str:
        """The text the bootstrap echoes; its nonce identifies the session Delivery may act on."""
        return f"OWLBEAR-{self.nonce}"

    @property
    def bootstrap(self) -> str:
        """The ``code chat`` prompt: a shell-only turn that calls no model (TD-48)."""
        return f"!echo {self.marker}"

    @property
    def agent_uri(self) -> str:
        """The agent file as the host names it in a session's customizations."""
        return self.agent.resolve().as_uri() if self.agent else ""


@dataclass(frozen=True)
class ToolCall:
    """One tool call that waits for Delivery's confirmation."""

    name: str
    input: str
    client: str | None


@dataclass
class Control:
    """The watcher's levers while a step runs: stop it, or steer it."""

    stop: threading.Event = field(default_factory=threading.Event)
    steering: queue.Queue[str] = field(default_factory=queue.Queue)
    started: threading.Event = field(default_factory=threading.Event)  # set once Delivery's first turn started
    settled: threading.Event = field(default_factory=threading.Event)  # set once Delivery holds the step's result


@dataclass
class Outcome:
    """How the step ended and what it touched; the result itself arrives through the Delivery MCP server."""

    end: End
    detail: str = ""
    session: str | None = None
    chat: str | None = None
    turns: list[str] = field(default_factory=list)
    tools: dict[str, str] = field(default_factory=dict)  # tool call id -> tool name, in call order
    denied: list[str] = field(default_factory=list)
    usage: Json | None = None
    tokens: dict[str, int] = field(default_factory=dict)  # billed model -> input plus output tokens of Delivery's turns
    cancel_confirmed: bool | None = None  # set when Delivery cancelled a turn: did the host confirm it?


def launch_code_chat(args: list[str], cwd: Path) -> None:
    """Start ``code chat``; it returns once the window has the prompt."""
    subprocess.Popen(args, cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)  # noqa: S603


@dataclass(frozen=True)
class Hooks:
    """The step's contact with the machine; tests replace them."""

    launch: Callable[[list[str], Path], None] = launch_code_chat
    clock: Callable[[], float] = time.monotonic
    settings: Callable[[Path, str], None] = write_window_settings
    reconnect: Callable[[], Transport] | None = None  # a new, signed-in connection to the same host
