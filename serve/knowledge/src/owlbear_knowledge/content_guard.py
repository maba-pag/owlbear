"""Content injection guard for IDPI (Indirect Prompt Injection) detection.

Scans text for known prompt-injection phrases before entity extraction.
This is a defense-in-depth measure (OWASP LLM01:2025 Strategy #3) using
case-insensitive substring matching against ~40 builtin patterns across 7
IDPI categories.  It does NOT guarantee detection of novel or obfuscated
attacks — it is one layer in a broader security strategy.
"""

from __future__ import annotations

import dataclasses
import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# ~40 builtin injection patterns across 7 IDPI categories (AC3)
# Case-insensitive substring matching — phrases are stored in lowercase.
# ---------------------------------------------------------------------------

_BUILTIN_PATTERNS: tuple[str, ...] = (
    # instruction override — 9 patterns
    "ignore previous instructions",
    "disregard your instructions",
    "disregard prior instructions",
    "disregard all prior",
    "forget your instructions",
    "override your instructions",
    "ignore the above",
    "do not follow your",
    "new instructions:",
    # role hijack — 7 patterns
    "you are now",
    "pretend you are",
    "from now on you are",
    "act as if",
    "your new identity",
    "roleplay as",
    "simulate being",
    # jailbreak — 7 patterns
    "jailbreak",
    "developer mode",
    "dan mode",
    "do anything now",
    "bypass safety",
    "bypass the filter",
    "unrestricted mode",
    # exfiltration — 6 patterns
    "send the data to",
    "exfiltrate",
    "leak the data",
    "send credentials to",
    "upload to http",
    "forward to http",
    # Indirect command (5)
    "your new task is",
    "follow these new rules",
    "execute the following command",
    "your real instructions are",
    "priority override",
    # Social engineering (4)
    "new instructions from the admin",
    "authorized by the system",
    "system update:",
    "security alert:",
    # System prompt extraction (3)
    "repeat your instructions",
    "what is your system prompt",
    "reveal your instructions",
)


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class CheckResult:
    """Result of a single content injection scan.

    Attributes:
        threat: True if an injection phrase was detected.
        blocked: True when threat is True **and** the guard is in strict mode.
        reason: Human-readable description of the match, or empty string.
        pattern: The matched pattern substring, or empty string on clean scan.
    """

    threat: bool
    blocked: bool
    reason: str
    pattern: str


# ---------------------------------------------------------------------------
# Guard
# ---------------------------------------------------------------------------


class ContentInjectionGuard:
    """Scans text for indirect prompt injection phrases.

    Args:
        custom_patterns: Additional substrings to match alongside builtins.
            Extends — does not replace — the builtin pattern list.
        strict_mode: When True (default), ``CheckResult.blocked`` is set to
            True on any detected threat.  When False (warn mode), the guard
            reports the threat but sets ``blocked=False`` so the caller can
            choose to log and proceed.
    """

    def __init__(
        self,
        custom_patterns: list[str] | None = None,
        *,
        strict_mode: bool = True,
    ) -> None:
        self._strict_mode = strict_mode
        # Merge builtins + custom; normalise to lowercase for matching
        extra = [p.lower() for p in (custom_patterns or [])]
        self._patterns: tuple[str, ...] = _BUILTIN_PATTERNS + tuple(extra)

    def scan(self, text: str) -> CheckResult:
        """Scan *text* for injection phrases.

        Returns:
            CheckResult with ``threat=False`` and empty fields when clean,
            or ``threat=True`` with the first matched pattern and a reason
            string when a threat is detected.
        """
        text_lower = text.lower()
        for phrase in self._patterns:
            if phrase in text_lower:
                blocked = self._strict_mode
                return CheckResult(
                    threat=True,
                    blocked=blocked,
                    reason=f"Injection phrase detected: '{phrase}'",
                    pattern=phrase,
                )
        return CheckResult(threat=False, blocked=False, reason="", pattern="")
