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


# --- CDP field defaults ---


class TestBrowserConfigCDPDefaults:
    """New CDP-related fields should have sensible defaults."""

    def test_cdp_endpoint_defaults_to_none(self) -> None:
        cfg = BrowserConfig()
        assert cfg.cdp_endpoint is None

    def test_cdp_port_defaults_to_9222(self) -> None:
        cfg = BrowserConfig()
        assert cfg.cdp_port == 9222

    def test_browser_executable_defaults_to_none(self) -> None:
        cfg = BrowserConfig()
        assert cfg.browser_executable is None

    def test_auto_launch_defaults_to_true(self) -> None:
        cfg = BrowserConfig()
        assert cfg.auto_launch is True

    def test_default_config_unchanged_behavior(self) -> None:
        """Default BrowserConfig() has no CDP behavior change."""
        cfg = BrowserConfig()
        assert cfg.cdp_endpoint is None
        assert cfg.auto_launch is True
        assert cfg.browser_executable is None


# --- CDP field custom values ---


class TestBrowserConfigCDPCustomValues:
    """CDP fields accept valid custom values."""

    def test_cdp_endpoint_localhost(self) -> None:
        cfg = BrowserConfig(cdp_endpoint="http://localhost:9222")
        assert cfg.cdp_endpoint == "http://localhost:9222"

    def test_cdp_endpoint_127_0_0_1(self) -> None:
        cfg = BrowserConfig(cdp_endpoint="http://127.0.0.1:9222")
        assert cfg.cdp_endpoint == "http://127.0.0.1:9222"

    def test_cdp_port_custom(self) -> None:
        cfg = BrowserConfig(cdp_port=9333)
        assert cfg.cdp_port == 9333

    def test_browser_executable_custom_path(self) -> None:
        cfg = BrowserConfig(browser_executable="C:/path/to/msedge.exe")
        assert cfg.browser_executable == "C:/path/to/msedge.exe"

    def test_auto_launch_false(self) -> None:
        cfg = BrowserConfig(auto_launch=False)
        assert cfg.auto_launch is False


# --- CDP field validation ---


class TestBrowserConfigCDPValidation:
    """CDP fields must reject invalid values."""

    def test_cdp_endpoint_non_localhost_host_raises(self) -> None:
        with pytest.raises(ValidationError, match="cdp_endpoint"):
            BrowserConfig(cdp_endpoint="http://evil.com:9222")

    def test_cdp_endpoint_non_http_scheme_raises(self) -> None:
        with pytest.raises(ValidationError, match="cdp_endpoint"):
            BrowserConfig(cdp_endpoint="https://localhost:9222")

    def test_cdp_endpoint_malformed_url_raises(self) -> None:
        with pytest.raises(ValidationError, match="cdp_endpoint"):
            BrowserConfig(cdp_endpoint="not-a-url")

    def test_cdp_port_zero_raises(self) -> None:
        with pytest.raises(ValidationError, match="cdp_port"):
            BrowserConfig(cdp_port=0)

    def test_cdp_port_above_65535_raises(self) -> None:
        with pytest.raises(ValidationError, match="cdp_port"):
            BrowserConfig(cdp_port=70000)

    def test_cdp_port_negative_raises(self) -> None:
        with pytest.raises(ValidationError, match="cdp_port"):
            BrowserConfig(cdp_port=-1)


# --- CDP frozen-model checks ---


class TestBrowserConfigCDPFrozen:
    """Frozen model rejects mutation of new CDP fields."""

    def test_frozen_cdp_endpoint(self) -> None:
        cfg = BrowserConfig()
        with pytest.raises(ValidationError):
            cfg.cdp_endpoint = "http://localhost:9222"  # type: ignore[misc]

    def test_frozen_cdp_port(self) -> None:
        cfg = BrowserConfig()
        with pytest.raises(ValidationError):
            cfg.cdp_port = 1234  # type: ignore[misc]

    def test_frozen_browser_executable(self) -> None:
        cfg = BrowserConfig()
        with pytest.raises(ValidationError):
            cfg.browser_executable = "/usr/bin/chrome"  # type: ignore[misc]

    def test_frozen_auto_launch(self) -> None:
        cfg = BrowserConfig()
        with pytest.raises(ValidationError):
            cfg.auto_launch = False  # type: ignore[misc]


# --- CDP endpoint None passthrough (line 73) ---


class TestCDPEndpointNonePassthrough:
    """Validator should return None when cdp_endpoint is explicitly None."""

    def test_explicit_none_returns_none(self) -> None:
        """Passing cdp_endpoint=None explicitly should pass validation."""
        cfg = BrowserConfig(cdp_endpoint=None)
        assert cfg.cdp_endpoint is None


# --- CDP endpoint urlparse failure (lines 76-78) ---


class TestCDPEndpointUrlparseFailure:
    """The except-Exception branch in _cdp_endpoint_localhost_only."""

    def test_urlparse_exception_raises_validation_error(self) -> None:
        """When urlparse raises, validator should raise 'not a valid URL'."""
        from unittest.mock import patch

        with (
            patch(
                "owlbear.tools.browser.config.urlparse",
                side_effect=ValueError("boom"),
            ),
            pytest.raises(ValidationError, match="cdp_endpoint is not a valid URL"),
        ):
            BrowserConfig(cdp_endpoint="http://localhost:9222")


# --- Retroactive coverage: unparseable CDP endpoint (#831) ---


class TestFromAC_BrowserConfigCdpUnparseable:  # noqa: N801
    """cdp_endpoint with an unparseable URL path raises ValidationError."""

    def test_cdp_endpoint_unparseable_url_raises_validation_error(self) -> None:
        """':::not-a-url' has no http scheme — validator rejects it."""
        with pytest.raises(ValidationError, match="cdp_endpoint"):
            BrowserConfig(cdp_endpoint=":::not-a-url")
