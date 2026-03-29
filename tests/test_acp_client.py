"""Failing RED-phase tests for AcpClient wrapper with timeouts and error classification.

Covers: per-method timeout enforcement (initialize 30 s, new_session 15 s, prompt 300 s),
RequestError classification by error code, session/cancel on asyncio.TimeoutError,
external CancelSignal triggering session/cancel, BrokenPipeError and EOF (ConnectionError)
classified as TRANSIENT.

All tests fail on current HEAD because
``packages/orchestrator/src/owlbear_orchestrator/acp_client.py`` does not exist yet.
"""

from __future__ import annotations

import asyncio
import contextlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from acp.client.connection import ClientSideConnection
from acp.exceptions import RequestError
from owlbear_orchestrator.acp_client import AcpClient, AcpClientError, ErrorCategory

_MODULE = "owlbear_orchestrator.acp_client"
_SESSION_ID = "test-session-abc123"


def _make_conn() -> AsyncMock:
    """Return a mock ClientSideConnection with all methods as AsyncMocks.

    Note: ClientSideConnection.initialize, .prompt, and .cancel are wrapped by
    @param_model/@compatible_class decorators, causing iscoroutinefunction() to
    return False. AsyncMock(spec=...) would create MagicMock children for those.
    We explicitly override them so all methods are AsyncMock as the docstring states.
    """
    conn = AsyncMock(spec=ClientSideConnection)
    conn.initialize = AsyncMock()
    conn.prompt = AsyncMock()
    conn.cancel = AsyncMock()
    return conn


# ---------------------------------------------------------------------------
# Timeout enforcement
# ---------------------------------------------------------------------------


class TestFromAC_Timeouts:  # noqa: N801
    """AcpClient wraps each method call in asyncio.wait_for with the specified timeout."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_initialize_uses_30s_timeout(self) -> None:
        """initialize() must pass timeout=30 to asyncio.wait_for."""
        conn = _make_conn()
        client = AcpClient(conn)
        with patch(f"{_MODULE}.asyncio.wait_for", new=AsyncMock(return_value=MagicMock())) as mock_wf:
            await client.initialize()
        _, kwargs = mock_wf.call_args
        assert kwargs.get("timeout") == 30  # noqa: PLR2004

    @pytest.mark.asyncio(loop_scope="function")
    async def test_new_session_uses_15s_timeout(self) -> None:
        """new_session() must pass timeout=15 to asyncio.wait_for."""
        conn = _make_conn()
        client = AcpClient(conn)
        with patch(f"{_MODULE}.asyncio.wait_for", new=AsyncMock(return_value=MagicMock())) as mock_wf:
            await client.new_session()
        _, kwargs = mock_wf.call_args
        assert kwargs.get("timeout") == 15  # noqa: PLR2004

    @pytest.mark.asyncio(loop_scope="function")
    async def test_prompt_uses_300s_timeout(self) -> None:
        """prompt() must pass timeout=300 to asyncio.wait_for."""
        conn = _make_conn()
        client = AcpClient(conn)
        with patch(f"{_MODULE}.asyncio.wait_for", new=AsyncMock(return_value=MagicMock())) as mock_wf:
            await client.prompt(session_id=_SESSION_ID)
        _, kwargs = mock_wf.call_args
        assert kwargs.get("timeout") == 300  # noqa: PLR2004


# ---------------------------------------------------------------------------
# Error classification
# ---------------------------------------------------------------------------


class TestFromAC_ErrorClassification:  # noqa: N801
    """AcpClient catches exceptions and re-raises classified errors with a .category attribute."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_request_error_parse_classified_permanent(self) -> None:
        """RequestError(-32700) parse error → ErrorCategory.PERMANENT."""
        conn = _make_conn()
        conn.initialize.side_effect = RequestError(-32700, "Parse error")
        client = AcpClient(conn)
        with pytest.raises(AcpClientError) as exc_info:
            await client.initialize()
        assert exc_info.value.category == ErrorCategory.PERMANENT

    @pytest.mark.asyncio(loop_scope="function")
    async def test_request_error_method_not_found_classified_permanent(self) -> None:
        """RequestError(-32601) method not found → ErrorCategory.PERMANENT."""
        conn = _make_conn()
        conn.prompt.side_effect = RequestError(-32601, "Method not found")
        client = AcpClient(conn)
        with pytest.raises(AcpClientError) as exc_info:
            await client.prompt(session_id=_SESSION_ID)
        assert exc_info.value.category == ErrorCategory.PERMANENT

    @pytest.mark.asyncio(loop_scope="function")
    async def test_request_error_internal_classified_transient(self) -> None:
        """RequestError(-32603) internal error → ErrorCategory.TRANSIENT."""
        conn = _make_conn()
        conn.prompt.side_effect = RequestError(-32603, "Internal error")
        client = AcpClient(conn)
        with pytest.raises(AcpClientError) as exc_info:
            await client.prompt(session_id=_SESSION_ID)
        assert exc_info.value.category == ErrorCategory.TRANSIENT

    @pytest.mark.asyncio(loop_scope="function")
    async def test_request_error_auth_required_classified_auth(self) -> None:
        """RequestError(-32000) auth required → ErrorCategory.AUTH."""
        conn = _make_conn()
        conn.initialize.side_effect = RequestError(-32000, "Auth required")
        client = AcpClient(conn)
        with pytest.raises(AcpClientError) as exc_info:
            await client.initialize()
        assert exc_info.value.category == ErrorCategory.AUTH

    @pytest.mark.asyncio(loop_scope="function")
    async def test_request_error_resource_not_found_classified_tool_semantic(self) -> None:
        """RequestError(-32002) resource not found → ErrorCategory.TOOL_SEMANTIC."""
        conn = _make_conn()
        conn.new_session.side_effect = RequestError(-32002, "Resource not found")
        client = AcpClient(conn)
        with pytest.raises(AcpClientError) as exc_info:
            await client.new_session()
        assert exc_info.value.category == ErrorCategory.TOOL_SEMANTIC

    @pytest.mark.asyncio(loop_scope="function")
    async def test_broken_pipe_classified_transient(self) -> None:
        """BrokenPipeError on prompt → ErrorCategory.TRANSIENT."""
        conn = _make_conn()
        conn.prompt.side_effect = BrokenPipeError("Connection reset")
        client = AcpClient(conn)
        with pytest.raises(AcpClientError) as exc_info:
            await client.prompt(session_id=_SESSION_ID)
        assert exc_info.value.category == ErrorCategory.TRANSIENT

    @pytest.mark.asyncio(loop_scope="function")
    async def test_eof_connection_error_classified_transient(self) -> None:
        """ConnectionError (EOF on stdout) on prompt → ErrorCategory.TRANSIENT."""
        conn = _make_conn()
        conn.prompt.side_effect = ConnectionError("EOF")
        client = AcpClient(conn)
        with pytest.raises(AcpClientError) as exc_info:
            await client.prompt(session_id=_SESSION_ID)
        assert exc_info.value.category == ErrorCategory.TRANSIENT


# ---------------------------------------------------------------------------
# Cancellation
# ---------------------------------------------------------------------------


class TestFromAC_Cancellation:  # noqa: N801
    """AcpClient sends session/cancel on timeout or when a CancelSignal is already set."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_cancel_sent_on_timeout_error_during_prompt(self) -> None:
        """asyncio.TimeoutError during prompt → conn.cancel(session_id=...) is awaited."""
        conn = _make_conn()
        client = AcpClient(conn)
        with patch(f"{_MODULE}.asyncio.wait_for", side_effect=asyncio.TimeoutError), pytest.raises((asyncio.TimeoutError, AcpClientError)):
            await client.prompt(session_id=_SESSION_ID)
        conn.cancel.assert_awaited_once_with(session_id=_SESSION_ID)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_cancel_sent_when_cancel_signal_already_set(self) -> None:
        """CancelSignal.is_set() == True before prompt → conn.cancel(session_id=...) awaited."""
        conn = _make_conn()
        cancel_signal = MagicMock()
        cancel_signal.is_set.return_value = True
        client = AcpClient(conn, cancel_signal=cancel_signal)
        with contextlib.suppress(asyncio.CancelledError):
            await client.prompt(session_id=_SESSION_ID)
        conn.cancel.assert_awaited_once_with(session_id=_SESSION_ID)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_cancel_not_sent_when_cancel_signal_not_set(self) -> None:
        """CancelSignal.is_set() == False → conn.cancel is never called."""
        conn = _make_conn()
        cancel_signal = MagicMock()
        cancel_signal.is_set.return_value = False
        client = AcpClient(conn, cancel_signal=cancel_signal)
        with patch(f"{_MODULE}.asyncio.wait_for", new=AsyncMock(return_value=MagicMock())):
            await client.prompt(session_id=_SESSION_ID)
        conn.cancel.assert_not_awaited()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_cancel_signal_set_raises_cancelled_error(self) -> None:
        """CancelSignal.is_set() == True → asyncio.CancelledError is raised."""
        conn = _make_conn()
        cancel_signal = MagicMock()
        cancel_signal.is_set.return_value = True
        client = AcpClient(conn, cancel_signal=cancel_signal)
        with pytest.raises(asyncio.CancelledError):
            await client.prompt(session_id=_SESSION_ID)


# ---------------------------------------------------------------------------
# Full 7-code JSON-RPC coverage (AC2 explicit requirement)
# ---------------------------------------------------------------------------


class TestFromAC_AllSevenErrorCodes:  # noqa: N801
    """_ACP_ERROR_CODES must map all 7 JSON-RPC error codes; unknown codes default to PERMANENT."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_request_error_invalid_request_classified_permanent(self) -> None:
        """RequestError(-32600) invalid request → ErrorCategory.PERMANENT."""
        conn = _make_conn()
        conn.prompt.side_effect = RequestError(-32600, "Invalid request")
        client = AcpClient(conn)
        with pytest.raises(AcpClientError) as exc_info:
            await client.prompt(session_id=_SESSION_ID)
        assert exc_info.value.category == ErrorCategory.PERMANENT

    @pytest.mark.asyncio(loop_scope="function")
    async def test_request_error_invalid_params_classified_permanent(self) -> None:
        """RequestError(-32602) invalid params → ErrorCategory.PERMANENT."""
        conn = _make_conn()
        conn.initialize.side_effect = RequestError(-32602, "Invalid params")
        client = AcpClient(conn)
        with pytest.raises(AcpClientError) as exc_info:
            await client.initialize()
        assert exc_info.value.category == ErrorCategory.PERMANENT

    @pytest.mark.asyncio(loop_scope="function")
    async def test_request_error_unknown_code_defaults_to_permanent(self) -> None:
        """RequestError with code not in _ACP_ERROR_CODES → ErrorCategory.PERMANENT (conservative default)."""
        conn = _make_conn()
        conn.new_session.side_effect = RequestError(-99999, "Unknown error")
        client = AcpClient(conn)
        with pytest.raises(AcpClientError) as exc_info:
            await client.new_session()
        assert exc_info.value.category == ErrorCategory.PERMANENT


# ---------------------------------------------------------------------------
# Connection-error classification — all three methods (AC4)
# ---------------------------------------------------------------------------


class TestFromAC_ConnectionErrorsAllMethods:  # noqa: N801
    """BrokenPipeError and ConnectionError must be classified TRANSIENT on every method."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_broken_pipe_on_initialize_classified_transient(self) -> None:
        """BrokenPipeError on initialize → AcpClientError with TRANSIENT category."""
        conn = _make_conn()
        conn.initialize.side_effect = BrokenPipeError("pipe broken")
        client = AcpClient(conn)
        with pytest.raises(AcpClientError) as exc_info:
            await client.initialize()
        assert exc_info.value.category == ErrorCategory.TRANSIENT

    @pytest.mark.asyncio(loop_scope="function")
    async def test_connection_error_on_initialize_classified_transient(self) -> None:
        """ConnectionError (EOF) on initialize → AcpClientError with TRANSIENT category."""
        conn = _make_conn()
        conn.initialize.side_effect = ConnectionError("EOF")
        client = AcpClient(conn)
        with pytest.raises(AcpClientError) as exc_info:
            await client.initialize()
        assert exc_info.value.category == ErrorCategory.TRANSIENT

    @pytest.mark.asyncio(loop_scope="function")
    async def test_broken_pipe_on_new_session_classified_transient(self) -> None:
        """BrokenPipeError on new_session → AcpClientError with TRANSIENT category."""
        conn = _make_conn()
        conn.new_session.side_effect = BrokenPipeError("pipe broken")
        client = AcpClient(conn)
        with pytest.raises(AcpClientError) as exc_info:
            await client.new_session()
        assert exc_info.value.category == ErrorCategory.TRANSIENT

    @pytest.mark.asyncio(loop_scope="function")
    async def test_connection_error_on_new_session_classified_transient(self) -> None:
        """ConnectionError (EOF) on new_session → AcpClientError with TRANSIENT category."""
        conn = _make_conn()
        conn.new_session.side_effect = ConnectionError("EOF")
        client = AcpClient(conn)
        with pytest.raises(AcpClientError) as exc_info:
            await client.new_session()
        assert exc_info.value.category == ErrorCategory.TRANSIENT
