"""ProcessSupervisor — ACP subprocess lifecycle management."""

from __future__ import annotations

import asyncio
import contextlib
import shutil
from typing import TYPE_CHECKING, Self


class ProcessRestartBudgetExhausted(Exception):
    """Raised when the process restart budget is exhausted."""


class ProcessSupervisor:
    """Manage an ACP subprocess lifecycle with restart budgeting.

    Usage::

        async with ProcessSupervisor(["copilot", "--acp", "--stdio"]) as sup:
            stdin, stdout = await sup.ensure_running()
    """

    def __init__(self, command: list[str], max_restarts: int = 3) -> None:
        self._command = command
        self._max_restarts = max_restarts
        self._proc: asyncio.subprocess.Process | None = None
        self._restart_count = 0

    async def __aenter__(self) -> Self:
        await self._spawn()
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.shutdown()

    async def _spawn(self) -> None:
        binary = self._command[0]
        if shutil.which(binary) is None:
            msg = f"Binary not found: {binary}"
            raise FileNotFoundError(msg)
        proc = await asyncio.create_subprocess_exec(
            *self._command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=None,
        )
        if proc.stdin is None:
            msg = "Spawned process has no stdin"
            raise RuntimeError(msg)
        if proc.stdout is None:
            msg = "Spawned process has no stdout"
            raise RuntimeError(msg)
        self._proc = proc

    async def shutdown(self) -> None:
        """Terminate the subprocess, killing if it does not exit in time."""
        if self._proc is None:
            return
        with contextlib.suppress(ProcessLookupError):
            self._proc.terminate()
        try:
            await asyncio.wait_for(self._proc.wait(), timeout=5.0)
        except TimeoutError:
            with contextlib.suppress(ProcessLookupError):
                self._proc.kill()

    @property
    def is_alive(self) -> bool:
        """Return True when the subprocess is running."""
        return self._proc is not None and self._proc.returncode is None

    async def ensure_running(self) -> tuple[asyncio.StreamWriter, asyncio.StreamReader]:
        """Return (stdin, stdout) pipes, respawning the process if it has died."""
        if not self.is_alive:
            self._restart_count += 1
            if self._restart_count > self._max_restarts:
                msg = f"Process restarted {self._max_restarts} times without mark_healthy()"
                raise ProcessRestartBudgetExhausted(msg)
            await self._spawn()
        if TYPE_CHECKING:
            assert self._proc is not None
        return self._proc.stdin, self._proc.stdout  # type: ignore[return-value]

    def mark_healthy(self) -> None:
        """Reset the restart counter after a successful session."""
        self._restart_count = 0
