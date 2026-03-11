"""SESSION_START hook that injects project context into the event payload.

Reads the project instructions file and runs a kanban board summary command,
then stores both as structured data on the event ``data`` dict.  Missing
files or failing commands are logged and silently degraded to empty strings.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from owlbear.core.hooks import SessionStartData  # noqa: TC001

if TYPE_CHECKING:
    from owlbear.core.hooks import HookRegistry

logger = logging.getLogger(__name__)

_DEFAULT_INSTRUCTIONS = Path(".github/copilot-instructions.md")
_DEFAULT_KANBAN_CMD = ["kanban/kanban-md.exe", "context"]


class ContextInjectionHook:
    """``SESSION_START`` hook that enriches the payload with project context.

    On invocation the hook:

    1. Reads the project instructions file from *instructions_path*.
    2. Runs the kanban summary command (*kanban_cmd*) via :func:`asyncio.create_subprocess_exec`.
    3. Stores both results under ``data["context"]`` as a dict with keys
       ``"instructions"`` and ``"kanban_summary"``.

    Either source may fail independently — the hook logs a warning and
    falls back to an empty string for the failing portion.

    Args:
        instructions_path: Path to the Markdown instructions file.
            Defaults to ``.github/copilot-instructions.md``.
        kanban_cmd: Command list for the kanban summary.
            Defaults to ``["kanban/kanban-md.exe", "context"]``.
    """

    def __init__(
        self,
        instructions_path: Path | None = None,
        kanban_cmd: list[str] | None = None,
    ) -> None:
        self.instructions_path: Path = (
            instructions_path if instructions_path is not None else _DEFAULT_INSTRUCTIONS
        )
        self.kanban_cmd: list[str] = (
            kanban_cmd if kanban_cmd is not None else list(_DEFAULT_KANBAN_CMD)
        )

    # -- hook callback -------------------------------------------------------

    async def __call__(self, data: SessionStartData) -> None:
        """Read instructions + kanban summary and inject into *data*.

        Args:
            data: Event payload with ``session_id`` key.
        """
        instructions = await self._read_instructions()
        kanban_summary = await self._run_kanban()

        data["context"] = {
            "instructions": instructions,
            "kanban_summary": kanban_summary,
        }

    # -- convenience ---------------------------------------------------------

    def register(self, hooks: HookRegistry) -> None:
        """Register this hook on :pyattr:`HookEvent.SESSION_START`."""
        from owlbear.core.hooks import HookEvent  # noqa: PLC0415

        hooks.register(HookEvent.SESSION_START, self)

    # -- internal ------------------------------------------------------------

    async def _read_instructions(self) -> str:
        """Read the instructions file, returning empty string on failure."""
        try:
            return await asyncio.to_thread(
                self.instructions_path.read_text, encoding="utf-8",
            )
        except (FileNotFoundError, OSError) as exc:
            logger.warning(
                "Could not read instructions file %s: %s",
                self.instructions_path,
                exc,
            )
            return ""

    async def _run_kanban(self) -> str:
        """Run the kanban summary command, returning empty string on failure."""
        try:
            proc = await asyncio.create_subprocess_exec(
                self.kanban_cmd[0],
                *self.kanban_cmd[1:],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_bytes, stderr_bytes = await proc.communicate()
        except OSError as exc:
            logger.warning("Kanban command %s error: %s", self.kanban_cmd, exc)
            return ""

        if proc.returncode != 0:
            logger.warning(
                "Kanban command %s failed (rc=%d): %s",
                self.kanban_cmd,
                proc.returncode,
                stderr_bytes.decode("utf-8", errors="replace"),
            )
            return ""
        return stdout_bytes.decode("utf-8", errors="replace")
