"""Root conftest.py — shared fixtures and marker registrations for v2 tests."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

pytest_plugins = ("owlbear_tools.flaky",)

_FOCUSED_WORKERS = 4
_FULL_SUITE_WORKERS = 10


@pytest.fixture
def project_root() -> Path:
    """Return the repository root as a Path."""
    return Path(__file__).parent


@pytest.fixture
def run_init_without_test_surface() -> Callable[..., None]:
    """Run setup initialization for a project without test-surface scaffolding, consenting to its writes."""

    def run(initializer: Callable[..., object], /, *args: object, **kwargs: object) -> None:
        kwargs.setdefault("yes", True)
        initializer(*args, **kwargs)

    return run


TODAYS_MEMORY_VALUES = {
    "outstanding_boost": 0.1,
    "unremarkable_penalty": 0.01,
    "stale_factor": 50,
    "recall_limit": 20,
    "explore_slots": 2,
    "challenge_slots": 2,
}


@pytest.fixture
def todays_memory_values(monkeypatch: pytest.MonkeyPatch) -> None:
    """Give the memory tools the values they once had in code, for tests of other behaviour than the values.

    Tests of the values themselves write a real ``config.json`` and leave this fixture out.
    """
    from owlbear_memory_mcp import tools  # noqa: PLC0415

    def values(_ctx: object, *names: str) -> dict[str, float]:
        return {name: TODAYS_MEMORY_VALUES[name] for name in names}

    monkeypatch.setattr(tools, "_memory_values", values)


def pytest_configure(config: pytest.Config) -> None:
    """Silence pluggy's teardown warning project-wide."""
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
