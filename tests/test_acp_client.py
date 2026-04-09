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
import inspect
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from acp.client.connection import ClientSideConnection
from acp.exceptions import RequestError
from acp.schema import TextContentBlock
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
            await client.initialize(protocol_version=1)
        _, kwargs = mock_wf.call_args
        assert kwargs.get("timeout") == 30  # noqa: PLR2004

    @pytest.mark.asyncio(loop_scope="function")
    async def test_new_session_uses_15s_timeout(self) -> None:
        """new_session() must pass timeout=15 to asyncio.wait_for."""
        conn = _make_conn()
        client = AcpClient(conn)
        with patch(f"{_MODULE}.asyncio.wait_for", new=AsyncMock(return_value=MagicMock())) as mock_wf:
            await client.new_session(cwd="/work")
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
            await client.initialize(protocol_version=1)
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
            await client.initialize(protocol_version=1)
        assert exc_info.value.category == ErrorCategory.AUTH

    @pytest.mark.asyncio(loop_scope="function")
    async def test_request_error_resource_not_found_classified_tool_semantic(self) -> None:
        """RequestError(-32002) resource not found → ErrorCategory.TOOL_SEMANTIC."""
        conn = _make_conn()
        conn.new_session.side_effect = RequestError(-32002, "Resource not found")
        client = AcpClient(conn)
        with pytest.raises(AcpClientError) as exc_info:
            await client.new_session(cwd="/work")
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
        with (
            patch(f"{_MODULE}.asyncio.wait_for", side_effect=asyncio.TimeoutError),
            pytest.raises((asyncio.TimeoutError, AcpClientError)),
        ):
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
            await client.initialize(protocol_version=1)
        assert exc_info.value.category == ErrorCategory.PERMANENT

    @pytest.mark.asyncio(loop_scope="function")
    async def test_request_error_unknown_code_defaults_to_permanent(self) -> None:
        """RequestError with code not in _ACP_ERROR_CODES → ErrorCategory.PERMANENT (conservative default)."""
        conn = _make_conn()
        conn.new_session.side_effect = RequestError(-99999, "Unknown error")
        client = AcpClient(conn)
        with pytest.raises(AcpClientError) as exc_info:
            await client.new_session(cwd="/work")
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
            await client.initialize(protocol_version=1)
        assert exc_info.value.category == ErrorCategory.TRANSIENT

    @pytest.mark.asyncio(loop_scope="function")
    async def test_connection_error_on_initialize_classified_transient(self) -> None:
        """ConnectionError (EOF) on initialize → AcpClientError with TRANSIENT category."""
        conn = _make_conn()
        conn.initialize.side_effect = ConnectionError("EOF")
        client = AcpClient(conn)
        with pytest.raises(AcpClientError) as exc_info:
            await client.initialize(protocol_version=1)
        assert exc_info.value.category == ErrorCategory.TRANSIENT

    @pytest.mark.asyncio(loop_scope="function")
    async def test_broken_pipe_on_new_session_classified_transient(self) -> None:
        """BrokenPipeError on new_session → AcpClientError with TRANSIENT category."""
        conn = _make_conn()
        conn.new_session.side_effect = BrokenPipeError("pipe broken")
        client = AcpClient(conn)
        with pytest.raises(AcpClientError) as exc_info:
            await client.new_session(cwd="/work")
        assert exc_info.value.category == ErrorCategory.TRANSIENT

    @pytest.mark.asyncio(loop_scope="function")
    async def test_connection_error_on_new_session_classified_transient(self) -> None:
        """ConnectionError (EOF) on new_session → AcpClientError with TRANSIENT category."""
        conn = _make_conn()
        conn.new_session.side_effect = ConnectionError("EOF")
        client = AcpClient(conn)
        with pytest.raises(AcpClientError) as exc_info:
            await client.new_session(cwd="/work")
        assert exc_info.value.category == ErrorCategory.TRANSIENT


# ---------------------------------------------------------------------------
# SDK parameter forwarding (retry-cycle additions — reviewer Finding 2)
# AC: each AcpClient method wraps conn.<method>() — it must forward all required
# SDK parameters, not silently drop them.
# ---------------------------------------------------------------------------


class TestFromAC_SDKParameterForwarding:  # noqa: N801
    """AcpClient must accept and forward required SDK parameters to the underlying conn methods.

    Tests call through to actual mock connection methods — asyncio.wait_for is NOT patched,
    so the AsyncMock conn methods receive real awaits with the forwarded arguments.
    """

    @pytest.mark.asyncio(loop_scope="function")
    async def test_initialize_forwards_protocol_version(self) -> None:
        """initialize(protocol_version=1) must forward protocol_version to conn.initialize().

        SDK signature: initialize(self, protocol_version: int, ...) — required positional.
        Current acp_client.py calls conn.initialize() with no args — TypeError at runtime.
        """
        conn = _make_conn()
        client = AcpClient(conn)
        await client.initialize(protocol_version=1)
        conn.initialize.assert_called_once_with(protocol_version=1)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_new_session_forwards_cwd(self) -> None:
        """new_session(cwd='/tmp') must forward cwd to conn.new_session().

        SDK signature: new_session(self, cwd: str, ...) — required positional.
        Current acp_client.py calls conn.new_session() with no args — TypeError at runtime.
        """
        conn = _make_conn()
        client = AcpClient(conn)
        await client.new_session(cwd="/work/cwd")
        conn.new_session.assert_called_once_with(cwd="/work/cwd")

    @pytest.mark.asyncio(loop_scope="function")
    async def test_prompt_forwards_prompt_content(self) -> None:
        """prompt(session_id=..., prompt=[...]) must forward prompt content to conn.prompt().

        SDK signature: prompt(self, prompt: list[...], session_id: str, ...) — prompt is required.
        Current acp_client.py calls conn.prompt(session_id=...) only — drops prompt content.
        """
        conn = _make_conn()
        client = AcpClient(conn)
        fake_content = [MagicMock()]
        with patch(f"{_MODULE}.asyncio.wait_for", new=AsyncMock(return_value=MagicMock())):
            await client.prompt(session_id=_SESSION_ID, prompt=fake_content)
        call_kwargs = conn.prompt.call_args[1]
        assert call_kwargs.get("prompt") == fake_content
        assert call_kwargs.get("session_id") == _SESSION_ID


# ---------------------------------------------------------------------------
# Builder-discovered tests: additional SDK parameter coverage
# ---------------------------------------------------------------------------


class TestBuilderDiscovered_SDKForwarding:  # noqa: N801
    """Additional SDK parameter forwarding tests discovered by the builder during GREEN phase."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_prompt_forwards_content_blocks(self) -> None:
        """prompt(prompt=[TextContentBlock(...)], session_id='s1') forwards both args to conn.prompt()."""
        conn = _make_conn()
        client = AcpClient(conn)
        content = [TextContentBlock(text="hello", type="text")]
        await client.prompt(prompt=content, session_id="s1")
        call_kwargs = conn.prompt.call_args.kwargs
        assert call_kwargs.get("prompt") == content
        assert call_kwargs.get("session_id") == "s1"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_new_session_forwards_mcp_servers(self) -> None:
        """new_session(cwd='/tmp', mcp_servers=[...]) must forward mcp_servers to conn.new_session()."""
        conn = _make_conn()
        client = AcpClient(conn)
        mcp_servers = [{"name": "test-server", "command": "npx test"}]
        await client.new_session(cwd="/work/cwd", mcp_servers=mcp_servers)
        conn.new_session.assert_called_once_with(cwd="/work/cwd", mcp_servers=mcp_servers)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_prompt_forwards_optional_message_id(self) -> None:
        """prompt(..., message_id='m1') must forward message_id to conn.prompt()."""
        conn = _make_conn()
        client = AcpClient(conn)
        content = [TextContentBlock(text="hi", type="text")]
        await client.prompt(prompt=content, session_id="s1", message_id="m1")
        call_kwargs = conn.prompt.call_args.kwargs
        assert call_kwargs.get("message_id") == "m1"


# ---------------------------------------------------------------------------
# Explicit signature enforcement (retry-cycle — reviewer Finding: LAX tests)
# Architecture Review: "no *args/**kwargs pass-through. Keeps the wrapper typed
# and inspectable." AC requires initialize(protocol_version: int) and
# new_session(cwd: str, mcp_servers: list | None = None) — not **kwargs.
# ---------------------------------------------------------------------------


class TestFromAC_ExplicitSignatureEnforcement:  # noqa: N801
    """AcpClient wrapper methods must declare required SDK params explicitly — no **kwargs.

    Per Architecture Review: "Interface: wrapper mirrors SDK required params explicitly
    (no *args/**kwargs pass-through). Keeps the wrapper typed and inspectable."
    Prior TestFromAC_SDKParameterForwarding tests were LAX — they verified forwarding
    but did not enforce that required params are explicit in the signature.
    """

    # --- initialize() ---

    def test_initialize_signature_has_protocol_version(self) -> None:
        """initialize() must declare 'protocol_version' as an explicit named parameter.

        With **kwargs AcpClient.initialize absorbs any name — this test enforces the
        AC-required explicit signature: initialize(protocol_version: int).
        """
        params = inspect.signature(AcpClient.initialize).parameters
        assert "protocol_version" in params, (
            "initialize() must declare 'protocol_version' explicitly, not absorb via **kwargs"
        )

    def test_initialize_signature_no_var_keyword(self) -> None:
        """initialize() must not have a **kwargs absorbing parameter.

        Architecture Review: no **kwargs pass-through — keep the wrapper typed.
        """
        params = inspect.signature(AcpClient.initialize).parameters
        var_kw = [name for name, p in params.items() if p.kind == inspect.Parameter.VAR_KEYWORD]
        assert var_kw == [], f"initialize() has **{var_kw} — Architecture Review requires explicit params, no **kwargs"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_initialize_requires_protocol_version_at_runtime(self) -> None:
        """Calling initialize() without protocol_version must raise TypeError.

        With **kwargs this silently succeeds — the test enforces that the param is
        a required, explicitly typed argument matching the SDK function signature.
        """
        conn = _make_conn()
        client = AcpClient(conn)
        with pytest.raises(TypeError):
            await client.initialize()

    # --- new_session() ---

    def test_new_session_signature_has_cwd(self) -> None:
        """new_session() must declare 'cwd' as an explicit named parameter."""
        params = inspect.signature(AcpClient.new_session).parameters
        assert "cwd" in params, "new_session() must declare 'cwd' explicitly, not absorb via **kwargs"

    def test_new_session_signature_cwd_is_required(self) -> None:
        """new_session() 'cwd' must be required — no default value.

        AC: new_session(cwd: str, ...) — cwd is a required positional-or-keyword arg.
        """
        params = inspect.signature(AcpClient.new_session).parameters
        cwd_param = params.get("cwd")
        assert cwd_param is not None, "new_session() must have an explicit 'cwd' parameter"
        assert cwd_param.default is inspect.Parameter.empty, (
            "new_session() 'cwd' must be required with no default, matching SDK signature"
        )

    def test_new_session_signature_has_mcp_servers_defaulting_to_none(self) -> None:
        """new_session() must declare 'mcp_servers' with a default of None.

        AC: new_session(cwd: str, mcp_servers: list or None = None)
        """
        params = inspect.signature(AcpClient.new_session).parameters
        mcp_param = params.get("mcp_servers")
        assert mcp_param is not None, "new_session() must declare 'mcp_servers' explicitly (not via **kwargs)"
        assert mcp_param.default is None, "new_session() 'mcp_servers' must default to None per AC"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_new_session_requires_cwd_at_runtime(self) -> None:
        """Calling new_session() without cwd must raise TypeError.

        With **kwargs this silently succeeds — the test enforces that cwd is a
        required, explicitly typed argument matching the SDK function signature.
        """
        conn = _make_conn()
        client = AcpClient(conn)
        with pytest.raises(TypeError):
            await client.new_session()


# ---------------------------------------------------------------------------
# ErrorLogger Protocol wiring (#521)
# AcpClient must accept an optional _ErrorLogger and call log_error on
# classified exceptions with keyword args: category, method, message.
# ---------------------------------------------------------------------------


class TestFromAC_ErrorLoggerWiring:  # noqa: N801
    """AcpClient must accept an optional _ErrorLogger and call log_error on classified exceptions."""

    # --- AC: initialize + RequestError ---

    @pytest.mark.asyncio(loop_scope="function")
    async def test_initialize_request_error_calls_log_error_with_category_method_message(self) -> None:
        """log_error called with correct category/method/message when initialize raises RequestError."""
        conn = _make_conn()
        conn.initialize.side_effect = RequestError(-32700, "Parse error")
        error_logger = MagicMock()
        client = AcpClient(conn, error_logger=error_logger)
        with pytest.raises(AcpClientError):
            await client.initialize(protocol_version=1)
        error_logger.log_error.assert_called_once()
        call_kwargs = error_logger.log_error.call_args.kwargs
        assert call_kwargs["category"] == ErrorCategory.PERMANENT
        assert call_kwargs["method"] == "initialize"
        assert "Parse error" in call_kwargs["message"]

    # --- AC: initialize + BrokenPipeError ---

    @pytest.mark.asyncio(loop_scope="function")
    async def test_initialize_broken_pipe_calls_log_error_category_transient(self) -> None:
        """log_error called with category=transient, method=initialize when initialize raises BrokenPipeError."""
        conn = _make_conn()
        conn.initialize.side_effect = BrokenPipeError("pipe broken")
        error_logger = MagicMock()
        client = AcpClient(conn, error_logger=error_logger)
        with pytest.raises(AcpClientError):
            await client.initialize(protocol_version=1)
        error_logger.log_error.assert_called_once()
        call_kwargs = error_logger.log_error.call_args.kwargs
        assert call_kwargs["category"] == ErrorCategory.TRANSIENT
        assert call_kwargs["method"] == "initialize"

    # --- AC: new_session + RequestError ---

    @pytest.mark.asyncio(loop_scope="function")
    async def test_new_session_request_error_calls_log_error_with_correct_args(self) -> None:
        """log_error called with correct category/method/message when new_session raises RequestError."""
        conn = _make_conn()
        conn.new_session.side_effect = RequestError(-32603, "Internal error")
        error_logger = MagicMock()
        client = AcpClient(conn, error_logger=error_logger)
        with pytest.raises(AcpClientError):
            await client.new_session(cwd="/work")
        error_logger.log_error.assert_called_once()
        call_kwargs = error_logger.log_error.call_args.kwargs
        assert call_kwargs["category"] == ErrorCategory.TRANSIENT
        assert call_kwargs["method"] == "new_session"
        assert "Internal error" in call_kwargs["message"]

    # --- AC: new_session + ConnectionError ---

    @pytest.mark.asyncio(loop_scope="function")
    async def test_new_session_connection_error_calls_log_error_category_transient(self) -> None:
        """log_error called with category=transient, method=new_session when new_session raises ConnectionError."""
        conn = _make_conn()
        conn.new_session.side_effect = ConnectionError("EOF on stdout")
        error_logger = MagicMock()
        client = AcpClient(conn, error_logger=error_logger)
        with pytest.raises(AcpClientError):
            await client.new_session(cwd="/work")
        error_logger.log_error.assert_called_once()
        call_kwargs = error_logger.log_error.call_args.kwargs
        assert call_kwargs["category"] == ErrorCategory.TRANSIENT
        assert call_kwargs["method"] == "new_session"

    # --- AC: prompt + RequestError ---

    @pytest.mark.asyncio(loop_scope="function")
    async def test_prompt_request_error_calls_log_error_with_correct_args(self) -> None:
        """log_error called with correct category/method/message when prompt raises RequestError."""
        conn = _make_conn()
        conn.prompt.side_effect = RequestError(-32601, "Method not found")
        error_logger = MagicMock()
        client = AcpClient(conn, error_logger=error_logger)
        with pytest.raises(AcpClientError):
            await client.prompt(session_id=_SESSION_ID)
        error_logger.log_error.assert_called_once()
        call_kwargs = error_logger.log_error.call_args.kwargs
        assert call_kwargs["category"] == ErrorCategory.PERMANENT
        assert call_kwargs["method"] == "prompt"
        assert "Method not found" in call_kwargs["message"]

    # --- AC: prompt + BrokenPipeError ---

    @pytest.mark.asyncio(loop_scope="function")
    async def test_prompt_broken_pipe_calls_log_error_category_transient(self) -> None:
        """log_error called with category=transient, method=prompt when prompt raises BrokenPipeError."""
        conn = _make_conn()
        conn.prompt.side_effect = BrokenPipeError("connection reset")
        error_logger = MagicMock()
        client = AcpClient(conn, error_logger=error_logger)
        with pytest.raises(AcpClientError):
            await client.prompt(session_id=_SESSION_ID)
        error_logger.log_error.assert_called_once()
        call_kwargs = error_logger.log_error.call_args.kwargs
        assert call_kwargs["category"] == ErrorCategory.TRANSIENT
        assert call_kwargs["method"] == "prompt"

    # --- AC: error_logger is None (default behavior) ---

    @pytest.mark.asyncio(loop_scope="function")
    async def test_no_log_error_when_error_logger_is_none(self) -> None:
        """log_error NOT called when error_logger is None — AcpClientError raised without AttributeError."""
        conn = _make_conn()
        conn.initialize.side_effect = RequestError(-32700, "Parse error")
        # Explicitly pass None — must not raise AttributeError on None.log_error
        client = AcpClient(conn, error_logger=None)
        with pytest.raises(AcpClientError):
            await client.initialize(protocol_version=1)

    # --- AC: TimeoutError does NOT call log_error ---

    @pytest.mark.asyncio(loop_scope="function")
    async def test_timeout_error_in_prompt_does_not_call_log_error(self) -> None:
        """TimeoutError in prompt() does NOT call log_error (excluded by design)."""
        conn = _make_conn()
        error_logger = MagicMock()
        client = AcpClient(conn, error_logger=error_logger)
        with (
            patch(f"{_MODULE}.asyncio.wait_for", side_effect=asyncio.TimeoutError),
            pytest.raises((asyncio.TimeoutError, AcpClientError)),
        ):
            await client.prompt(session_id=_SESSION_ID)
        error_logger.log_error.assert_not_called()
