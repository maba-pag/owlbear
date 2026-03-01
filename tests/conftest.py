"""Shared pytest fixtures for the OwlBear test suite."""

from __future__ import annotations

import os

import pytest

from owlbear.config import OwlBearSettings


@pytest.fixture
def default_settings(monkeypatch: pytest.MonkeyPatch) -> OwlBearSettings:
    """Return an ``OwlBearSettings`` instance with all defaults.

    Clears every ``OWLBEAR_*`` env var first so that the developer's
    shell environment (or test pollution from earlier tests) never leaks
    into the assertion.  Scanned at *execution* time, not import time.
    """
    for var in [k for k in os.environ if k.startswith("OWLBEAR_")]:
        monkeypatch.delenv(var, raising=False)
    return OwlBearSettings()
