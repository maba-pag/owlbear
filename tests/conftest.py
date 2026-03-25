"""Shared pytest fixtures and helpers for the OwlBear test suite."""

from __future__ import annotations

import os
import subprocess
import warnings
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from owlbear.config import OwlBearSettings, get_settings

# ---------------------------------------------------------------------------
# Skip test files that need optional dependencies not installed in dev
# ---------------------------------------------------------------------------

_NUMPY_FILES = [
    "test_embedding_idle_timeout.py",
    "test_knowledge_embeddings.py",
    "test_voice_stt.py",
]

_QDRANT_FILES = [
    "test_qdrant_vector_store.py",
    "test_search_benchmark.py",
]


def _detect_missing_optional_deps() -> list[str]:
    """Return test globs to skip and emit a warning for each skipped file."""
    skipped: list[str] = []

    try:
        import numpy  # noqa: F401,ICN001
    except ModuleNotFoundError:
        skipped.extend(_NUMPY_FILES)
        for f in _NUMPY_FILES:
            warnings.warn(
                f"Skipping {f}: numpy not installed",
                stacklevel=2,
            )

    try:
        import qdrant_client  # noqa: F401
    except ModuleNotFoundError:
        skipped.extend(_QDRANT_FILES)
        for f in _QDRANT_FILES:
            warnings.warn(
                f"Skipping {f}: qdrant_client not installed",
                stacklevel=2,
            )

    return skipped


collect_ignore_glob: list[str] = _detect_missing_optional_deps()


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


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    """Clear the ``get_settings`` cache between tests."""
    get_settings.cache_clear()


# ---------------------------------------------------------------------------
# Shared test helpers (extracted from individual test files — task #808)
# ---------------------------------------------------------------------------


class MockChannel:
    """Minimal ChannelPlugin mock with programmable receive sequence."""

    def __init__(self, messages: list[str | None]) -> None:
        self._messages = list(messages)
        self._index = 0
        self.sent: list[str] = []

    @property
    def name(self) -> str:
        return "mock"

    async def send(self, message: str) -> None:
        self.sent.append(message)

    async def receive(self, *, prompt: str | None = None) -> str | None:  # noqa: ARG002
        if self._index >= len(self._messages):
            return None
        msg = self._messages[self._index]
        self._index += 1
        return msg


def make_mock_toolset(return_value: object = "tool_result") -> MagicMock:
    """Create a mock AbstractToolset with an async call_tool."""
    mock_ts = MagicMock()
    mock_ts.call_tool = AsyncMock(return_value=return_value)
    return mock_ts


def make_settings(tmp_path: Path, **overrides: object) -> OwlBearSettings:
    """Build test-safe settings pointing at *tmp_path*."""
    defaults: dict[str, object] = {
        "copilot_token_path": tmp_path / "token.json",
        "agents_dir": tmp_path / "agents",
        "usage_path": tmp_path / "usage.jsonl",
    }
    defaults.update(overrides)
    return OwlBearSettings(**defaults)  # type: ignore[arg-type]


def make_completed_process(
    *,
    returncode: int = 0,
    stdout: str = "",
    stderr: str = "",
) -> subprocess.CompletedProcess[str]:
    """Build a real text-mode subprocess.CompletedProcess for use in tests."""
    return subprocess.CompletedProcess(
        args=[],
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


def make_missing_binary_error(
    *,
    binary_path: str = "kanban/kanban-md.exe",
) -> FileNotFoundError:
    """Build a FileNotFoundError used by CLI tests for missing kanban-md."""
    return FileNotFoundError(f"No such file or directory: '{binary_path}'")
