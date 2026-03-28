"""Trivial smoke test — verifies orchestrator package is importable."""

from __future__ import annotations

import owlbear


def test_orchestrator_package_importable() -> None:
    """Orchestrator package can be imported."""
    assert owlbear.__name__ == "owlbear"
