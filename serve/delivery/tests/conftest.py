"""Conftest for Delivery package tests."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def _tmp_path(tmp_path: Path) -> Path:
    """Alias for tmp_path with underscore prefix (for tests that use _tmp_path)."""
    return tmp_path
