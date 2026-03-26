"""Tests for CommandSafetyGuard — PRE_TOOL_USE command/file safety guard.

Covers: blocklist matching for shell commands, file path blocking,
configurable patterns, DEBUG logging of all invocations, HookRegistry
integration, and edge cases.
"""

from __future__ import annotations

import logging

import pytest

from owlbear.core.command_guard import (
    DEFAULT_BLOCKED_COMMANDS,
    DEFAULT_BLOCKED_FILES,
    BlockedCommandError,
    CommandSafetyGuard,
)
from owlbear.core.hooks import HookEvent, HookRegistry

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _shell_data(command: str) -> dict[str, object]:
    """Build a PRE_TOOL_USE payload for a shell/terminal tool."""
    return {"tool_name": "run_in_terminal", "args": {"command": command}}


def _file_data(path: str) -> dict[str, object]:
    """Build a PRE_TOOL_USE payload for a file write tool."""
    return {"tool_name": "create_file", "args": {"path": path}}


# ---------------------------------------------------------------------------
# BlockedCommandError
# ---------------------------------------------------------------------------


class TestBlockedCommandError:
    """Custom exception stores command and pattern."""

    def test_is_exception(self) -> None:
        err = BlockedCommandError("rm -rf /", r"rm\s+-rf\s+/")
        assert isinstance(err, Exception)

    def test_stores_command_and_pattern(self) -> None:
        err = BlockedCommandError("rm -rf /", r"rm\s+-rf\s+/")
        assert err.command == "rm -rf /"
        assert err.pattern == r"rm\s+-rf\s+/"

    def test_message_contains_command(self) -> None:
        err = BlockedCommandError("rm -rf /", r"rm\s+-rf\s+/")
        assert "rm -rf /" in str(err)

    def test_message_contains_pattern(self) -> None:
        err = BlockedCommandError("rm -rf /", r"rm\s+-rf\s+/")
        assert "pattern" in str(err).lower()
        assert "rm -rf /" in str(err)


# ---------------------------------------------------------------------------
# Default patterns
# ---------------------------------------------------------------------------


class TestDefaultPatterns:
    """Module-level defaults are populated."""

    def test_default_blocked_commands_is_non_empty(self) -> None:
        assert len(DEFAULT_BLOCKED_COMMANDS) >= 15

    def test_default_blocked_files_is_non_empty(self) -> None:
        assert len(DEFAULT_BLOCKED_FILES) >= 1


# ---------------------------------------------------------------------------
# Blocking dangerous shell commands
# ---------------------------------------------------------------------------


class TestCommandSafetyGuardBlocking:
    """Guard blocks dangerous shell commands."""

    @pytest.mark.parametrize(
        "cmd",
        [
            "rm -rf /",
            "rm  -rf  /home",
            "sudo rm -rf /var",
            "git push --force",
            "git push --force origin main",
            "pip install requests",
            "pip install -r requirements.txt",
            "format C:",
            "format c:",
            "del /s /q C:\\Windows",
            "del /S /Q .",
            "sudo rm important_file",
        ],
    )
    @pytest.mark.asyncio
    async def test_blocks_dangerous_command(self, cmd: str) -> None:
        guard = CommandSafetyGuard()
        with pytest.raises(BlockedCommandError):
            await (guard(_shell_data(cmd)))

    @pytest.mark.parametrize(
        "cmd",
        [
            "ls -la",
            "git push origin main",
            "git status",
            "uv pip install requests",
            "uv run pip install requests",
            "echo hello",
            "cat file.txt",
            "python script.py",
            "rm file.txt",
            "mkdir new_dir",
        ],
    )
    @pytest.mark.asyncio
    async def test_allows_safe_command(self, cmd: str) -> None:
        guard = CommandSafetyGuard()
        await (guard(_shell_data(cmd)))  # should NOT raise


# ---------------------------------------------------------------------------
# Blocking dangerous file operations
# ---------------------------------------------------------------------------


class TestCommandSafetyGuardFileBlocking:
    """Guard blocks dangerous file operations."""

    @pytest.mark.parametrize(
        "path",
        [
            ".env",
            "config/.env",
            "/home/user/project/.env",
        ],
    )
    @pytest.mark.asyncio
    async def test_blocks_env_file_write(self, path: str) -> None:
        guard = CommandSafetyGuard()
        with pytest.raises(BlockedCommandError):
            await (guard(_file_data(path)))

    @pytest.mark.parametrize(
        "path",
        [
            "src/main.py",
            ".envrc",
            ".environment",
            "config/settings.toml",
        ],
    )
    @pytest.mark.asyncio
    async def test_allows_safe_file_paths(self, path: str) -> None:
        guard = CommandSafetyGuard()
        await (guard(_file_data(path)))  # should NOT raise


# ---------------------------------------------------------------------------
# Configurable patterns
# ---------------------------------------------------------------------------


class TestCommandSafetyGuardConfigurable:
    """Guard supports custom blocklists."""

    @pytest.mark.asyncio
    async def test_custom_blocked_commands(self) -> None:
        guard = CommandSafetyGuard(blocked_commands=[r"drop\s+table"])
        with pytest.raises(BlockedCommandError):
            await (guard(_shell_data("drop table users")))

    @pytest.mark.asyncio
    async def test_custom_blocked_commands_allows_default_dangerous(self) -> None:
        """When custom patterns replace defaults, old patterns no longer block."""
        guard = CommandSafetyGuard(blocked_commands=[r"drop\s+table"])
        await (guard(_shell_data("rm -rf /")))  # no longer blocked

    @pytest.mark.asyncio
    async def test_custom_blocked_file_patterns(self) -> None:
        guard = CommandSafetyGuard(blocked_file_patterns=[r"\.secret$"])
        with pytest.raises(BlockedCommandError):
            await (guard(_file_data("creds.secret")))

    @pytest.mark.asyncio
    async def test_custom_file_patterns_allows_default_blocked(self) -> None:
        guard = CommandSafetyGuard(blocked_file_patterns=[r"\.secret$"])
        await (guard(_file_data(".env")))  # no longer blocked


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestCommandSafetyGuardEdgeCases:
    """Edge cases: missing fields, non-shell tools."""

    @pytest.mark.asyncio
    async def test_non_shell_tool_without_file_path_ignored(self) -> None:
        guard = CommandSafetyGuard()
        data: dict[str, object] = {"tool_name": "semantic_search", "args": {"query": "rm -rf /"}}
        await (guard(data))  # no raise — not a shell or file tool

    @pytest.mark.asyncio
    async def test_missing_args_key_ignored(self) -> None:
        guard = CommandSafetyGuard()
        data: dict[str, object] = {"tool_name": "run_in_terminal"}
        await (guard(data))  # no raise

    @pytest.mark.asyncio
    async def test_missing_command_in_args_ignored(self) -> None:
        guard = CommandSafetyGuard()
        data: dict[str, object] = {"tool_name": "run_in_terminal", "args": {}}
        await (guard(data))  # no raise

    @pytest.mark.asyncio
    async def test_empty_command_ignored(self) -> None:
        guard = CommandSafetyGuard()
        await (guard(_shell_data("")))  # no raise

    @pytest.mark.asyncio
    async def test_missing_path_in_file_args_ignored(self) -> None:
        guard = CommandSafetyGuard()
        data: dict[str, object] = {"tool_name": "create_file", "args": {}}
        await (guard(data))  # no raise

    @pytest.mark.asyncio
    async def test_args_not_dict_ignored(self) -> None:
        guard = CommandSafetyGuard()
        data: dict[str, object] = {"tool_name": "run_in_terminal", "args": "bad"}
        await (guard(data))  # no raise

    @pytest.mark.asyncio
    async def test_file_tool_with_file_path_key(self) -> None:
        """Some tools use 'filePath' instead of 'path'."""
        guard = CommandSafetyGuard()
        data: dict[str, object] = {"tool_name": "create_file", "args": {"filePath": ".env"}}
        with pytest.raises(BlockedCommandError):
            await (guard(data))


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------


class TestCommandSafetyGuardLogging:
    """All tool invocations are logged at DEBUG; blocked ones at WARNING."""

    @pytest.mark.asyncio
    async def test_logs_all_invocations_at_debug(self, caplog: pytest.LogCaptureFixture) -> None:
        guard = CommandSafetyGuard()
        with caplog.at_level(logging.DEBUG, logger="owlbear.core.command_guard"):
            await (guard(_shell_data("echo hello")))
        assert "run_in_terminal" in caplog.text

    @pytest.mark.asyncio
    async def test_logs_blocked_command_at_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        guard = CommandSafetyGuard()
        with (
            caplog.at_level(logging.WARNING, logger="owlbear.core.command_guard"),
            pytest.raises(BlockedCommandError),
        ):
            await (guard(_shell_data("rm -rf /")))
        assert "rm -rf /" in caplog.text

    @pytest.mark.asyncio
    async def test_logs_blocked_file_at_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        guard = CommandSafetyGuard()
        with (
            caplog.at_level(logging.WARNING, logger="owlbear.core.command_guard"),
            pytest.raises(BlockedCommandError),
        ):
            await (guard(_file_data(".env")))
        assert ".env" in caplog.text


# ---------------------------------------------------------------------------
# HookRegistry integration
# ---------------------------------------------------------------------------


class TestCommandSafetyGuardHookIntegration:
    """Guard registers on HookRegistry and fires on PRE_TOOL_USE."""

    def test_register_adds_to_pre_tool_use(self) -> None:
        guard = CommandSafetyGuard()
        registry = HookRegistry()
        guard.register(registry)
        handlers = registry.handlers.get(HookEvent.PRE_TOOL_USE, [])
        assert guard in handlers

    @pytest.mark.asyncio
    async def test_emit_invokes_guard_for_safe_command(self) -> None:
        guard = CommandSafetyGuard()
        registry = HookRegistry()
        guard.register(registry)
        await (registry.emit(HookEvent.PRE_TOOL_USE, _shell_data("echo hello")))

    @pytest.mark.asyncio
    async def test_emit_blocked_command_swallowed_by_registry(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        guard = CommandSafetyGuard()
        registry = HookRegistry()
        guard.register(registry)
        with caplog.at_level(logging.WARNING):
            await (
                registry.emit(
                    HookEvent.PRE_TOOL_USE,
                    _shell_data("rm -rf /"),
                )
            )
        assert "rm -rf /" in caplog.text


# ---------------------------------------------------------------------------
# Expanded blocklist patterns (SEC-04)
# ---------------------------------------------------------------------------


class TestExpandedRmPatterns:
    """rm variants: -r -f separated flags, --recursive --force long flags."""

    @pytest.mark.parametrize(
        "cmd",
        [
            "rm -r -f /home",
            "rm -f -r /tmp",
            "rm --recursive --force /var",
            "rm --force --recursive /etc",
            "rm -r -f  /data",
        ],
    )
    @pytest.mark.asyncio
    async def test_blocks_rm_recursive_force_variants(self, cmd: str) -> None:
        guard = CommandSafetyGuard()
        with pytest.raises(BlockedCommandError):
            await (guard(_shell_data(cmd)))

    @pytest.mark.asyncio
    async def test_allows_rm_single_file(self) -> None:
        guard = CommandSafetyGuard()
        await (guard(_shell_data("rm file.txt")))

    @pytest.mark.asyncio
    async def test_allows_rm_single_flag(self) -> None:
        guard = CommandSafetyGuard()
        await (guard(_shell_data("rm -r dir/")))


class TestExpandedGitPushPatterns:
    """git push: -f shorthand and --force-with-lease."""

    @pytest.mark.parametrize(
        "cmd",
        [
            "git push -f",
            "git push -f origin main",
            "git push --force-with-lease",
            "git push --force-with-lease origin main",
        ],
    )
    @pytest.mark.asyncio
    async def test_blocks_force_push_variants(self, cmd: str) -> None:
        guard = CommandSafetyGuard()
        with pytest.raises(BlockedCommandError):
            await (guard(_shell_data(cmd)))

    @pytest.mark.asyncio
    async def test_allows_normal_push(self) -> None:
        guard = CommandSafetyGuard()
        await (guard(_shell_data("git push origin main")))


class TestPythonMPipPattern:
    """python -m pip should be blocked like bare pip."""

    @pytest.mark.parametrize(
        "cmd",
        [
            "python -m pip install requests",
            "python3 -m pip install flask",
            "python -m pip install -r requirements.txt",
        ],
    )
    @pytest.mark.asyncio
    async def test_blocks_python_m_pip(self, cmd: str) -> None:
        guard = CommandSafetyGuard()
        with pytest.raises(BlockedCommandError):
            await (guard(_shell_data(cmd)))

    @pytest.mark.asyncio
    async def test_blocks_uv_run_python_m_pip(self) -> None:
        """uv run python -m pip still invokes system pip — blocked."""
        guard = CommandSafetyGuard()
        with pytest.raises(BlockedCommandError):
            await (guard(_shell_data("uv run python -m pip install requests")))


class TestRemoveItemPattern:
    """PowerShell Remove-Item -Recurse -Force variants."""

    @pytest.mark.parametrize(
        "cmd",
        [
            "Remove-Item -Recurse -Force C:\\dir",
            "Remove-Item -Force -Recurse .",
            "Remove-Item -Recurse -Force -Path C:\\data",
        ],
    )
    @pytest.mark.asyncio
    async def test_blocks_remove_item_recursive_force(self, cmd: str) -> None:
        guard = CommandSafetyGuard()
        with pytest.raises(BlockedCommandError):
            await (guard(_shell_data(cmd)))

    @pytest.mark.asyncio
    async def test_allows_remove_item_single_file(self) -> None:
        guard = CommandSafetyGuard()
        await (guard(_shell_data("Remove-Item file.txt")))


class TestAdditionalDangerousCommands:
    """chmod 777, mkfs, dd if=, shutdown, reboot."""

    @pytest.mark.parametrize(
        "cmd",
        [
            "chmod 777 /var/www",
            "chmod 777 file.sh",
            "mkfs /dev/sda1",
            "mkfs.ext4 /dev/sda1",
            "dd if=/dev/zero of=/dev/sda",
            "dd if=/dev/urandom of=/dev/sdb bs=1M",
            "shutdown -h now",
            "shutdown /s",
            "reboot",
            "reboot -f",
            "sudo reboot",
            "sudo shutdown now",
        ],
    )
    @pytest.mark.asyncio
    async def test_blocks_dangerous_system_commands(self, cmd: str) -> None:
        guard = CommandSafetyGuard()
        with pytest.raises(BlockedCommandError):
            await (guard(_shell_data(cmd)))


class TestGitDestructivePatterns:
    """git sparse-checkout, reset --hard, clean -f."""

    @pytest.mark.parametrize(
        "cmd",
        [
            "git sparse-checkout set gemini/agents",
            "git sparse-checkout init --cone",
            "git sparse-checkout disable",
            "git reset --hard",
            "git reset --hard HEAD~1",
            "git clean -fd",
            "git clean -fxd",
        ],
    )
    @pytest.mark.asyncio
    async def test_blocks_destructive_git_commands(self, cmd: str) -> None:
        guard = CommandSafetyGuard()
        with pytest.raises(BlockedCommandError):
            await (guard(_shell_data(cmd)))

    @pytest.mark.asyncio
    async def test_allows_normal_git_operations(self) -> None:
        guard = CommandSafetyGuard()
        await (guard(_shell_data("git status")))
        await (guard(_shell_data("git checkout main")))
        await (guard(_shell_data("git reset HEAD file.txt")))
