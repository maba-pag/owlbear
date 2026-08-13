"""Root conftest.py — shared fixtures and marker registrations for v2 tests."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

_FOCUSED_WORKERS = 4
_FULL_SUITE_WORKERS = 10


@pytest.fixture
def project_root() -> Path:
    """Return the repository root as a Path."""
    return Path(__file__).parent


@pytest.fixture
def run_init_without_test_surface() -> Callable[..., None]:
    """Run setup initialization for a project without test-surface scaffolding."""

    def run(initializer: Callable[..., object], /, *args: object, **kwargs: object) -> None:
        kwargs.setdefault("github_repository", "example/project")
        initializer(*args, **kwargs)

    return run


def pytest_configure(config: pytest.Config) -> None:
    """Register project-wide markers."""
    config.addinivalue_line(
        "markers",
        "api: tests that require API integrations or network services",
    )
    config.addinivalue_line(
        "markers",
        "slow: tests that are long-running (subprocess-heavy tests)",
    )
    config.addinivalue_line(
        "markers",
        "benchmark: latency benchmarks — run with -v -s to see results",
    )
    config.addinivalue_line(
        "filterwarnings",
        "ignore::pluggy.PluggyTeardownRaisedWarning",
    )


def pytest_xdist_auto_num_workers(config: pytest.Config) -> int:
    """Return worker count for ``-n auto`` based on test scope.

    Called by xdist when ``-n auto`` is in addopts / CLI.
    - Specific ``.py`` files in args → fewer workers (startup overhead matters)
    - Whole directories → more workers (subprocess-heavy tests benefit)

    Override: ``-n 0`` to disable parallelism, ``-n <X>`` for explicit count.
    """
    has_py_file = any(a.endswith(".py") for a in config.args)
    return _FOCUSED_WORKERS if has_py_file else _FULL_SUITE_WORKERS
