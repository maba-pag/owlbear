from __future__ import annotations

# --- merged from tests/test_init_exports_1213.py ---
"""Tests for task #1213 — Update __init__.py to export real public API.

AC:
- AC1: __all__ adds exactly: AgentView, ValidationError, NotFoundError,
        ConcurrencyError, CorruptionError
- AC2: `from owlbear_kanban import AgentView` resolves without error
- AC3: `from owlbear_kanban import ValidationError, NotFoundError,
        ConcurrencyError, CorruptionError` resolves without error
- AC4 (refined): No import of `owlbear_cockpit` in any .py file under
        serve/kanban/src/ (test files excluded)
- AC5 (refined): All 6 pre-existing symbols (KanbanEngine, WorkSession,
    Task, TaskSummary, BoardConfig) remain in __all__
        and each resolves via `from owlbear_kanban import X` without error
"""


import importlib
import pathlib
import re

import owlbear_kanban


class TestFromAC_KanbanInitExports:
    """Tests derived from AC for task #1213 (all must be RED before builder starts)."""

    # --- AC1: new symbols present in __all__ ---

    def test_agentview_in_dunder_all(self) -> None:
        """AC1: AgentView must appear in owlbear_kanban.__all__."""
        assert "AgentView" in owlbear_kanban.__all__

    def test_validationerror_in_dunder_all(self) -> None:
        """AC1: ValidationError must appear in owlbear_kanban.__all__."""
        assert "ValidationError" in owlbear_kanban.__all__

    def test_notfounderror_in_dunder_all(self) -> None:
        """AC1: NotFoundError must appear in owlbear_kanban.__all__."""
        assert "NotFoundError" in owlbear_kanban.__all__

    def test_concurrencyerror_in_dunder_all(self) -> None:
        """AC1: ConcurrencyError must appear in owlbear_kanban.__all__."""
        assert "ConcurrencyError" in owlbear_kanban.__all__

    def test_corruptionerror_in_dunder_all(self) -> None:
        """AC1: CorruptionError must appear in owlbear_kanban.__all__."""
        assert "CorruptionError" in owlbear_kanban.__all__

    def test_dunder_all_new_additions_are_exactly_six_symbols(self) -> None:
        """AC1 + #1867: the only additions to __all__ beyond the original 5 are exactly 6 symbols
        (5 from task #1213 + atomic_write from task #1867)."""
        existing = {
            "BoardConfig",
            "KanbanEngine",
            "Task",
            "TaskSummary",
            "WorkSession",
        }
        expected_new = {
            "AgentView",
            "ValidationError",
            "NotFoundError",
            "ConcurrencyError",
            "CorruptionError",
            "atomic_write",
        }
        actual_new = set(owlbear_kanban.__all__) - existing
        assert actual_new == expected_new
        assert "pick_dispatchable" not in owlbear_kanban.__all__

    # --- AC2: AgentView importable from package root ---

    def test_agentview_importable_from_root(self) -> None:
        """AC2: AgentView is accessible as a top-level attribute of owlbear_kanban."""
        mod = importlib.import_module("owlbear_kanban")
        assert hasattr(mod, "AgentView"), "AgentView not found on owlbear_kanban"

    def test_agentview_is_a_class(self) -> None:
        """AC2: AgentView imported from root is a class, not None or an alias error."""
        mod = importlib.import_module("owlbear_kanban")
        agentview_cls = getattr(mod, "AgentView", None)
        assert agentview_cls is not None
        assert isinstance(agentview_cls, type)

    # --- AC3: error classes importable from package root ---

    def test_validationerror_importable_from_root(self) -> None:
        """AC3: ValidationError is accessible as a top-level attribute of owlbear_kanban."""
        mod = importlib.import_module("owlbear_kanban")
        assert hasattr(mod, "ValidationError"), "ValidationError not found on owlbear_kanban"

    def test_notfounderror_importable_from_root(self) -> None:
        """AC3: NotFoundError is accessible as a top-level attribute of owlbear_kanban."""
        mod = importlib.import_module("owlbear_kanban")
        assert hasattr(mod, "NotFoundError"), "NotFoundError not found on owlbear_kanban"

    def test_concurrencyerror_importable_from_root(self) -> None:
        """AC3: ConcurrencyError is accessible as a top-level attribute of owlbear_kanban."""
        mod = importlib.import_module("owlbear_kanban")
        assert hasattr(mod, "ConcurrencyError"), "ConcurrencyError not found on owlbear_kanban"

    def test_corruptionerror_importable_from_root(self) -> None:
        """AC3: CorruptionError is accessible as a top-level attribute of owlbear_kanban."""
        mod = importlib.import_module("owlbear_kanban")
        assert hasattr(mod, "CorruptionError"), "CorruptionError not found on owlbear_kanban"

    # --- AC4: no owlbear_cockpit import in serve/kanban/src/ ---

    def test_no_owlbear_cockpit_import_in_src(self) -> None:
        """AC4: No file under serve/kanban/src/ imports owlbear_cockpit."""
        src_root = pathlib.Path(__file__).parent.parent / "serve" / "kanban" / "src"
        violations = []
        for py_file in src_root.rglob("*.py"):
            text = py_file.read_text(encoding="utf-8")
            if re.search(r"owlbear_cockpit", text):
                violations.append(str(py_file.relative_to(src_root.parent.parent.parent)))
        assert not violations, f"owlbear_cockpit referenced in src files: {violations}"

    # --- AC5: pre-existing symbols still in __all__ ---

    def test_kanbanengine_in_dunder_all(self) -> None:
        """AC5: KanbanEngine must remain in owlbear_kanban.__all__."""
        assert "KanbanEngine" in owlbear_kanban.__all__

    def test_worksession_in_dunder_all(self) -> None:
        """AC5: WorkSession must remain in owlbear_kanban.__all__."""
        assert "WorkSession" in owlbear_kanban.__all__

    def test_task_in_dunder_all(self) -> None:
        """AC5: Task must remain in owlbear_kanban.__all__."""
        assert "Task" in owlbear_kanban.__all__

    def test_tasksummary_in_dunder_all(self) -> None:
        """AC5: TaskSummary must remain in owlbear_kanban.__all__."""
        assert "TaskSummary" in owlbear_kanban.__all__

    def test_boardconfig_in_dunder_all(self) -> None:
        """AC5: BoardConfig must remain in owlbear_kanban.__all__."""
        assert "BoardConfig" in owlbear_kanban.__all__

    # --- AC5: pre-existing symbols importable from package root ---

    def test_kanbanengine_importable_from_root(self) -> None:
        """AC5: KanbanEngine resolves via from owlbear_kanban import KanbanEngine."""
        mod = importlib.import_module("owlbear_kanban")
        assert hasattr(mod, "KanbanEngine"), "KanbanEngine not found on owlbear_kanban"

    def test_worksession_importable_from_root(self) -> None:
        """AC5: WorkSession resolves via from owlbear_kanban import WorkSession."""
        mod = importlib.import_module("owlbear_kanban")
        assert hasattr(mod, "WorkSession"), "WorkSession not found on owlbear_kanban"

    def test_task_importable_from_root(self) -> None:
        """AC5: Task resolves via from owlbear_kanban import Task."""
        mod = importlib.import_module("owlbear_kanban")
        assert hasattr(mod, "Task"), "Task not found on owlbear_kanban"

    def test_tasksummary_importable_from_root(self) -> None:
        """AC5: TaskSummary resolves via from owlbear_kanban import TaskSummary."""
        mod = importlib.import_module("owlbear_kanban")
        assert hasattr(mod, "TaskSummary"), "TaskSummary not found on owlbear_kanban"

    def test_boardconfig_importable_from_root(self) -> None:
        """AC5: BoardConfig resolves via from owlbear_kanban import BoardConfig."""
        mod = importlib.import_module("owlbear_kanban")
        assert hasattr(mod, "BoardConfig"), "BoardConfig not found on owlbear_kanban"


# --- merged from tests/test_init_exports_1350.py ---
"""RED-phase tests for task #1350 — Remove legacy dispatch export and refresh kanban docs.

AC coverage:
- AC1: pick_dispatchable removed from __all__ and import in __init__.py; docstring updated (td:1)
- AC2: test_init_exports_1213.py updated — positive test removed, existing set pruned,
        negative assertion added (td:1)
- AC3-6: td:0 — no tests required
"""


import pathlib
import re

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

    def test_pick_dispatchable_absent_from_root_namespace(self) -> None:
        """AC1: pick_dispatchable must NOT be bound on the owlbear_kanban root namespace."""
        assert not hasattr(owlbear_kanban, "pick_dispatchable")


class TestFromAC_TestFileSurgery:
    """AC2: test_init_exports_1213.py updated to reflect the export removal."""

    def test_positive_pick_dispatchable_test_removed(self) -> None:
        """AC2: no line in the merged test file defines test_pick_dispatchable_in_dunder_all
        as a function (test_init_exports_1213.py was merged into test_init_exports.py;
        the positive test was never re-added)."""
        test_file = pathlib.Path(__file__).parent / "test_init_exports.py"
        lines = test_file.read_text(encoding="utf-8").splitlines()
        assert not any(line.strip().startswith("def test_pick_dispatchable_in_dunder_all") for line in lines)

    def test_negative_assertion_present(self) -> None:
        """AC2: negative assertion for pick_dispatchable must exist in the merged test file."""
        test_file = pathlib.Path(__file__).parent / "test_init_exports.py"
        content = test_file.read_text(encoding="utf-8")
        assert '"pick_dispatchable" not in owlbear_kanban.__all__' in content

    def test_existing_set_pruned_of_pick_dispatchable(self) -> None:
        """AC2: the 'existing' baseline set in the merged test file must not list pick_dispatchable."""
        test_file = pathlib.Path(__file__).parent / "test_init_exports.py"
        content = test_file.read_text(encoding="utf-8")
        match = re.search(r"existing\s*=\s*\{([^}]+)\}", content, re.DOTALL)
        assert match is not None, "existing set not found in test_init_exports.py"
        existing_body = match.group(1)
        assert "pick_dispatchable" not in existing_body
