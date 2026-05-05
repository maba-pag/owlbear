"""RED-phase tests for task #1350 — Remove legacy dispatch export and refresh kanban docs.

AC coverage:
- AC1: pick_dispatchable removed from __all__ and import in __init__.py; docstring updated (td:1)
- AC2: test_init_exports_1213.py updated — positive test removed, existing set pruned,
        negative assertion added (td:1)
- AC3-6: td:0 — no tests required
"""

from __future__ import annotations

import pathlib

import owlbear_kanban


class TestFromAC_DispatchExportRemoval:
    """AC1: pick_dispatchable removed from __all__ and root-package namespace."""

    def test_pick_dispatchable_absent_from_dunder_all(self) -> None:
        """AC1: pick_dispatchable must NOT be listed in owlbear_kanban.__all__."""
        assert "pick_dispatchable" not in owlbear_kanban.__all__

    def test_module_docstring_no_longer_advertises_pick_dispatchable(self) -> None:
        """AC1: module docstring must not mention 'dispatch selector (pick_dispatchable)'."""
        doc = owlbear_kanban.__doc__ or ""
        assert "dispatch selector (pick_dispatchable)" not in doc


class TestFromAC_TestFileSurgery:
    """AC2: test_init_exports_1213.py updated to reflect the export removal."""

    def test_positive_pick_dispatchable_test_removed(self) -> None:
        """AC2: test_pick_dispatchable_in_dunder_all must be deleted from test_init_exports_1213.py."""
        test_file = pathlib.Path(__file__).parent / "test_init_exports_1213.py"
        content = test_file.read_text(encoding="utf-8")
        assert "def test_pick_dispatchable_in_dunder_all" not in content

    def test_negative_assertion_present(self) -> None:
        """AC2: negative assertion must exist in test_init_exports_1213.py."""
        test_file = pathlib.Path(__file__).parent / "test_init_exports_1213.py"
        content = test_file.read_text(encoding="utf-8")
        assert '"pick_dispatchable" not in owlbear_kanban.__all__' in content
