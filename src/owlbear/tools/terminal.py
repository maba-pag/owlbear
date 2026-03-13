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

from owlbear.core.hooks import emit_pre_tool_use
from owlbear.paths import sandbox_path

if TYPE_CHECKING:
    from typing import ClassVar

    from owlbear.core.hooks import HookRegistry

__all__ = ["TerminalResult", "TerminalToolset", "classify_exit"]

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class TerminalResult:
    """Immutable result of a shell command execution.

    Attributes:
        stdout: Decoded standard output (UTF-8, ``errors="replace"``).
        stderr: Decoded standard error (UTF-8, ``errors="replace"``).
        exit_code: Process return code (``-1`` when unknown after timeout).
        timed_out: ``True`` when the process was killed due to timeout.
        soft_fail: ``True`` when exit code 1 with meaningful stdout (see
            :func:`classify_exit`).
    """

    stdout: str
    stderr: str
    exit_code: int
    timed_out: bool
    soft_fail: bool = False


def classify_exit(exit_code: int, stdout: str) -> bool:
    """Return ``True`` when *exit_code* is 1 and *stdout* has meaningful content.

    A "soft fail" is a command that exited with code 1 but produced useful
    output (e.g. ``grep`` with no matches, ``diff`` with differences).  Exit 0
    (success) and exit >= 2 (real errors) are never classified as soft fail.
    """
    return exit_code == 1 and bool(stdout.strip())


def _truncate(output: str, max_bytes: int) -> str:
    """Apply head+tail truncation if *output* exceeds *max_bytes*.

    Uses a 60/40 head/tail byte budget and snaps at newline boundaries
    when possible.  Produces a marker like::

        [N lines / X.YKB truncated -- showing first A + last B lines]
    """
    if len(output) <= max_bytes:
        return output

    head_budget = int(max_bytes * 0.6)
    tail_budget = max_bytes - head_budget

    # --- head: snap to last newline within budget -----------------------
    newline_pos = output.rfind("\n", 0, head_budget)
    head = output[: newline_pos + 1] if newline_pos > 0 else output[:head_budget]

    # --- tail: snap to first newline within tail region -----------------
    tail_start_raw = len(output) - tail_budget
    newline_pos = output.find("\n", tail_start_raw)
    if newline_pos != -1 and newline_pos < len(output) - 1:
        tail = output[newline_pos + 1 :]  # start after the newline
    else:
        tail = output[tail_start_raw:]  # no newline → character split

    # --- marker ---------------------------------------------------------
    total_lines = output.count("\n") + (0 if output.endswith("\n") else 1)
    head_lines = head.count("\n") + (0 if head.endswith("\n") else 1)
    tail_lines = tail.count("\n") + (0 if tail.endswith("\n") else 1)
    # For zero-newline content, count as 1 line each
    if "\n" not in head and head:
        head_lines = 1
    if "\n" not in tail and tail:
        tail_lines = 1
    truncated_lines = max(total_lines - head_lines - tail_lines, 0)
    omitted_bytes = len(output) - len(head) - len(tail)
    omitted_kb = round(omitted_bytes / 1024, 1)

    marker = (
        f"[{truncated_lines} lines / {omitted_kb}KB truncated"
        f" -- showing first {head_lines} + last {tail_lines} lines]"
    )
    return f"{head}{marker}\n{tail}"


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
        if result.soft_fail:
            parts.append("(soft-fail)")
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
        await emit_pre_tool_use(self._hooks, "run_command", {"command": command})

        # -- Resolve working directory ------------------------------------
        if working_dir is None:
            cwd = self._workspace_root
        else:
            cwd = sandbox_path(self._workspace_root, working_dir)

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
            soft_fail=classify_exit(exit_code, stdout),
        )
