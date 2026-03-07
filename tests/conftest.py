"""Shared pytest fixtures for the OwlBear test suite."""

from __future__ import annotations

import os
import warnings

import pytest

from owlbear.config import OwlBearSettings

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
