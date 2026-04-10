"""AcpClient — thin wrapper around ClientSideConnection with timeouts and error classification."""

from __future__ import annotations

import asyncio
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Protocol, Self

from acp.exceptions import RequestError

if TYPE_CHECKING:
    from acp.client.connection import ClientSideConnection
    from acp.schema import ContentBlock, InitializeResponse, NewSessionResponse, PromptResponse


class ErrorCategory(StrEnum):
    """Classifies an ACP exception into a retry-policy bucket.

    Members:
        TRANSIENT: Retry with exponential backoff (network errors, internal errors).
        AUTH: Refresh token, retry once (auth SDK errors).
        PERMANENT: Do not retry — escalate to user (bad input, protocol errors).
        TOOL_SEMANTIC: Model self-correction via retry (resource not found, semantic errors).
    """

    TRANSIENT = "transient"
    AUTH = "auth"
    PERMANENT = "permanent"
    TOOL_SEMANTIC = "tool_semantic"


class _CancelSignal(Protocol):
    """Duck-type protocol for cancellation signal objects."""

    def is_set(self) -> bool:
        """Return True if the cancel signal has been set."""
        ...


class _ErrorLogger(Protocol):
    """Duck-type protocol for error-logging objects."""

    def log_error(self, *, category: ErrorCategory, method: str, message: str) -> None:
        """Record a classified ACP error."""
        ...


_ACP_ERROR_CODES: dict[int, ErrorCategory] = {
    -32700: ErrorCategory.PERMANENT,  # Parse error
    -32600: ErrorCategory.PERMANENT,  # Invalid request
    -32601: ErrorCategory.PERMANENT,  # Method not found
    -32602: ErrorCategory.PERMANENT,  # Invalid params
    -32603: ErrorCategory.TRANSIENT,  # Internal error
    -32000: ErrorCategory.AUTH,  # Auth required
    -32002: ErrorCategory.TOOL_SEMANTIC,  # Resource not found
}


class AcpClientError(Exception):
    """Raised by AcpClient for classified, recoverable errors.

    Attributes:
        category: The retry-policy category for the error.
    """

    def __init__(self, message: str, *, category: ErrorCategory) -> None:
        super().__init__(message)
        self.category = category


def _classify_request_error(exc: RequestError) -> ErrorCategory:
    """Map a RequestError to an ErrorCategory by JSON-RPC error code."""
    return _ACP_ERROR_CODES.get(exc.code, ErrorCategory.PERMANENT)


class AcpClient:
    """Wrap ClientSideConnection with per-method timeouts and structured error classification.

    Args:
        conn: The ACP connection to wrap.
        cancel_signal: Optional signal object; if ``is_set()`` returns True before a
            prompt call, session/cancel is sent and the call is aborted.
        error_logger: Optional object satisfying the ``_ErrorLogger`` protocol; if provided,
            ``log_error`` is called with the classified ``ErrorCategory``, method name, and
            error message whenever ``initialize``, ``new_session``, or ``prompt`` raises a
            ``RequestError``, ``BrokenPipeError``, or ``ConnectionError``.
    """

    def __init__(
        self,
        conn: ClientSideConnection,
        *,
        cancel_signal: _CancelSignal | None = None,
        error_logger: _ErrorLogger | None = None,
    ) -> None:
        self._conn = conn
        self._cancel_signal = cancel_signal
        self._error_logger = error_logger

    async def __aenter__(self) -> Self:
        """Enter the async context manager; returns self."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Exit the async context manager; performs no cleanup."""

    async def initialize(self, protocol_version: int) -> InitializeResponse:
        """Call conn.initialize() with a 30 s timeout, forwarding protocol_version to the SDK."""
        try:
            return await asyncio.wait_for(self._conn.initialize(protocol_version=protocol_version), timeout=30)
        except RequestError as exc:
            category = _classify_request_error(exc)
            if self._error_logger is not None:
                self._error_logger.log_error(category=category, method="initialize", message=str(exc))
            raise AcpClientError(str(exc), category=category) from exc
        except (BrokenPipeError, ConnectionError) as exc:
            if self._error_logger is not None:
                self._error_logger.log_error(category=ErrorCategory.TRANSIENT, method="initialize", message=str(exc))
            raise AcpClientError(str(exc), category=ErrorCategory.TRANSIENT) from exc

    async def new_session(self, cwd: str, mcp_servers: list | None = None) -> NewSessionResponse:
        """Call conn.new_session() with a 15 s timeout, forwarding cwd and mcp_servers."""
        call_kwargs: dict[str, Any] = {"cwd": cwd}
        if mcp_servers is not None:
            call_kwargs["mcp_servers"] = mcp_servers
        try:
            return await asyncio.wait_for(self._conn.new_session(**call_kwargs), timeout=15)
        except RequestError as exc:
            category = _classify_request_error(exc)
            if self._error_logger is not None:
                self._error_logger.log_error(category=category, method="new_session", message=str(exc))
            raise AcpClientError(str(exc), category=category) from exc
        except (BrokenPipeError, ConnectionError) as exc:
            if self._error_logger is not None:
                self._error_logger.log_error(category=ErrorCategory.TRANSIENT, method="new_session", message=str(exc))
            raise AcpClientError(str(exc), category=ErrorCategory.TRANSIENT) from exc

    async def prompt(
        self,
        session_id: str,
        prompt: list[ContentBlock] | None = None,
        **kwargs: Any,  # noqa: ANN401
    ) -> PromptResponse:
        """Call conn.prompt() with a 300 s timeout, handling CancelSignal and TimeoutError."""
        if self._cancel_signal is not None and self._cancel_signal.is_set():
            await self._conn.cancel(session_id=session_id)
            raise asyncio.CancelledError
        call_kwargs: dict[str, Any] = {"session_id": session_id, **kwargs}
        if prompt is not None:
            call_kwargs["prompt"] = prompt
        try:
            return await asyncio.wait_for(
                self._conn.prompt(**call_kwargs),
                timeout=300,
            )
        except TimeoutError:
            await self._conn.cancel(session_id=session_id)
            raise
        except RequestError as exc:
            category = _classify_request_error(exc)
            if self._error_logger is not None:
                self._error_logger.log_error(category=category, method="prompt", message=str(exc))
            raise AcpClientError(str(exc), category=category) from exc
        except (BrokenPipeError, ConnectionError) as exc:
            if self._error_logger is not None:
                self._error_logger.log_error(category=ErrorCategory.TRANSIENT, method="prompt", message=str(exc))
            raise AcpClientError(str(exc), category=ErrorCategory.TRANSIENT) from exc
