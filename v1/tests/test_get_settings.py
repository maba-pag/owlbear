"""Tests for owlbear.config.get_settings — lazy-singleton cache (#807)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from owlbear.config import OwlBearSettings, get_settings

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> Generator[None, None, None]:
    """Clear get_settings cache before and after each test.

    Prevents cross-test state leakage from the @functools.cache singleton.
    """
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class TestFromAC_GetSettingsSingleton:
    """AC-driven tests: get_settings() returns a @functools.cache singleton."""

    def test_get_settings_returns_cached_instance(self) -> None:
        """Two calls to get_settings() return the exact same object (identity check)."""
        first = get_settings()
        second = get_settings()
        assert first is second

    def test_get_settings_cache_clear_creates_fresh(self) -> None:
        """After cache_clear(), get_settings() returns a new instance."""
        original = get_settings()
        get_settings.cache_clear()
        refreshed = get_settings()
        assert refreshed is not original


class TestFromAC_GetSettingsEdgeCases:
    """Edge cases and boundary conditions for the get_settings singleton."""

    def test_get_settings_returns_owlbearsettings_instance(self) -> None:
        """get_settings() must return an OwlBearSettings instance."""
        result = get_settings()
        assert isinstance(result, OwlBearSettings)

    def test_multiple_cache_clear_cycles_produce_distinct_instances(self) -> None:
        """Each cache_clear -> get_settings cycle yields a distinct object."""
        instances = []
        for _ in range(3):
            get_settings.cache_clear()
            instances.append(get_settings())
        # All instances should be distinct objects
        assert len({id(inst) for inst in instances}) == 3

    def test_cache_clear_is_callable(self) -> None:
        """get_settings must expose cache_clear (functools.cache protocol)."""
        assert callable(get_settings.cache_clear)
