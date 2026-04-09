"""Tests for #560 — Rename ks_ CLI functions to full knowledge_source_ prefix.

TDD red-phase: these tests define the rename contract. After the rename,
the new function names must be importable and the old abbreviated names
must be gone. CLI command names (add, list, show, remove) must remain
unchanged.
"""

from __future__ import annotations

import importlib

# ---------------------------------------------------------------------------
# TestFromAC_NewNamesExist — AC lines 1-4
# ---------------------------------------------------------------------------


class TestFromAC_NewNamesExist:
    """After rename, the full-prefix function names must be importable."""

    def test_knowledge_source_add_importable(self) -> None:
        mod = importlib.import_module("bearclaw.commands.knowledge_source")
        assert hasattr(mod, "knowledge_source_add"), (
            "knowledge_source_add should exist after rename"
        )

    def test_knowledge_source_list_importable(self) -> None:
        mod = importlib.import_module("bearclaw.commands.knowledge_source")
        assert hasattr(mod, "knowledge_source_list"), (
            "knowledge_source_list should exist after rename"
        )

    def test_knowledge_source_show_importable(self) -> None:
        mod = importlib.import_module("bearclaw.commands.knowledge_source")
        assert hasattr(mod, "knowledge_source_show"), (
            "knowledge_source_show should exist after rename"
        )

    def test_knowledge_source_remove_importable(self) -> None:
        mod = importlib.import_module("bearclaw.commands.knowledge_source")
        assert hasattr(mod, "knowledge_source_remove"), (
            "knowledge_source_remove should exist after rename"
        )


# ---------------------------------------------------------------------------
# TestFromAC_OldNamesRemoved — AC lines 1-4 (inverse)
# ---------------------------------------------------------------------------


class TestFromAC_OldNamesRemoved:
    """After rename, the old abbreviated names must NOT exist in the module."""

    def test_ks_add_no_longer_exists(self) -> None:
        mod = importlib.import_module("bearclaw.commands.knowledge_source")
        assert not hasattr(mod, "ks_add"), "ks_add should be removed after rename"

    def test_ks_list_no_longer_exists(self) -> None:
        mod = importlib.import_module("bearclaw.commands.knowledge_source")
        assert not hasattr(mod, "ks_list"), "ks_list should be removed after rename"

    def test_ks_show_no_longer_exists(self) -> None:
        mod = importlib.import_module("bearclaw.commands.knowledge_source")
        assert not hasattr(mod, "ks_show"), "ks_show should be removed after rename"

    def test_ks_remove_no_longer_exists(self) -> None:
        mod = importlib.import_module("bearclaw.commands.knowledge_source")
        assert not hasattr(mod, "ks_remove"), "ks_remove should be removed after rename"
