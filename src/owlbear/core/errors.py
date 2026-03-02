"""Error classification for structured recovery.

Provides :class:`ErrorCategory` — a ``StrEnum`` with four retry-policy
categories — and :func:`classify_error`, a pure function that maps any
``Exception`` to an ``ErrorCategory``.

:class:`ToolError` is a frozen dataclass that pairs an ``ErrorCategory``
with the originating tool name and a human-readable message, exposing a
:meth:`~ToolError.to_dict` method for JSON-serializable LLM feedback.

Downstream consumers:
- **Daemon loop** (#360) — decides retry vs. escalate.
- **Tool-level retry** (#359) — wraps transient tool failures.
- **ToolError** (#363) — attaches category to structured error feedback.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal

import httpx
import openai
import pydantic

from owlbear.core.command_guard import BlockedCommandError

# ---------------------------------------------------------------------------
# Error categories
# ---------------------------------------------------------------------------

_TRANSIENT_HTTP_CODES: frozenset[int] = frozenset({429, 502, 503, 504})
_AUTH_HTTP_CODES: frozenset[int] = frozenset({401, 403})


class ErrorCategory(StrEnum):
    """Classifies an exception into a retry-policy bucket.

    Members:
        TRANSIENT: Retry with exponential backoff (network, rate-limit).
        AUTH: Refresh token, retry once (401/403, auth SDK errors).
        PERMANENT: Do not retry — escalate to user (bad input, config).
        TOOL_SEMANTIC: Model self-correction via PydanticAI ``ModelRetry``.
    """

    TRANSIENT = "transient"
    AUTH = "auth"
    PERMANENT = "permanent"
    TOOL_SEMANTIC = "tool_semantic"


# ---------------------------------------------------------------------------
# Classifier
# ---------------------------------------------------------------------------


def _classify_http_status(code: int) -> ErrorCategory:
    """Classify an HTTP status code into an :class:`ErrorCategory`."""
    if code in _TRANSIENT_HTTP_CODES:
        return ErrorCategory.TRANSIENT
    if code in _AUTH_HTTP_CODES:
        return ErrorCategory.AUTH
    return ErrorCategory.PERMANENT


def classify_error(exc: Exception) -> ErrorCategory:
    """Map *exc* to an :class:`ErrorCategory`.

    Pure function — no side effects, no I/O, no logging.  Uses
    ``isinstance`` checks in priority order so that more-specific
    exception subclasses match before their parents.
    """
    # --- HTTP status errors (most specific first) --------------------------
    if isinstance(exc, httpx.HTTPStatusError):
        return _classify_http_status(exc.response.status_code)

    # --- Transient network / timeout errors --------------------------------
    if isinstance(
        exc, (httpx.ConnectError, httpx.TimeoutException, TimeoutError, ConnectionError)
    ):
        return ErrorCategory.TRANSIENT

    # --- Auth SDK errors ---------------------------------------------------
    if isinstance(exc, (openai.AuthenticationError, openai.PermissionDeniedError)):
        return ErrorCategory.AUTH

    # --- Permanent (non-retryable) -----------------------------------------
    # pydantic.ValidationError is a ValueError subclass — check before
    # TOOL_SEMANTIC to avoid misclassification.
    if isinstance(
        exc,
        (pydantic.ValidationError, FileNotFoundError, PermissionError, BlockedCommandError),
    ):
        return ErrorCategory.PERMANENT

    # --- Tool-semantic (model can self-correct) ----------------------------
    if isinstance(exc, (ValueError, KeyError, TypeError)):
        return ErrorCategory.TOOL_SEMANTIC

    # --- Default -----------------------------------------------------------
    return ErrorCategory.PERMANENT


# ---------------------------------------------------------------------------
# Structured error feedback
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ToolError:
    """Structured error returned to the LLM as a JSON-serializable dict.

    All tool/agent error paths should construct a ``ToolError`` and return
    ``json.dumps(error.to_dict())`` so the model receives machine-parseable
    feedback instead of free-form strings.
    """

    error_type: ErrorCategory
    tool_name: str
    message: str
    status: Literal["error"] = "error"

    def to_dict(self) -> dict[str, str]:
        """Return a JSON-serializable dict."""
        return {
            "status": self.status,
            "error_type": self.error_type.value,
            "tool_name": self.tool_name,
            "message": self.message,
        }
