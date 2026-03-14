"""Command safety guard for PRE_TOOL_USE hook.

Provides :class:`CommandSafetyGuard` — a ``PRE_TOOL_USE`` hook that inspects
tool-call payloads and blocks dangerous shell commands or file operations.
Raises :class:`BlockedCommandError` for denied commands or file paths.

NOTE: This blocklist is defense-in-depth only — it is NOT a security boundary.
The approval gate on run_command is the primary control. Regex blocklists
are provably insufficient for shell command safety.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from owlbear.core.exceptions import OwlBearError
from owlbear.core.hooks import PreToolUseData  # noqa: TC001

if TYPE_CHECKING:
    from owlbear.core.hooks import HookRegistry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default blocklists
# ---------------------------------------------------------------------------

DEFAULT_BLOCKED_COMMANDS: list[str] = [
    # rm: -rf combined, -r -f separated, --recursive --force long flags
    r"rm\s+-rf\s+/",
    r"rm\s+(-[a-z]*r[a-z]*\s+)*-[a-z]*f[a-z]*\s+/",
    r"rm\s+(-[a-z]*f[a-z]*\s+)*-[a-z]*r[a-z]*\s+/",
    r"rm\s+--recursive\s+--force\b",
    r"rm\s+--force\s+--recursive\b",
    r"sudo\s+rm",
    # git push: --force, -f, --force-with-lease
    r"git\s+push\s+--force",
    r"git\s+push\s+-f\b",
    # pip: bare pip and python -m pip
    r"(?<!uv )(?<!uv run )pip\s+install",
    r"python\d?\s+-m\s+pip\s+install",
    # Windows: format, del, Remove-Item -Recurse -Force
    r"format\s+[cC]:",
    r"del\s+/[sS]\s+/[qQ]",
    r"(?i)Remove-Item\s+.*-Recurse.*-Force",
    r"(?i)Remove-Item\s+.*-Force.*-Recurse",
    # git: destructive index/worktree mutations
    r"git\s+sparse-checkout",
    r"git\s+reset\s+--hard",
    r"git\s+clean\s+-[a-z]*f",
    # System: chmod 777, mkfs, dd if=, shutdown, reboot
    r"chmod\s+777\b",
    r"mkfs",
    r"\bdd\s+if=",
    r"(?:sudo\s+)?shutdown\b",
    r"(?:sudo\s+)?reboot\b",
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


class BlockedCommandError(OwlBearError):
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

    async def __call__(self, data: PreToolUseData) -> None:
        """Inspect a ``PRE_TOOL_USE`` payload and block dangerous actions.

        Args:
            data: Event payload with ``tool_name`` and ``args`` keys.

        Raises:
            BlockedCommandError: If the command or file path is denied.
        """
        tool_name: str = data.get("tool_name", "")
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
