"""Tests for BrowserConfig model — URL filtering, defaults, edge cases."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from owlbear.tools.browser.config import BrowserConfig

# --- Defaults ---


class TestBrowserConfigDefaults:
    """BrowserConfig should have sensible defaults out of the box."""

    def test_default_headless_is_false(self) -> None:
        cfg = BrowserConfig()
        assert cfg.headless is False

    def test_default_viewport(self) -> None:
        cfg = BrowserConfig()
        assert cfg.viewport == (1280, 720)

    def test_default_timeout_ms(self) -> None:
        cfg = BrowserConfig()
        assert cfg.timeout_ms == 30_000

    def test_default_allowed_urls_empty(self) -> None:
        cfg = BrowserConfig()
        assert cfg.allowed_urls == []

    def test_default_blocked_urls_empty(self) -> None:
        cfg = BrowserConfig()
        assert cfg.blocked_urls == []


# --- Custom values ---


class TestBrowserConfigCustomValues:
    """Fields accept valid custom values."""

    def test_headless_true(self) -> None:
        cfg = BrowserConfig(headless=True)
        assert cfg.headless is True

    def test_custom_viewport(self) -> None:
        cfg = BrowserConfig(viewport=(1920, 1080))
        assert cfg.viewport == (1920, 1080)

    def test_custom_timeout(self) -> None:
        cfg = BrowserConfig(timeout_ms=60_000)
        assert cfg.timeout_ms == 60_000

    def test_allowed_urls_with_patterns(self) -> None:
        patterns = [r"https://example\.com/.*", r"https://docs\.python\.org/.*"]
        cfg = BrowserConfig(allowed_urls=patterns)
        assert cfg.allowed_urls == patterns

    def test_blocked_urls_with_patterns(self) -> None:
        patterns = [r"https://ads\..*", r".*\.tracking\.com"]
        cfg = BrowserConfig(blocked_urls=patterns)
        assert cfg.blocked_urls == patterns


# --- URL pattern validation ---


class TestURLPatternValidation:
    """URL patterns must be valid regular expressions."""

    def test_valid_regex_allowed(self) -> None:
        cfg = BrowserConfig(allowed_urls=[r"https://.*\.example\.com"])
        assert len(cfg.allowed_urls) == 1

    def test_valid_regex_blocked(self) -> None:
        cfg = BrowserConfig(blocked_urls=[r"https://.*\.ads\.com"])
        assert len(cfg.blocked_urls) == 1

    def test_invalid_regex_in_allowed_urls_raises(self) -> None:
        with pytest.raises(ValidationError, match="allowed_urls"):
            BrowserConfig(allowed_urls=[r"[invalid(regex"])

    def test_invalid_regex_in_blocked_urls_raises(self) -> None:
        with pytest.raises(ValidationError, match="blocked_urls"):
            BrowserConfig(blocked_urls=[r"[invalid(regex"])

    def test_mixed_valid_and_invalid_raises(self) -> None:
        with pytest.raises(ValidationError):
            BrowserConfig(allowed_urls=[r"https://ok\.com", r"[bad"])


# --- Edge cases ---


class TestBrowserConfigEdgeCases:
    """Edge cases: empty lists, boundary values, type coercion."""

    def test_empty_allowed_urls_list(self) -> None:
        cfg = BrowserConfig(allowed_urls=[])
        assert cfg.allowed_urls == []

    def test_empty_blocked_urls_list(self) -> None:
        cfg = BrowserConfig(blocked_urls=[])
        assert cfg.blocked_urls == []

    def test_timeout_zero_is_valid(self) -> None:
        cfg = BrowserConfig(timeout_ms=0)
        assert cfg.timeout_ms == 0

    def test_negative_timeout_raises(self) -> None:
        with pytest.raises(ValidationError, match="timeout_ms"):
            BrowserConfig(timeout_ms=-1)

    def test_viewport_must_have_positive_width(self) -> None:
        with pytest.raises(ValidationError, match="viewport"):
            BrowserConfig(viewport=(0, 720))

    def test_viewport_must_have_positive_height(self) -> None:
        with pytest.raises(ValidationError, match="viewport"):
            BrowserConfig(viewport=(1280, 0))

    def test_viewport_negative_dimensions_raises(self) -> None:
        with pytest.raises(ValidationError, match="viewport"):
            BrowserConfig(viewport=(-1, -1))

    def test_model_is_frozen(self) -> None:
        cfg = BrowserConfig()
        with pytest.raises(ValidationError):
            cfg.headless = True  # type: ignore[misc]
