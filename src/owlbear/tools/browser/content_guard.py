"""Content injection guard for browser-extracted text.

Provides :class:`ContentInjectionGuard` — scans page text for prompt-injection
patterns and returns a :class:`CheckResult` indicating whether a threat was
detected and whether the content is blocked.

Three modes:

* ``strict`` — detected injections are both flagged **and** blocked.
* ``warn`` — detected injections are flagged but **not** blocked (log only).
* ``off`` — scanning disabled; always returns clean.
"""

from __future__ import annotations

import logging
import re
from typing import Literal

from pydantic import BaseModel

__all__ = [
    "DEFAULT_INJECTION_PATTERNS",
    "CheckResult",
    "ContentInjectionError",
    "ContentInjectionGuard",
]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default injection patterns (~40 regexes, case-insensitive at scan time)
# ---------------------------------------------------------------------------

DEFAULT_INJECTION_PATTERNS: list[str] = [
    # Direct instruction override
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"disregard\s+(all\s+)?(prior|previous|above)\s+instructions",
    r"forget\s+(all\s+)?(prior|previous|above)\s+instructions",
    r"override\s+(your\s+)?system\s+prompt",
    r"bypass\s+(your\s+)?(safety|security|content)\s+(filter|guard|check)",
    # Role hijacking
    r"you\s+are\s+now\s+a\b",
    r"pretend\s+you\s+are\b",
    r"act\s+as\s+(if\s+you\s+are|a)\b",
    r"switch\s+to\s+.{0,30}\s+mode",
    r"enter\s+(developer|god|admin|root|sudo)\s+mode",
    # Command execution
    r"execute\s+the\s+following\s+command",
    r"run\s+the\s+following\s+(command|script|code)",
    r"eval\s*\(",
    r"exec\s*\(",
    r"import\s+os\s*[;.]",
    r"subprocess\.\w+\(",
    # Data exfiltration
    r"\bexfiltrate\b",
    r"send\s+(the\s+)?(data|info|information|content|response)\s+to\b",
    r"post\s+(the\s+)?(data|info|information|content|response)\s+to\b",
    r"forward\s+(all|the)\s+.{0,30}\s+to\b",
    r"leak\s+(the\s+)?(data|secret|key|token|password)",
    # System prompt extraction
    r"what\s+is\s+your\s+system\s+prompt",
    r"show\s+(me\s+)?your\s+(system\s+)?prompt",
    r"reveal\s+your\s+(system\s+)?prompt",
    r"print\s+your\s+(system\s+)?prompt",
    r"output\s+your\s+(system\s+)?(prompt|instructions)",
    r"repeat\s+(your\s+)?(system\s+)?(prompt|instructions)\s+verbatim",
    r"\bDAN\b.*\bjailbreak\b",
    r"jailbreak\b.*\bDAN\b",
    r"do\s+anything\s+now",
    # Encoding / obfuscation evasion markers
    r"base64\s+decode\s+the\s+following",
    r"decode\s+this\s+base64",
    r"rot13\s+decode",
    # Markdown / HTML injection
    r"<script\b[^>]*>",
    r"javascript\s*:",
    r"on(error|load|click)\s*=",
    # Prompt delimiter manipulation
    r"\[SYSTEM\]\s*:",
    r"\[INST\]",
    r"<<\s*SYS\s*>>",
    r"```system",
    # Misc dangerous phrases
    r"ignore\s+safety\s+(guidelines|rules|restrictions)",
    r"there\s+are\s+no\s+(ethical|safety)\s+(guidelines|rules|restrictions)",
]


# ---------------------------------------------------------------------------
# CheckResult model
# ---------------------------------------------------------------------------


class CheckResult(BaseModel, frozen=True):
    """Result of a content injection scan.

    Attributes:
        threat: ``True`` if an injection pattern was detected.
        blocked: ``True`` if the content should be blocked.
        reason: Human-readable explanation.
        pattern: The regex pattern that matched, or ``None`` for clean content.
    """

    threat: bool
    blocked: bool
    reason: str
    pattern: str | None


# ---------------------------------------------------------------------------
# ContentInjectionError
# ---------------------------------------------------------------------------


class ContentInjectionError(Exception):
    """Raised when content injection is detected in strict mode.

    Attributes:
        text: The scanned text that triggered the guard.
        pattern: The regex pattern that matched.
        reason: Human-readable explanation.
    """

    def __init__(self, text: str, pattern: str, reason: str) -> None:
        self.text = text
        self.pattern = pattern
        self.reason = reason
        super().__init__(reason)


# ---------------------------------------------------------------------------
# ContentInjectionGuard
# ---------------------------------------------------------------------------


class ContentInjectionGuard:
    """Scans text for prompt-injection patterns.

    Args:
        mode: Operating mode — ``'strict'``, ``'warn'``, or ``'off'``.
        patterns: Custom regex patterns. When provided, replaces
            :data:`DEFAULT_INJECTION_PATTERNS` entirely.
    """

    def __init__(
        self,
        mode: Literal["strict", "warn", "off"] = "strict",
        patterns: list[str] | None = None,
    ) -> None:
        self._mode = mode
        self._patterns = patterns if patterns is not None else DEFAULT_INJECTION_PATTERNS

    def scan(self, text: str) -> CheckResult:
        """Scan *text* for injection patterns.

        Returns:
            A :class:`CheckResult` with threat/blocked status and reason.
        """
        if self._mode == "off":
            return CheckResult(
                threat=False,
                blocked=False,
                reason="scanning disabled",
                pattern=None,
            )

        for pattern in self._patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return self._on_match(text, pattern)

        return CheckResult(
            threat=False,
            blocked=False,
            reason="clean",
            pattern=None,
        )

    def _on_match(self, _text: str, pattern: str) -> CheckResult:
        """Handle a pattern match according to the current mode."""
        reason = f"Prompt injection detected (pattern: {pattern!r})"

        if self._mode == "strict":
            return CheckResult(
                threat=True,
                blocked=True,
                reason=reason,
                pattern=pattern,
            )

        # warn mode
        logger.warning("Content injection detected: %s", reason)
        return CheckResult(
            threat=True,
            blocked=False,
            reason=reason,
            pattern=pattern,
        )
