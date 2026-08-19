"""Tests for the setup CLI's Python version requirement."""

from __future__ import annotations

import importlib.util
import runpy
import sys
import types
from collections import namedtuple
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).parent.parent
_INIT_PATH = _REPO_ROOT / "setup" / "init.py"


def _load_init_module() -> types.ModuleType:
    spec = importlib.util.spec_from_file_location("owlbear_setup_init_python_version", _INIT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_accepts_minimum_python_version() -> None:
    _load_init_module()._check_python_version((3, 14, 6))  # noqa: SLF001


def test_rejects_python_version_below_minimum() -> None:
    with pytest.raises(SystemExit, match=r"Python 3\.14\.6 or newer"):
        _load_init_module()._check_python_version((3, 14, 5))  # noqa: SLF001


def test_cli_checks_python_version_before_argument_parsing(monkeypatch: pytest.MonkeyPatch) -> None:
    version_info = namedtuple("version_info", "major minor micro releaselevel serial")
    monkeypatch.setattr(sys, "version_info", version_info(3, 14, 5, "final", 0))
    monkeypatch.setattr(sys, "argv", [str(_INIT_PATH), "--help"])

    with pytest.raises(SystemExit, match=r"Python 3\.14\.6 or newer"):
        runpy.run_path(str(_INIT_PATH), run_name="__main__")
