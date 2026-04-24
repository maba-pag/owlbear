"""Mock ACP agent for E2E testing.

Acts as a test double for Copilot CLI. Receives a task ID via ACP prompt,
calls kanban-md to annotate and advance the task, and returns PromptResponse.

Entry point: ``run_agent(KanbanMockAgent())`` — spawnable via spawn_agent_process().

Environment variables:
    KANBAN_DIR: Path to the kanban board directory (required).
    KANBAN_BIN: Path to the kanban-md binary (default: kanban/kanban-md).
"""

from __future__ import annotations

import os
import re
import subprocess
import uuid
from typing import Any

from acp import run_agent
from acp.schema import InitializeResponse, NewSessionResponse, PromptResponse

_DEFAULT_KANBAN_BIN = "kanban/kanban-md"
_TASK_ID_RE = re.compile(r"#(\d+)")


class KanbanMockAgent:
    """ACP agent that processes kanban tasks via kanban-md subprocess."""

    def on_connect(self, conn: Any) -> None:  # noqa: ANN401
        """Save the client connection reference."""
        self._conn = conn

    async def initialize(
        self,
        protocol_version: int,
        **_kwargs: Any,  # noqa: ANN401
    ) -> InitializeResponse:
        """Return InitializeResponse with the ACP protocol version."""
        return InitializeResponse(protocol_version=protocol_version)

    async def new_session(
        self,
        cwd: str,  # noqa: ARG002
        **_kwargs: Any,  # noqa: ANN401
    ) -> NewSessionResponse:
        """Return NewSessionResponse with a generated session ID."""
        return NewSessionResponse(session_id=str(uuid.uuid4()))

    async def prompt(
        self,
        prompt: list[Any],
        session_id: str,  # noqa: ARG002
        **_kwargs: Any,  # noqa: ANN401
    ) -> PromptResponse:
        """Parse task ID, run kanban-md show/edit/move, return PromptResponse."""
        kanban_bin = os.environ.get("KANBAN_BIN", _DEFAULT_KANBAN_BIN)
        kanban_dir = os.environ["KANBAN_DIR"]
        text = prompt[0].text
        match = _TASK_ID_RE.search(text)
        if not match:
            msg = f"No task ID found in prompt text: {text!r}"
            raise ValueError(msg)
        task_id = match.group(1)

        subprocess.run(  # noqa: ASYNC221
            [kanban_bin, "--dir", kanban_dir, "show", task_id],
            check=False,
        )
        subprocess.run(  # noqa: ASYNC221
            [
                kanban_bin,
                "--dir",
                kanban_dir,
                "edit",
                task_id,
                "-a",
                "Mock agent processed",
            ],
            check=False,
        )
        subprocess.run(  # noqa: ASYNC221
            [kanban_bin, "--dir", kanban_dir, "move", task_id, "--next"],
            check=False,
        )
        return PromptResponse(stop_reason="end_turn")

    async def cancel(self, session_id: str, **_kwargs: Any) -> None:  # noqa: ANN401, ARG002
        """No-op stub."""

    async def load_session(self, cwd: str, session_id: str, **_kwargs: Any) -> None:  # noqa: ANN401, ARG002
        """No-op stub."""

    async def close_session(self, session_id: str, **_kwargs: Any) -> None:  # noqa: ANN401, ARG002
        """No-op stub."""

    async def list_sessions(self, **_kwargs: Any) -> None:  # noqa: ANN401
        """No-op stub."""

    async def fork_session(self, **_kwargs: Any) -> None:  # noqa: ANN401
        """No-op stub."""

    async def resume_session(self, **_kwargs: Any) -> None:  # noqa: ANN401
        """No-op stub."""

    async def set_session_mode(self, **_kwargs: Any) -> None:  # noqa: ANN401
        """No-op stub."""

    async def set_session_model(self, **_kwargs: Any) -> None:  # noqa: ANN401
        """No-op stub."""

    async def set_config_option(self, **_kwargs: Any) -> None:  # noqa: ANN401
        """No-op stub."""

    async def authenticate(self, **_kwargs: Any) -> None:  # noqa: ANN401
        """No-op stub."""

    async def ext_method(self, **_kwargs: Any) -> None:  # noqa: ANN401
        """No-op stub."""

    async def ext_notification(self, **_kwargs: Any) -> None:  # noqa: ANN401
        """No-op stub."""


if __name__ == "__main__":
    import asyncio

    asyncio.run(run_agent(KanbanMockAgent()))
