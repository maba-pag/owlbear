"""Tests for CrawlConfig model — seed URLs, depth/page limits, regex patterns."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from owlbear.tools.browser.crawl_config import CrawlConfig

_SEED = ["https://example.com"]


# --- Frozen model ---


class TestCrawlConfigFrozen:
    """CrawlConfig must be a frozen (immutable) Pydantic model."""

    def test_is_frozen_model(self) -> None:
        cfg = CrawlConfig(seed_urls=_SEED)
        with pytest.raises(ValidationError):
            cfg.max_depth = 5  # type: ignore[misc]

    def test_frozen_seed_urls(self) -> None:
        cfg = CrawlConfig(seed_urls=_SEED)
        with pytest.raises(ValidationError):
            cfg.seed_urls = ["https://other.com"]  # type: ignore[misc]


# --- Defaults ---


class TestCrawlConfigDefaults:
    """CrawlConfig should expose sensible defaults."""

    def test_default_max_depth(self) -> None:
        cfg = CrawlConfig(seed_urls=_SEED)
        assert cfg.max_depth == 1

    def test_default_max_pages(self) -> None:
        cfg = CrawlConfig(seed_urls=_SEED)
        assert cfg.max_pages == 50

    def test_default_same_domain_only(self) -> None:
        cfg = CrawlConfig(seed_urls=_SEED)
        assert cfg.same_domain_only is True

    def test_default_delay_seconds(self) -> None:
        cfg = CrawlConfig(seed_urls=_SEED)
        assert cfg.delay_seconds == 1.5

    def test_default_respect_robots(self) -> None:
        cfg = CrawlConfig(seed_urls=_SEED)
        assert cfg.respect_robots is True

    def test_default_user_agent(self) -> None:
        cfg = CrawlConfig(seed_urls=_SEED)
        assert cfg.user_agent == "OwlBear/1.0 (research crawler)"

    def test_default_allow_patterns_empty(self) -> None:
        cfg = CrawlConfig(seed_urls=_SEED)
        assert cfg.allow_patterns == []

    def test_default_deny_patterns_empty(self) -> None:
        cfg = CrawlConfig(seed_urls=_SEED)
        assert cfg.deny_patterns == []


# --- Required field: seed_urls ---


class TestSeedUrlsRequired:
    """seed_urls is required and must be non-empty."""

    def test_missing_seed_urls_raises(self) -> None:
        with pytest.raises(ValidationError):
            CrawlConfig()  # type: ignore[call-arg]

    def test_empty_seed_urls_raises(self) -> None:
        with pytest.raises(ValidationError, match="seed_urls"):
            CrawlConfig(seed_urls=[])


# --- Field validators ---


class TestFieldValidators:
    """Numeric fields enforce their lower bounds."""

    def test_max_depth_negative_raises(self) -> None:
        with pytest.raises(ValidationError, match="max_depth"):
            CrawlConfig(seed_urls=_SEED, max_depth=-1)

    def test_max_depth_zero_allowed(self) -> None:
        cfg = CrawlConfig(seed_urls=_SEED, max_depth=0)
        assert cfg.max_depth == 0

    def test_max_pages_zero_raises(self) -> None:
        with pytest.raises(ValidationError, match="max_pages"):
            CrawlConfig(seed_urls=_SEED, max_pages=0)

    def test_max_pages_negative_raises(self) -> None:
        with pytest.raises(ValidationError, match="max_pages"):
            CrawlConfig(seed_urls=_SEED, max_pages=-5)

    def test_max_pages_one_allowed(self) -> None:
        cfg = CrawlConfig(seed_urls=_SEED, max_pages=1)
        assert cfg.max_pages == 1

    def test_delay_seconds_negative_raises(self) -> None:
        with pytest.raises(ValidationError, match="delay_seconds"):
            CrawlConfig(seed_urls=_SEED, delay_seconds=-0.1)

    def test_delay_seconds_zero_allowed(self) -> None:
        cfg = CrawlConfig(seed_urls=_SEED, delay_seconds=0.0)
        assert cfg.delay_seconds == 0.0


# --- Regex pattern validation ---


class TestRegexPatternValidation:
    """allow_patterns and deny_patterns must be compilable regexes."""

    def test_valid_allow_patterns(self) -> None:
        cfg = CrawlConfig(
            seed_urls=_SEED,
            allow_patterns=[r"https://.*\.example\.com", r"/docs/.*"],
        )
        assert len(cfg.allow_patterns) == 2

    def test_valid_deny_patterns(self) -> None:
        cfg = CrawlConfig(
            seed_urls=_SEED,
            deny_patterns=[r".*\.pdf$", r"/login"],
        )
        assert len(cfg.deny_patterns) == 2

    def test_invalid_allow_pattern_raises(self) -> None:
        with pytest.raises(ValidationError, match="allow_patterns"):
            CrawlConfig(seed_urls=_SEED, allow_patterns=[r"[invalid(regex"])

    def test_invalid_deny_pattern_raises(self) -> None:
        with pytest.raises(ValidationError, match="deny_patterns"):
            CrawlConfig(seed_urls=_SEED, deny_patterns=[r"[bad"])

    def test_mixed_valid_and_invalid_raises(self) -> None:
        with pytest.raises(ValidationError):
            CrawlConfig(
                seed_urls=_SEED,
                allow_patterns=[r"https://ok\.com", r"[bad"],
            )
