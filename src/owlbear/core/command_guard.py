"""Command safety guard for PRE_TOOL_USE hook.

Provides :class:`CommandSafetyGuard` — a ``PRE_TOOL_USE`` hook that inspects
tool-call payloads and blocks dangerous shell commands or file operations.
Raises :class:`BlockedCommandError` for denied commands or file paths.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from owlbear.core.hooks import HookRegistry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default blocklists
# ---------------------------------------------------------------------------

DEFAULT_BLOCKED_COMMANDS: list[str] = [
    r"rm\s+-rf\s+/",
    r"git\s+push\s+--force",
    r"(?<!uv )(?<!uv run )pip\s+install",
    r"format\s+[cC]:",
    r"del\s+/[sS]\s+/[qQ]",
    r"sudo\s+rm",
]

DEFAULT_BLOCKED_FILES: list[str] = [
    r"\.env$",
]

# Tool names whose ``command`` arg should be checked.
_SHELL_TOOLS: frozenset[str] = frozenset(
    {
        "run_in_terminal",
        "run_command",
        "execute_command",
        "shell",
    }
)

# Tool names whose ``path`` / ``filePath`` arg should be checked.
_FILE_TOOLS: frozenset[str] = frozenset(
    {
        "create_file",
        "write_file",
        "replace_string_in_file",
        "multi_replace_string_in_file",
    }
)


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------


class BlockedCommandError(Exception):
    """Raised when a command or file path is denied by the safety guard.

    Attributes:
        command: The command string or file path that was blocked.
        pattern: The regex pattern that matched.
    """

    def __init__(self, command: str, pattern: str) -> None:
        self.command = command
        self.pattern = pattern
        super().__init__(f"Command blocked by pattern {pattern!r}: {command}")


# ---------------------------------------------------------------------------
# Guard
# ---------------------------------------------------------------------------


class CommandSafetyGuard:
    """``PRE_TOOL_USE`` hook that blocks dangerous shell commands and file ops.

    The guard inspects tool-call payloads and checks the command string or
    file path against configurable regex blocklists.

    Args:
        blocked_commands: Regex patterns for dangerous shell commands.
            Defaults to :data:`DEFAULT_BLOCKED_COMMANDS`.
        blocked_file_patterns: Regex patterns for dangerous file paths.
            Defaults to :data:`DEFAULT_BLOCKED_FILES`.
    """

    def __init__(
        self,
        blocked_commands: list[str] | None = None,
        blocked_file_patterns: list[str] | None = None,
    ) -> None:
        self._blocked_commands = (
            blocked_commands if blocked_commands is not None else list(DEFAULT_BLOCKED_COMMANDS)
        )
        self._blocked_file_patterns = (
            blocked_file_patterns
            if blocked_file_patterns is not None
            else list(DEFAULT_BLOCKED_FILES)
        )

    # -- hook callback -------------------------------------------------------

    async def __call__(self, data: object) -> None:
        """Inspect a ``PRE_TOOL_USE`` payload and block dangerous actions.

        Args:
            data: Event payload — expected ``{"tool_name": str, "args": dict}``.
                Non-dict payloads are silently ignored.

        Raises:
            BlockedCommandError: If the command or file path is denied.
        """
        if not isinstance(data, dict):
            return

        tool_name: str = data.get("tool_name", "")  # type: ignore[assignment]
        args = data.get("args")
        if not isinstance(args, dict):
            if tool_name:
                logger.debug("Tool invocation: %s (no args)", tool_name)
            return

        logger.debug("Tool invocation: %s args=%s", tool_name, args)

        # Shell / terminal commands
        if tool_name in _SHELL_TOOLS:
            cmd: str = args.get("command", "")  # type: ignore[assignment]
            if cmd:
                self.check_command(cmd)

        # File write operations
        if tool_name in _FILE_TOOLS:
            path: str = args.get("path", "") or args.get("filePath", "")  # type: ignore[assignment]
            if path:
                self.check_file_path(path)

    # -- convenience ---------------------------------------------------------

    def register(self, hooks: HookRegistry) -> None:
        """Register this guard on :pyattr:`HookEvent.PRE_TOOL_USE`."""
        from owlbear.core.hooks import HookEvent  # noqa: PLC0415

        hooks.register(HookEvent.PRE_TOOL_USE, self)

    # -- internal ------------------------------------------------------------

    def check_command(self, cmd: str) -> None:
        """Raise :class:`BlockedCommandError` if *cmd* matches a blocked pattern."""
        for pattern in self._blocked_commands:
            if re.search(pattern, cmd):
                logger.warning("Blocked command %r matching pattern %r", cmd, pattern)
                raise BlockedCommandError(cmd, pattern)

    def check_file_path(self, path: str) -> None:
        """Raise :class:`BlockedCommandError` if *path* matches a blocked file pattern."""
        for pattern in self._blocked_file_patterns:
            if re.search(pattern, path):
                logger.warning("Blocked file path %r matching pattern %r", path, pattern)
                raise BlockedCommandError(path, pattern)
