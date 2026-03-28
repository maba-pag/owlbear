"""Root conftest.py — shared fixtures and marker registrations for v2 tests."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def project_root() -> Path:
    """Return the repository root as a Path."""
    return Path(__file__).parent


def pytest_configure(config: pytest.Config) -> None:
    """Register project-wide markers."""
    config.addinivalue_line(
        "markers",
        "api: tests that require API integrations or network services",
    )
    config.addinivalue_line(
        "markers",
        "slow: tests that are long-running",
    )
