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

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Literal

import httpx
import pydantic

try:
    import openai
except ImportError:  # openai is an optional dependency
    openai = None  # type: ignore[assignment]

from owlbear.core.circuit_breaker import CircuitOpenError
from owlbear.core.exceptions import OwlBearError
from owlbear.tools.browser.safety import BlockedURLError


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


class BudgetExceededError(Exception):
    """Raised when cumulative spend reaches or exceeds the budget limit."""


# ---------------------------------------------------------------------------
# Optional-dependency error tuples
# ---------------------------------------------------------------------------

_openai_auth_errors: tuple[type[Exception], ...] = (
    (openai.AuthenticationError, openai.PermissionDeniedError) if openai is not None else ()
)

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
    if isinstance(exc, (httpx.ConnectError, httpx.TimeoutException, TimeoutError, ConnectionError)):
        return ErrorCategory.TRANSIENT

    # --- Auth SDK errors ---------------------------------------------------
    if _openai_auth_errors and isinstance(exc, _openai_auth_errors):
        return ErrorCategory.AUTH

    # --- Permanent (non-retryable) -----------------------------------------
    # pydantic.ValidationError is a ValueError subclass — check before
    # TOOL_SEMANTIC to avoid misclassification.
    # CircuitOpenError: fast-fail when Copilot API circuit breaker is open.
    if isinstance(
        exc,
        (
            pydantic.ValidationError,
            FileNotFoundError,
            PermissionError,
            BlockedCommandError,
            BlockedURLError,
            CircuitOpenError,
            BudgetExceededError,
        ),
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


# ---------------------------------------------------------------------------
# User-facing error sanitization
# ---------------------------------------------------------------------------

_SAFE_MESSAGES: dict[type[Exception], str] = {
    httpx.ConnectError: "Connection failed",
    httpx.TimeoutException: "Request timed out",
    pydantic.ValidationError: "Validation error",
    FileNotFoundError: "File not found",
    PermissionError: "Permission denied",
}
if openai is not None:
    _SAFE_MESSAGES[openai.AuthenticationError] = "Authentication failed"
    _SAFE_MESSAGES[openai.PermissionDeniedError] = "Permission denied"

_SCRUB_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"Bearer\s+\S+"), "[REDACTED]"),
    (re.compile(r"(?i)(token|key|secret|password)=[^\s&]+"), r"\1=[REDACTED]"),
    (re.compile(r"https?://\S+"), "[URL]"),
    (re.compile(r"[A-Za-z]:\\[^\s]+"), "[PATH]"),
    (re.compile(r"/(?:[^\s/]+/)+[^\s/]+"), "[PATH]"),
]


def error_to_user_message(exc: Exception) -> str:
    """Return a safe, user-facing error description.

    Pure function — no I/O, no logging, no side effects.  Uses a type-based
    mapping for known exception types, with a regex-scrubbed fallback for
    everything else.
    """
    # HTTPStatusError needs dynamic formatting (status code).
    if isinstance(exc, httpx.HTTPStatusError):
        return f"HTTP request failed (status {exc.response.status_code})"

    # Check static safe-message mapping.
    for exc_type, safe_msg in _SAFE_MESSAGES.items():
        if isinstance(exc, exc_type):
            return safe_msg

    # Fallback: scrub sensitive patterns from the original message.
    msg = str(exc)
    for pattern, replacement in _SCRUB_PATTERNS:
        msg = pattern.sub(replacement, msg)

    return f"{type(exc).__name__}: {msg}"
