"""Keep every memory-server test away from the machine's shared data repository."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _no_shared_repository(monkeypatch: pytest.MonkeyPatch) -> None:
    """No shared repository and no named folders, so no real store is read or written; tests set their own."""
    monkeypatch.setenv("OWLBEAR_DATA", "")  # empty means none, so the real pointer is never read
    monkeypatch.delenv("OWLBEAR_MEMORY_DIR", raising=False)
    monkeypatch.delenv("OWLBEAR_MEMORY_GLOBAL_DIR", raising=False)
    monkeypatch.delenv("OWLBEAR_MEMORY_AGENTS", raising=False)
