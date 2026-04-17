"""Failing RED-phase tests for KanbanMockAgent — ACP mock agent for E2E testing.

Tests cover: ACP protocol method implementations (initialize, new_session, prompt),
subprocess call verification for kanban-md operations, environment variable configuration
(KANBAN_DIR, KANBAN_BIN), task-ID regex parsing, error handling for missing/invalid task
IDs, and stub-method safety.

All tests fail on current HEAD — tests/fixtures/mock_acp_agent.py does not exist yet.
Task #155: Build mock ACP agent for E2E testing
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from acp import PROTOCOL_VERSION
from acp.schema import InitializeResponse, NewSessionResponse, PromptResponse, TextContentBlock

from tests.fixtures.mock_acp_agent import KanbanMockAgent

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MODULE = "tests.fixtures.mock_acp_agent"
_BOARD_DIR = "/boards/test-155"
_SESSION_ID = "test-session-abc123"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _prompt_blocks(text: str) -> list[TextContentBlock]:
    """Create a single-element prompt block list from plain text."""
    return [TextContentBlock(type="text", text=text)]


def _make_mock_conn() -> MagicMock:
    """Return a mock ACP Client connection."""
    conn = MagicMock()
    conn.session_update = AsyncMock()
    return conn


def _make_agent_with_conn(*, conn: MagicMock | None = None) -> KanbanMockAgent:
    """Create KanbanMockAgent and wire up a mock connection via on_connect()."""
    agent = KanbanMockAgent()
    agent.on_connect(conn if conn is not None else _make_mock_conn())
    return agent


def _subprocess_ok() -> MagicMock:
    """Return a CompletedProcess-like mock with returncode=0."""
    return MagicMock(returncode=0, stdout="", stderr="")


# ---------------------------------------------------------------------------
# TestFromAC_Initialize
# ---------------------------------------------------------------------------


class TestFromAC_Initialize:
    """initialize() must return InitializeResponse carrying the ACP protocol version."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_initialize_returns_initialize_response(self) -> None:
        """initialize() returns an InitializeResponse instance."""
        agent = KanbanMockAgent()
        result = await agent.initialize(protocol_version=PROTOCOL_VERSION)
        assert isinstance(result, InitializeResponse)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_initialize_protocol_version_matches_acp_constant(self) -> None:
        """initialize() response.protocol_version equals acp.PROTOCOL_VERSION."""
        agent = KanbanMockAgent()
        result = await agent.initialize(protocol_version=PROTOCOL_VERSION)
        assert result.protocol_version == PROTOCOL_VERSION


# ---------------------------------------------------------------------------
# TestFromAC_NewSession
# ---------------------------------------------------------------------------


class TestFromAC_NewSession:
    """new_session() must return NewSessionResponse with a non-empty session_id."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_new_session_returns_new_session_response(self) -> None:
        """new_session() returns a NewSessionResponse instance."""
        agent = KanbanMockAgent()
        result = await agent.new_session(cwd="/workspace")
        assert isinstance(result, NewSessionResponse)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_new_session_has_non_empty_session_id(self) -> None:
        """new_session() response.session_id is a non-empty string."""
        agent = KanbanMockAgent()
        result = await agent.new_session(cwd="/workspace")
        assert isinstance(result.session_id, str)
        assert len(result.session_id) > 0


# ---------------------------------------------------------------------------
# TestFromAC_PromptTaskIdParsing
# ---------------------------------------------------------------------------


class TestFromAC_PromptTaskIdParsing:
    """prompt() extracts task ID from first TextContentBlock via regex #(\\d+)."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_prompt_parses_bare_hash_id(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """prompt('#42') calls kanban-md with task ID '42'."""
        monkeypatch.setenv("KANBAN_DIR", _BOARD_DIR)
        monkeypatch.delenv("KANBAN_BIN", raising=False)
        agent = _make_agent_with_conn()
        with patch(f"{_MODULE}.subprocess.run", return_value=_subprocess_ok()) as mock_run:
            await agent.prompt(prompt=_prompt_blocks("#42"), session_id=_SESSION_ID)
        all_args: list[list[str]] = [c.args[0] for c in mock_run.call_args_list]
        show_args = next(a for a in all_args if "show" in a)
        assert "42" in show_args

    @pytest.mark.asyncio(loop_scope="function")
    async def test_prompt_parses_id_surrounded_by_text(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """prompt() extracts task ID when '#N' is embedded in a longer sentence."""
        monkeypatch.setenv("KANBAN_DIR", _BOARD_DIR)
        monkeypatch.delenv("KANBAN_BIN", raising=False)
        agent = _make_agent_with_conn()
        with patch(f"{_MODULE}.subprocess.run", return_value=_subprocess_ok()) as mock_run:
            await agent.prompt(
                prompt=_prompt_blocks("Please work on task #99 and finish it"),
                session_id=_SESSION_ID,
            )
        all_args: list[list[str]] = [c.args[0] for c in mock_run.call_args_list]
        show_args = next(a for a in all_args if "show" in a)
        assert "99" in show_args

    @pytest.mark.asyncio(loop_scope="function")
    async def test_prompt_uses_first_id_when_multiple_present(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """prompt() uses the first matching #N when multiple task IDs appear in text."""
        monkeypatch.setenv("KANBAN_DIR", _BOARD_DIR)
        monkeypatch.delenv("KANBAN_BIN", raising=False)
        agent = _make_agent_with_conn()
        with patch(f"{_MODULE}.subprocess.run", return_value=_subprocess_ok()) as mock_run:
            await agent.prompt(
                prompt=_prompt_blocks("#10 is parent of #20"),
                session_id=_SESSION_ID,
            )
        all_args: list[list[str]] = [c.args[0] for c in mock_run.call_args_list]
        show_args = next(a for a in all_args if "show" in a)
        assert "10" in show_args
        assert "20" not in show_args

    @pytest.mark.asyncio(loop_scope="function")
    async def test_prompt_raises_on_missing_task_id(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """prompt() raises an exception when no #N is present in the prompt text."""
        monkeypatch.setenv("KANBAN_DIR", _BOARD_DIR)
        monkeypatch.delenv("KANBAN_BIN", raising=False)
        agent = _make_agent_with_conn()
        with (
            patch(f"{_MODULE}.subprocess.run", return_value=_subprocess_ok()),
            pytest.raises((ValueError, RuntimeError, Exception)),
        ):
            await agent.prompt(
                prompt=_prompt_blocks("no task id here"),
                session_id=_SESSION_ID,
            )

    @pytest.mark.asyncio(loop_scope="function")
    async def test_prompt_raises_on_empty_prompt_text(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """prompt() raises an exception when the TextContentBlock contains empty text."""
        monkeypatch.setenv("KANBAN_DIR", _BOARD_DIR)
        monkeypatch.delenv("KANBAN_BIN", raising=False)
        agent = _make_agent_with_conn()
        with (
            patch(f"{_MODULE}.subprocess.run", return_value=_subprocess_ok()),
            pytest.raises((ValueError, RuntimeError, Exception)),
        ):
            await agent.prompt(
                prompt=_prompt_blocks(""),
                session_id=_SESSION_ID,
            )


# ---------------------------------------------------------------------------
# TestFromAC_PromptSubprocessCalls
# ---------------------------------------------------------------------------


class TestFromAC_PromptSubprocessCalls:
    """prompt() calls kanban-md show, edit, and move as list-args subprocesses (no shell=True)."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_prompt_calls_show_with_task_id(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """prompt() calls subprocess.run with 'show' and the task ID."""
        monkeypatch.setenv("KANBAN_DIR", _BOARD_DIR)
        monkeypatch.delenv("KANBAN_BIN", raising=False)
        agent = _make_agent_with_conn()
        with patch(f"{_MODULE}.subprocess.run", return_value=_subprocess_ok()) as mock_run:
            await agent.prompt(prompt=_prompt_blocks("#42"), session_id=_SESSION_ID)
        all_args: list[list[str]] = [c.args[0] for c in mock_run.call_args_list]
        show_calls = [a for a in all_args if "show" in a]
        assert len(show_calls) >= 1, "show must be called at least once"
        assert "42" in show_calls[0]

    @pytest.mark.asyncio(loop_scope="function")
    async def test_prompt_calls_edit_with_annotation(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """prompt() calls subprocess.run with 'edit', the task ID, and 'Mock agent processed' text."""
        monkeypatch.setenv("KANBAN_DIR", _BOARD_DIR)
        monkeypatch.delenv("KANBAN_BIN", raising=False)
        agent = _make_agent_with_conn()
        with patch(f"{_MODULE}.subprocess.run", return_value=_subprocess_ok()) as mock_run:
            await agent.prompt(prompt=_prompt_blocks("#42"), session_id=_SESSION_ID)
        all_args: list[list[str]] = [c.args[0] for c in mock_run.call_args_list]
        edit_calls = [a for a in all_args if "edit" in a]
        assert len(edit_calls) >= 1, "edit must be called at least once"
        combined = " ".join(edit_calls[0])
        assert "Mock agent processed" in combined

    @pytest.mark.asyncio(loop_scope="function")
    async def test_prompt_calls_move_with_task_id(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """prompt() calls subprocess.run with 'move' and the task ID."""
        monkeypatch.setenv("KANBAN_DIR", _BOARD_DIR)
        monkeypatch.delenv("KANBAN_BIN", raising=False)
        agent = _make_agent_with_conn()
        with patch(f"{_MODULE}.subprocess.run", return_value=_subprocess_ok()) as mock_run:
            await agent.prompt(prompt=_prompt_blocks("#42"), session_id=_SESSION_ID)
        all_args: list[list[str]] = [c.args[0] for c in mock_run.call_args_list]
        move_calls = [a for a in all_args if "move" in a]
        assert len(move_calls) >= 1, "move must be called at least once"
        assert "42" in move_calls[0]

    @pytest.mark.asyncio(loop_scope="function")
    async def test_prompt_subprocess_args_are_list_not_shell(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """All subprocess.run calls use list args and must not pass shell=True."""
        monkeypatch.setenv("KANBAN_DIR", _BOARD_DIR)
        monkeypatch.delenv("KANBAN_BIN", raising=False)
        agent = _make_agent_with_conn()
        with patch(f"{_MODULE}.subprocess.run", return_value=_subprocess_ok()) as mock_run:
            await agent.prompt(prompt=_prompt_blocks("#42"), session_id=_SESSION_ID)
        for c in mock_run.call_args_list:
            # First positional arg must be a list, not a string
            assert isinstance(c.args[0], list), "subprocess.run must receive a list, not a string"
            # shell must not be True
            shell = c.kwargs.get("shell", False) if c.kwargs else False
            assert shell is not True, "subprocess.run must not use shell=True"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_prompt_subprocess_calls_include_board_dir(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """All kanban-md subprocess calls include the KANBAN_DIR board directory."""
        monkeypatch.setenv("KANBAN_DIR", _BOARD_DIR)
        monkeypatch.delenv("KANBAN_BIN", raising=False)
        agent = _make_agent_with_conn()
        with patch(f"{_MODULE}.subprocess.run", return_value=_subprocess_ok()) as mock_run:
            await agent.prompt(prompt=_prompt_blocks("#42"), session_id=_SESSION_ID)
        for c in mock_run.call_args_list:
            args_str = " ".join(c.args[0])
            assert _BOARD_DIR in args_str, f"KANBAN_DIR must appear in call args: {c.args[0]}"


# ---------------------------------------------------------------------------
# TestFromAC_PromptResponse
# ---------------------------------------------------------------------------


class TestFromAC_PromptResponse:
    """prompt() must return PromptResponse(stop_reason='end_turn')."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_prompt_returns_prompt_response(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """prompt() return value is a PromptResponse instance."""
        monkeypatch.setenv("KANBAN_DIR", _BOARD_DIR)
        monkeypatch.delenv("KANBAN_BIN", raising=False)
        agent = _make_agent_with_conn()
        with patch(f"{_MODULE}.subprocess.run", return_value=_subprocess_ok()):
            result = await agent.prompt(prompt=_prompt_blocks("#42"), session_id=_SESSION_ID)
        assert isinstance(result, PromptResponse)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_prompt_stop_reason_is_end_turn(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """prompt() response.stop_reason is 'end_turn'."""
        monkeypatch.setenv("KANBAN_DIR", _BOARD_DIR)
        monkeypatch.delenv("KANBAN_BIN", raising=False)
        agent = _make_agent_with_conn()
        with patch(f"{_MODULE}.subprocess.run", return_value=_subprocess_ok()):
            result = await agent.prompt(prompt=_prompt_blocks("#42"), session_id=_SESSION_ID)
        assert result.stop_reason == "end_turn"


# ---------------------------------------------------------------------------
# TestFromAC_EnvVarConfig
# ---------------------------------------------------------------------------


class TestFromAC_EnvVarConfig:
    """Board dir and binary path are resolved from KANBAN_DIR / KANBAN_BIN env vars."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_kanban_bin_env_var_used_for_binary_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When KANBAN_BIN is set, that path is used as the kanban-md binary."""
        custom_bin = "/custom/path/kanban-md"
        monkeypatch.setenv("KANBAN_BIN", custom_bin)
        monkeypatch.setenv("KANBAN_DIR", _BOARD_DIR)
        agent = _make_agent_with_conn()
        with patch(f"{_MODULE}.subprocess.run", return_value=_subprocess_ok()) as mock_run:
            await agent.prompt(prompt=_prompt_blocks("#42"), session_id=_SESSION_ID)
        first_call_args = mock_run.call_args_list[0].args[0]
        assert first_call_args[0] == custom_bin, f"Binary must be KANBAN_BIN '{custom_bin}', got '{first_call_args[0]}'"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_kanban_bin_fallback_when_env_var_absent(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When KANBAN_BIN is unset, binary falls back to 'kanban/kanban-md'."""
        monkeypatch.delenv("KANBAN_BIN", raising=False)
        monkeypatch.setenv("KANBAN_DIR", _BOARD_DIR)
        agent = _make_agent_with_conn()
        with patch(f"{_MODULE}.subprocess.run", return_value=_subprocess_ok()) as mock_run:
            await agent.prompt(prompt=_prompt_blocks("#42"), session_id=_SESSION_ID)
        first_call_args = mock_run.call_args_list[0].args[0]
        assert first_call_args[0] == "kanban/kanban-md", (
            f"Default binary must be 'kanban/kanban-md', got '{first_call_args[0]}'"
        )

    @pytest.mark.asyncio(loop_scope="function")
    async def test_kanban_dir_env_var_passed_to_all_subprocess_calls(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """KANBAN_DIR env var value appears in every kanban-md subprocess call."""
        custom_dir = "/custom/board/dir"
        monkeypatch.setenv("KANBAN_DIR", custom_dir)
        monkeypatch.delenv("KANBAN_BIN", raising=False)
        agent = _make_agent_with_conn()
        with patch(f"{_MODULE}.subprocess.run", return_value=_subprocess_ok()) as mock_run:
            await agent.prompt(prompt=_prompt_blocks("#42"), session_id=_SESSION_ID)
        assert len(mock_run.call_args_list) >= 3, "Expected show + edit + move calls"  # noqa: PLR2004
        for c in mock_run.call_args_list:
            args_str = " ".join(c.args[0])
            assert custom_dir in args_str, f"KANBAN_DIR '{custom_dir}' must appear in call args: {c.args[0]}"


# ---------------------------------------------------------------------------
# TestFromAC_StubMethods
# ---------------------------------------------------------------------------


class TestFromAC_StubMethods:
    """Remaining Agent Protocol methods return defaults and do not raise."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_cancel_does_not_raise(self) -> None:
        """cancel() returns None without raising an exception."""
        agent = KanbanMockAgent()
        result = await agent.cancel(session_id=_SESSION_ID)
        assert result is None

    @pytest.mark.asyncio(loop_scope="function")
    async def test_load_session_returns_none_or_default(self) -> None:
        """load_session() stub returns None or a default response without raising."""
        agent = KanbanMockAgent()
        await agent.load_session(cwd="/workspace", session_id=_SESSION_ID)
        # Verification: no exception raised; return value is not constrained by AC

    @pytest.mark.asyncio(loop_scope="function")
    async def test_close_session_does_not_raise(self) -> None:
        """close_session() stub returns without raising an exception."""
        agent = KanbanMockAgent()
        await agent.close_session(session_id=_SESSION_ID)
        # Verification: no exception raised; return value is not constrained by AC
