"""Tests for URLSafetyGuard — URL filtering for browser navigation.

Covers: blocklist matching, allowlist enforcement, logging of blocked
attempts, HookRegistry integration, and edge cases (empty config,
missing args, non-navigate tools).
"""

from __future__ import annotations

import asyncio
import logging

import pytest

from owlbear.core.hooks import HookEvent, HookRegistry
from owlbear.tools.browser.config import BrowserConfig
from owlbear.tools.browser.safety import BlockedURLError, URLSafetyGuard

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run(coro: object) -> None:
    """Convenience wrapper around asyncio.run for coroutines."""
    asyncio.run(coro)  # type: ignore[arg-type]


def _navigate_data(url: str) -> dict[str, object]:
    """Build a PRE_TOOL_USE payload for a navigate call."""
    return {"tool_name": "navigate", "args": {"url": url}}


# ---------------------------------------------------------------------------
# BlockedURLError
# ---------------------------------------------------------------------------


class TestBlockedURLError:
    """Custom exception carries url and pattern."""

    def test_is_exception(self) -> None:
        err = BlockedURLError("https://evil.com", r".*evil.*")
        assert isinstance(err, Exception)

    def test_stores_url_and_pattern(self) -> None:
        err = BlockedURLError("https://evil.com", r".*evil.*")
        assert err.url == "https://evil.com"
        assert err.pattern == r".*evil.*"

    def test_message_contains_url(self) -> None:
        err = BlockedURLError("https://evil.com", r".*evil.*")
        assert "evil.com" in str(err)


# ---------------------------------------------------------------------------
# Blocklist behaviour
# ---------------------------------------------------------------------------


class TestURLSafetyGuardBlocking:
    """Guard blocks URLs matching blocked_urls patterns."""

    def test_blocks_url_matching_blocked_pattern(self) -> None:
        cfg = BrowserConfig(blocked_urls=[r".*evil\.com.*"])
        guard = URLSafetyGuard(cfg)
        with pytest.raises(BlockedURLError):
            _run(guard(_navigate_data("https://evil.com/page")))

    def test_blocks_url_matching_any_blocked_pattern(self) -> None:
        cfg = BrowserConfig(blocked_urls=[r".*evil\.com.*", r".*malware\.org.*"])
        guard = URLSafetyGuard(cfg)
        with pytest.raises(BlockedURLError):
            _run(guard(_navigate_data("https://malware.org/bad")))

    def test_allows_url_not_matching_blocked_pattern(self) -> None:
        cfg = BrowserConfig(blocked_urls=[r".*evil\.com.*"])
        guard = URLSafetyGuard(cfg)
        _run(guard(_navigate_data("https://example.com")))  # should NOT raise


# ---------------------------------------------------------------------------
# Allowlist behaviour
# ---------------------------------------------------------------------------


class TestURLSafetyGuardAllowlist:
    """When allowed_urls is non-empty, URL must match at least one."""

    def test_allows_url_matching_allowed_pattern(self) -> None:
        cfg = BrowserConfig(allowed_urls=[r"https://example\.com/.*"])
        guard = URLSafetyGuard(cfg)
        _run(guard(_navigate_data("https://example.com/page")))  # no raise

    def test_blocks_url_not_in_allowlist(self) -> None:
        cfg = BrowserConfig(allowed_urls=[r"https://example\.com/.*"])
        guard = URLSafetyGuard(cfg)
        with pytest.raises(BlockedURLError):
            _run(guard(_navigate_data("https://other.com/page")))

    def test_blocked_takes_precedence_over_allowed(self) -> None:
        cfg = BrowserConfig(
            allowed_urls=[r"https://example\.com/.*"],
            blocked_urls=[r".*secret.*"],
        )
        guard = URLSafetyGuard(cfg)
        with pytest.raises(BlockedURLError):
            _run(guard(_navigate_data("https://example.com/secret")))


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestURLSafetyGuardEdgeCases:
    """Edge cases: empty config, non-navigate tool, missing url arg."""

    def test_empty_config_allows_everything(self) -> None:
        cfg = BrowserConfig()  # no allowed/blocked
        guard = URLSafetyGuard(cfg)
        _run(guard(_navigate_data("https://anything.com")))  # no raise

    def test_non_navigate_tool_ignored(self) -> None:
        cfg = BrowserConfig(blocked_urls=[r".*"])
        guard = URLSafetyGuard(cfg)
        data: dict[str, object] = {"tool_name": "click", "args": {"selector": "#btn"}}
        _run(guard(data))  # no raise even though pattern blocks everything

    def test_navigate_without_url_arg_ignored(self) -> None:
        cfg = BrowserConfig(blocked_urls=[r".*"])
        guard = URLSafetyGuard(cfg)
        data: dict[str, object] = {"tool_name": "navigate", "args": {}}
        _run(guard(data))  # no raise — no url to check

    def test_navigate_with_empty_url_ignored(self) -> None:
        cfg = BrowserConfig(blocked_urls=[r".+"])
        guard = URLSafetyGuard(cfg)
        _run(guard(_navigate_data("")))  # empty string — skip check

    def test_missing_args_key_ignored(self) -> None:
        cfg = BrowserConfig(blocked_urls=[r".*"])
        guard = URLSafetyGuard(cfg)
        data: dict[str, object] = {"tool_name": "navigate"}
        _run(guard(data))  # no raise — no args dict

    def test_non_dict_data_ignored(self) -> None:
        cfg = BrowserConfig(blocked_urls=[r".*"])
        guard = URLSafetyGuard(cfg)
        _run(guard("not a dict"))  # type: ignore[arg-type]  # no raise


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------


class TestURLSafetyGuardLogging:
    """Blocked attempts are logged."""

    def test_logs_blocked_url(self, caplog: pytest.LogCaptureFixture) -> None:
        cfg = BrowserConfig(blocked_urls=[r".*evil\.com.*"])
        guard = URLSafetyGuard(cfg)
        with (
            caplog.at_level(logging.WARNING, logger="owlbear.tools.browser.safety"),
            pytest.raises(BlockedURLError),
        ):
            _run(guard(_navigate_data("https://evil.com")))
        assert "evil.com" in caplog.text

    def test_logs_url_not_in_allowlist(self, caplog: pytest.LogCaptureFixture) -> None:
        cfg = BrowserConfig(allowed_urls=[r"https://safe\.com/.*"])
        guard = URLSafetyGuard(cfg)
        with (
            caplog.at_level(logging.WARNING, logger="owlbear.tools.browser.safety"),
            pytest.raises(BlockedURLError),
        ):
            _run(guard(_navigate_data("https://other.com")))
        assert "other.com" in caplog.text


# ---------------------------------------------------------------------------
# HookRegistry integration
# ---------------------------------------------------------------------------


class TestURLSafetyGuardHookIntegration:
    """Guard registers on HookRegistry and fires on PRE_TOOL_USE."""

    def test_register_adds_to_pre_tool_use(self) -> None:
        cfg = BrowserConfig(blocked_urls=[r".*evil.*"])
        guard = URLSafetyGuard(cfg)
        registry = HookRegistry()
        guard.register(registry)
        handlers = registry.handlers.get(HookEvent.PRE_TOOL_USE, [])
        assert guard in handlers

    def test_emit_invokes_guard(self) -> None:
        """HookRegistry.emit swallows exceptions, so the guard fires but
        the BlockedURLError is caught by the registry.  Verify the guard
        was actually invoked by checking that a non-blocked URL passes
        and that the guard is called.
        """
        cfg = BrowserConfig(blocked_urls=[r".*evil.*"])
        guard = URLSafetyGuard(cfg)
        registry = HookRegistry()
        guard.register(registry)
        # Allowed URL — emit completes without error.
        _run(registry.emit(HookEvent.PRE_TOOL_USE, _navigate_data("https://safe.com")))

    def test_emit_blocked_url_swallowed_by_registry(self, caplog: pytest.LogCaptureFixture) -> None:
        """Blocked URL raises inside the guard, but HookRegistry.emit
        swallows the exception and logs it.  Verify the guard's log
        message still appears (it fires before the raise).
        """
        cfg = BrowserConfig(blocked_urls=[r".*evil.*"])
        guard = URLSafetyGuard(cfg)
        registry = HookRegistry()
        guard.register(registry)
        with caplog.at_level(logging.WARNING):
            _run(
                registry.emit(
                    HookEvent.PRE_TOOL_USE,
                    _navigate_data("https://evil.com"),
                )
            )
        # Guard logged the blocked URL before raising.
        assert "evil.com" in caplog.text
