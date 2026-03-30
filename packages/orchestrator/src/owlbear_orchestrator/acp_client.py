"""AcpClient — thin wrapper around ClientSideConnection with timeouts and error classification."""

from __future__ import annotations

import asyncio
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Protocol

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


_ACP_ERROR_CODES: dict[int, ErrorCategory] = {
    -32700: ErrorCategory.PERMANENT,   # Parse error
    -32600: ErrorCategory.PERMANENT,   # Invalid request
    -32601: ErrorCategory.PERMANENT,   # Method not found
    -32602: ErrorCategory.PERMANENT,   # Invalid params
    -32603: ErrorCategory.TRANSIENT,   # Internal error
    -32000: ErrorCategory.AUTH,        # Auth required
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
    """

    def __init__(
        self,
        conn: ClientSideConnection,
        *,
        cancel_signal: _CancelSignal | None = None,
    ) -> None:
        self._conn = conn
        self._cancel_signal = cancel_signal

    async def initialize(self, **kwargs: Any) -> InitializeResponse:  # noqa: ANN401
        """Call conn.initialize() with a 30 s timeout, forwarding all kwargs to the SDK."""
        try:
            return await asyncio.wait_for(self._conn.initialize(**kwargs), timeout=30)
        except RequestError as exc:
            raise AcpClientError(str(exc), category=_classify_request_error(exc)) from exc
        except (BrokenPipeError, ConnectionError) as exc:
            raise AcpClientError(str(exc), category=ErrorCategory.TRANSIENT) from exc

    async def new_session(self, **kwargs: Any) -> NewSessionResponse:  # noqa: ANN401
        """Call conn.new_session() with a 15 s timeout, forwarding all kwargs to the SDK."""
        try:
            return await asyncio.wait_for(self._conn.new_session(**kwargs), timeout=15)
        except RequestError as exc:
            raise AcpClientError(str(exc), category=_classify_request_error(exc)) from exc
        except (BrokenPipeError, ConnectionError) as exc:
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
            raise AcpClientError(str(exc), category=_classify_request_error(exc)) from exc
        except (BrokenPipeError, ConnectionError) as exc:
            raise AcpClientError(str(exc), category=ErrorCategory.TRANSIENT) from exc
