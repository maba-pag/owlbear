"""Regression checks for the repository's pytest configuration."""

from __future__ import annotations

import tomllib
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def test_pytest_timeouts_preserve_suite_headroom_and_test_timeout() -> None:
    config = tomllib.loads((_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    options = config["tool"]["pytest"]["ini_options"]

    assert options["timeout"] == 30
    assert options["session_timeout"] == 900
