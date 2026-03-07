"""TerminalToolset — FunctionToolset wrapping ``run_command`` for shell execution.

Provides a single ``run_command`` tool that runs shell commands via
:func:`asyncio.create_subprocess_shell`, captures stdout/stderr, handles
timeouts, and optionally emits :attr:`HookEvent.PRE_TOOL_USE` hooks.

Usage::

    from owlbear.tools.terminal import TerminalToolset

    toolset = TerminalToolset(workspace_root=Path("."))
    result = await toolset.run_command("echo hello")
    print(result.stdout, result.exit_code)
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic_ai.toolsets import FunctionToolset

from owlbear.core.hooks import HookEvent

if TYPE_CHECKING:
    from typing import ClassVar

    from owlbear.core.hooks import HookRegistry

__all__ = ["TerminalResult", "TerminalToolset"]

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class TerminalResult:
    """Immutable result of a shell command execution.

    Attributes:
        stdout: Decoded standard output (UTF-8, ``errors="replace"``).
        stderr: Decoded standard error (UTF-8, ``errors="replace"``).
        exit_code: Process return code (``-1`` when unknown after timeout).
        timed_out: ``True`` when the process was killed due to timeout.
    """

    stdout: str
    stderr: str
    exit_code: int
    timed_out: bool


def _truncate(output: str, max_bytes: int) -> str:
    """Apply head+tail truncation if *output* exceeds *max_bytes*.

    Keeps the first ``max_bytes // 2`` and last ``max_bytes // 2``
    characters with a ``[...truncated N bytes...]`` marker in between.
    """
    if len(output) <= max_bytes:
        return output

    half = max_bytes // 2
    head = output[:half]
    tail = output[-half:]
    omitted = len(output) - max_bytes
    return f"{head}\n[...truncated {omitted} bytes...]\n{tail}"


class TerminalToolset(FunctionToolset):
    """FunctionToolset subclass that registers a ``run_command`` tool.

    Args:
        workspace_root: Directory used as the default working directory
            for commands.  Defaults to the current directory.
        hooks: Optional :class:`HookRegistry` for emitting
            :attr:`HookEvent.PRE_TOOL_USE` before each command.
        max_output_bytes: Maximum length (in characters) for stdout/stderr
            before head+tail truncation kicks in.  Defaults to ``60_000``.
    """

    tool_alias: ClassVar[str] = "terminal"

    def __init__(
        self,
        workspace_root: Path = Path(),
        *,
        hooks: HookRegistry | None = None,
        max_output_bytes: int = 60_000,
    ) -> None:
        super().__init__()
        self._workspace_root = workspace_root.resolve()
        self._hooks = hooks
        self._max_output_bytes = max_output_bytes
        self._register_tools()

    def update_workspace(self, workspace: Path) -> None:
        """Set the workspace root to *workspace*."""
        self._workspace_root = workspace

    # ------------------------------------------------------------------
    # Tool registration
    # ------------------------------------------------------------------

    def _register_tools(self) -> None:
        """Register the ``run_command`` tool on this toolset."""
        self.add_function(
            self._run_command_wrapper,
            name="run_command",
            description=(
                "Run a shell command and return stdout, stderr, exit code, "
                "and whether it timed out."
            ),
        )

    # ------------------------------------------------------------------
    # Tool wrapper
    # ------------------------------------------------------------------

    async def _run_command_wrapper(
        self,
        command: str,
        working_dir: str | None = None,
        timeout_seconds: float = 30,
    ) -> str:
        """Thin wrapper registered as the tool; delegates to :meth:`run_command`."""
        result = await self.run_command(
            command,
            working_dir=working_dir,
            timeout_seconds=timeout_seconds,
        )
        parts = [f"exit_code={result.exit_code}"]
        if result.timed_out:
            parts.append("TIMED OUT")
        if result.stdout:
            parts.append(f"stdout:\n{result.stdout}")
        if result.stderr:
            parts.append(f"stderr:\n{result.stderr}")
        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run_command(
        self,
        command: str,
        *,
        working_dir: str | None = None,
        timeout_seconds: float = 30,
    ) -> TerminalResult:
        """Execute *command* in a subprocess and return a :class:`TerminalResult`.

        Args:
            command: Shell command string.
            working_dir: Working directory for the command.  Resolved
                relative to *workspace_root* when relative; uses
                *workspace_root* when ``None``.
            timeout_seconds: Maximum wall-clock seconds before the process
                is killed.
        """
        # -- Hook emission ------------------------------------------------
        if self._hooks is not None:
            await self._hooks.emit(
                HookEvent.PRE_TOOL_USE,
                {"tool_name": "run_command", "args": {"command": command}},
            )

        # -- Resolve working directory ------------------------------------
        if working_dir is None:
            cwd = self._workspace_root
        else:
            if "\x00" in working_dir:
                msg = f"Path outside workspace: {working_dir!r}"
                raise PermissionError(msg)
            cwd_path = Path(working_dir)
            cwd = (
                cwd_path if cwd_path.is_absolute() else self._workspace_root / cwd_path
            ).resolve()
            if not cwd.is_relative_to(self._workspace_root):
                msg = f"Path outside workspace: {working_dir}"
                raise PermissionError(msg)

        # -- Launch subprocess --------------------------------------------
        logger.debug("run_command: %r  cwd=%s", command, cwd)
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )

        # -- Wait with timeout --------------------------------------------
        timed_out = False
        try:
            raw_stdout, raw_stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout_seconds,
            )
        except TimeoutError:
            timed_out = True
            proc.kill()
            await proc.wait()
            # Collect any partial output already buffered
            raw_stdout = b""
            raw_stderr = b""
            if proc.stdout is not None:
                with contextlib.suppress(TimeoutError, OSError):
                    raw_stdout = await asyncio.wait_for(proc.stdout.read(), timeout=1)
            if proc.stderr is not None:
                with contextlib.suppress(TimeoutError, OSError):
                    raw_stderr = await asyncio.wait_for(proc.stderr.read(), timeout=1)

        # -- Decode + truncate --------------------------------------------
        stdout = raw_stdout.decode("utf-8", errors="replace")
        stderr = raw_stderr.decode("utf-8", errors="replace")

        stdout = _truncate(stdout, self._max_output_bytes)
        stderr = _truncate(stderr, self._max_output_bytes)

        exit_code = proc.returncode if proc.returncode is not None else -1

        return TerminalResult(
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            timed_out=timed_out,
        )
