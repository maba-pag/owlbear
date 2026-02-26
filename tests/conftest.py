"""Shared pytest fixtures for the OwlBear test suite."""

from __future__ import annotations

import pytest

from owlbear.config import OwlBearSettings


@pytest.fixture
def default_settings() -> OwlBearSettings:
    """Return an ``OwlBearSettings`` instance with all defaults."""
    return OwlBearSettings()
