"""Runtime guard tests for setup/init.py."""

from __future__ import annotations

import importlib.util
import runpy
import sys
import types
from pathlib import Path
from unittest.mock import patch

import pytest

_REPO_ROOT = Path(__file__).parent.parent
_INIT_PATH = _REPO_ROOT / "setup" / "init.py"


def _version_info(major: int, minor: int, micro: int) -> tuple[int, int, int, str, int]:
    return type(sys.version_info)((major, minor, micro, "final", 0))


def _one_patch_below(version: tuple[int, int, int]) -> tuple[int, int, int]:
    major, minor, micro = version
    if micro > 0:
        return major, minor, micro - 1
    if minor > 0:
        return major, minor - 1, 99
    return major - 1, 99, 99


def _load_init_module(*, bootstrap_version: tuple[int, int, int] | None = None) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location("owlbear_setup_init_runtime", _INIT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    active_version = bootstrap_version if bootstrap_version is not None else sys.version_info[:3]
    version_info = _version_info(*active_version)
    with patch.object(sys, "version_info", version_info):
        spec.loader.exec_module(module)
    return module


def test_check_python_version_accepts_supported_versions() -> None:
    init_module = _load_init_module()
    minimum = init_module._MINIMUM_PYTHON
    major, minor, micro = minimum

    for version in (minimum, (major, minor, micro + 1), (major, minor + 1, 0), (major + 1, 0, 0)):
        assert init_module._check_python_version(version) is None


def test_check_python_version_rejects_older_versions_with_actionable_message() -> None:
    init_module = _load_init_module()
    minimum_python_text = ".".join(str(part) for part in init_module._MINIMUM_PYTHON)
    rejected = _one_patch_below(init_module._MINIMUM_PYTHON)
    rejected_text = ".".join(str(part) for part in rejected)
    expected = rf"OwlBear requires Python {minimum_python_text} or newer; found Python {rejected_text}\."

    with pytest.raises(SystemExit, match=expected) as exc:
        init_module._check_python_version(rejected)

    assert isinstance(exc.value.code, str)
    message = exc.value.code
    assert "uv run --project" in message
    assert "setup/init.py" in message


def test_setup_cli_path_runs_runtime_guard_before_argument_parsing() -> None:
    minimum = _load_init_module()._MINIMUM_PYTHON
    minimum_python_text = ".".join(str(part) for part in minimum)
    rejected = _one_patch_below(minimum)
    rejected_text = ".".join(str(part) for part in rejected)
    version_info = _version_info(*rejected)
    expected = rf"OwlBear requires Python {minimum_python_text} or newer; found Python {rejected_text}\."
    with (
        patch.object(sys, "version_info", version_info),
        patch("argparse.ArgumentParser.parse_args") as parse_args,
        pytest.raises(SystemExit, match=expected),
    ):
        runpy.run_path(str(_INIT_PATH), run_name="__main__")

    parse_args.assert_not_called()
