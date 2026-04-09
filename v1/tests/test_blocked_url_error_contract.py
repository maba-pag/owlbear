"""Contract tests for #850 — BlockedURLError dependency inversion.

Covers AC items not addressed in tests/test_blocked_url_error_location.py:

- AC1: BlockedURLError constructor preserves url, pattern, and exact message format;
       inherits from OwlBearError.
- AC3: owlbear.tools.browser.safety re-exports BlockedURLError so the backward-compat
       import path returns the same class as owlbear.core.exceptions.BlockedURLError.
- AC4: URLSafetyGuard.check_url() raises BlockedURLError for blocklist and allowlist
       denials, with the matched pattern value unchanged in the exception.
- AC6: BlockedURLError is NOT exported from owlbear.tools.__init__.py; the scope of
       this task is limited to the core exception layer and the browser safety module.
"""

from __future__ import annotations

import pytest

from owlbear.tools.browser.config import BrowserConfig
from owlbear.tools.browser.safety import URLSafetyGuard

# ---------------------------------------------------------------------------
# AC1 — BlockedURLError constructor and class hierarchy
# ---------------------------------------------------------------------------


class TestFromAC_BlockedURLErrorDefinition:
    """BlockedURLError must be defined in owlbear.core.exceptions as an OwlBearError subclass."""

    def test_is_owlbear_error_subclass(self) -> None:
        """BlockedURLError must inherit from OwlBearError."""
        from owlbear.core.exceptions import BlockedURLError, OwlBearError

        assert issubclass(BlockedURLError, OwlBearError)

    def test_url_attribute_exact(self) -> None:
        """BlockedURLError must store the exact url passed to the constructor."""
        from owlbear.core.exceptions import BlockedURLError

        url = "https://blocked.example.com/path?q=1"
        err = BlockedURLError(url, r"blocked\.example\.com")
        assert err.url == url

    def test_pattern_attribute_exact(self) -> None:
        """BlockedURLError must store the exact pattern passed to the constructor."""
        from owlbear.core.exceptions import BlockedURLError

        pattern = r"blocked\.example\.com"
        err = BlockedURLError("https://blocked.example.com", pattern)
        assert err.pattern == pattern

    def test_message_format_exact(self) -> None:
        """Exception message must be 'URL blocked by pattern {pattern!r}: {url}'."""
        from owlbear.core.exceptions import BlockedURLError

        url = "https://blocked.example.com"
        pattern = r"blocked\.example\.com"
        err = BlockedURLError(url, pattern)
        expected = f"URL blocked by pattern {pattern!r}: {url}"
        assert str(err) == expected

    def test_compat_import_from_safety_is_same_class(self) -> None:
        """from owlbear.tools.browser.safety import BlockedURLError must return
        the same class object as owlbear.core.exceptions.BlockedURLError.
        """
        from owlbear.core.exceptions import BlockedURLError as CoreBlockedURLError
        from owlbear.tools.browser.safety import BlockedURLError as SafetyBlockedURLError

        assert SafetyBlockedURLError is CoreBlockedURLError

    def test_allowlist_sentinel_pattern_value(self) -> None:
        """BlockedURLError for allowlist denial must use the sentinel '<not in allowlist>'."""
        from owlbear.core.exceptions import BlockedURLError

        err = BlockedURLError("https://other.com", "<not in allowlist>")
        assert err.pattern == "<not in allowlist>"


# ---------------------------------------------------------------------------
# AC4 — URLSafetyGuard.check_url() raises with unchanged pattern values
# ---------------------------------------------------------------------------


class TestFromAC_URLSafetyGuardCheckURL:
    """check_url() must raise BlockedURLError for blocklist and allowlist denials."""

    def test_check_url_raises_for_blocklist_match(self) -> None:
        """check_url raises BlockedURLError when url matches a blocked_urls pattern."""
        from owlbear.core.exceptions import BlockedURLError

        cfg = BrowserConfig(blocked_urls=[r"evil\.com"])
        guard = URLSafetyGuard(cfg)
        with pytest.raises(BlockedURLError):
            guard.check_url("https://evil.com/page")

    def test_check_url_blocklist_exception_carries_pattern(self) -> None:
        """Raised BlockedURLError must carry the matching blocklist pattern exactly."""
        from owlbear.core.exceptions import BlockedURLError

        pattern = r"evil\.com"
        cfg = BrowserConfig(blocked_urls=[pattern])
        guard = URLSafetyGuard(cfg)
        with pytest.raises(BlockedURLError) as exc_info:
            guard.check_url("https://evil.com/page")
        assert exc_info.value.pattern == pattern

    def test_check_url_blocklist_exception_carries_url(self) -> None:
        """Raised BlockedURLError must carry the blocked url exactly."""
        from owlbear.core.exceptions import BlockedURLError

        url = "https://evil.com/page"
        cfg = BrowserConfig(blocked_urls=[r"evil\.com"])
        guard = URLSafetyGuard(cfg)
        with pytest.raises(BlockedURLError) as exc_info:
            guard.check_url(url)
        assert exc_info.value.url == url

    def test_check_url_raises_for_allowlist_denial(self) -> None:
        """check_url raises BlockedURLError when allowed_urls is set but url does not match."""
        from owlbear.core.exceptions import BlockedURLError

        cfg = BrowserConfig(allowed_urls=[r"https://safe\.example\.com/.*"])
        guard = URLSafetyGuard(cfg)
        with pytest.raises(BlockedURLError):
            guard.check_url("https://other.com/page")

    def test_check_url_allowlist_denial_uses_sentinel_pattern(self) -> None:
        """Allowlist denial must set pattern to '<not in allowlist>' (unchanged sentinel)."""
        from owlbear.core.exceptions import BlockedURLError

        cfg = BrowserConfig(allowed_urls=[r"https://safe\.example\.com/.*"])
        guard = URLSafetyGuard(cfg)
        with pytest.raises(BlockedURLError) as exc_info:
            guard.check_url("https://other.com/page")
        assert exc_info.value.pattern == "<not in allowlist>"

    def test_check_url_does_not_raise_for_allowed_url(self) -> None:
        """check_url must NOT raise when url matches an allowed_urls pattern."""
        cfg = BrowserConfig(allowed_urls=[r"https://safe\.example\.com/.*"])
        guard = URLSafetyGuard(cfg)
        guard.check_url("https://safe.example.com/page")  # must not raise

    def test_check_url_blocklist_takes_precedence_over_allowlist(self) -> None:
        """Blocklist denial must fire even when url also matches an allowlist pattern."""
        from owlbear.core.exceptions import BlockedURLError

        cfg = BrowserConfig(
            blocked_urls=[r"evil\.com"],
            allowed_urls=[r"evil\.com"],  # would be allowed if blocklist didn't take priority
        )
        guard = URLSafetyGuard(cfg)
        with pytest.raises(BlockedURLError) as exc_info:
            guard.check_url("https://evil.com/page")
        # pattern must be the blocklist pattern, not the sentinel
        assert exc_info.value.pattern == r"evil\.com"


# ---------------------------------------------------------------------------
# AC6 — scope boundary: BlockedURLError must NOT appear in owlbear.tools
# ---------------------------------------------------------------------------


class TestFromAC_ToolsInitScope:
    """BlockedURLError must not be added to owlbear.tools.__all__ by this task."""

    def test_blocked_url_error_not_in_tools_all(self) -> None:
        """owlbear.tools.__all__ must not export BlockedURLError."""
        import owlbear.tools

        assert "BlockedURLError" not in owlbear.tools.__all__

    def test_blocked_url_error_not_a_top_level_tools_attribute(self) -> None:
        """owlbear.tools must not expose BlockedURLError as a direct module attribute
        introduced by this task (i.e. no new re-export added to tools/__init__.py).
        """
        import owlbear.tools

        # hasattr checks the module namespace, not __all__
        assert not hasattr(owlbear.tools, "BlockedURLError")
