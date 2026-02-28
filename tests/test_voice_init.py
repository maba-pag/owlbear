"""Tests for voice package initialisation — Task #91."""

from __future__ import annotations


def test_import_owlbear_voice() -> None:
    """Importing owlbear.voice must succeed even without optional deps."""
    import owlbear.voice  # noqa: F401
