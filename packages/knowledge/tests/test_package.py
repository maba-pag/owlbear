"""Trivial smoke test — verifies knowledge package is importable."""

from __future__ import annotations

import owlbear_knowledge


def test_knowledge_package_importable() -> None:
    """Knowledge package can be imported."""
    assert owlbear_knowledge.__name__ == "owlbear_knowledge"
