"""Failing tests for task #1211: Consolidate 6 duplicated helper functions.

RED phase — all tests must FAIL on the current codebase.

AC coverage:
  AC1 — test_naming_module_exists, test_naming_module_has_generate_slug,
         test_naming_module_has_make_task_filename,
         test_naming_module_has_validate_path_containment,
         test_naming_module_has_move_to_quarantine
  AC2 — test_storage_generate_slug_no_local_body,
         test_storage_make_task_filename_no_local_body,
         test_storage_validate_path_containment_no_local_body,
         test_storage_move_to_quarantine_no_local_body,
         test_storage_imports_from_naming,
         test_storage_imports_generate_slug_from_naming,
         test_storage_imports_make_task_filename_from_naming,
         test_storage_imports_validate_path_containment_from_naming,
         test_storage_imports_move_to_quarantine_from_naming
  AC3 — test_corruption_no_private_generate_slug,
         test_corruption_no_private_make_task_filename,
         test_corruption_no_private_validate_path_containment,
         test_corruption_no_private_move_to_quarantine,
         test_corruption_imports_from_naming,
         test_corruption_imports_make_task_filename_from_naming,
         test_corruption_imports_move_to_quarantine_from_naming
  AC4 — test_agentview_no_dep_effect_method,
         test_kanbanengine_has_dep_effect_method
  AC5 — test_agentview_no_compute_dep_status_method,
         test_agentview_show_task_delegates_compute_dep_status
  AC6 — test_naming_module_importable
"""

from __future__ import annotations

import ast
from pathlib import Path

_PKG_DIR = Path(__file__).parent.parent / "serve" / "kanban" / "src" / "owlbear_kanban"


def _source(filename: str) -> str:
    return (_PKG_DIR / filename).read_text(encoding="utf-8")


def _has_top_level_function(source: str, funcname: str) -> bool:
    """Return True if *source* has a module-level FunctionDef named *funcname*."""
    tree = ast.parse(source)
    return any(isinstance(node, ast.FunctionDef) and node.name == funcname for node in ast.iter_child_nodes(tree))


def _has_class_method(source: str, classname: str, methodname: str) -> bool:
    """Return True if class *classname* in *source* has a method *methodname*."""
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == classname:
            for item in ast.iter_child_nodes(node):
                if isinstance(item, ast.FunctionDef) and item.name == methodname:
                    return True
    return False


def _imports_from(source: str, module: str) -> bool:
    """Return True if *source* contains ``from {module} import ...``."""
    tree = ast.parse(source)
    return any(isinstance(node, ast.ImportFrom) and node.module == module for node in ast.walk(tree))


def _class_method_calls_attr(source: str, classname: str, methodname: str, callee_attr: str) -> bool:
    """Return True if any method in *classname* contains a call to .{callee_attr}(...)."""
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == classname:
            for item in ast.walk(node):
                if isinstance(item, ast.FunctionDef) and item.name == methodname:
                    continue
                if isinstance(item, ast.Call):
                    func = item.func
                    if isinstance(func, ast.Attribute) and func.attr == callee_attr:
                        return True
    return False


def _imported_names_from(source: str, module: str) -> set[str]:
    """Return all names imported via 'from {module} import ...' statements."""
    tree = ast.parse(source)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == module:
            names.update(alias.name for alias in node.names)
    return names


def _method_calls_engine_attr(source: str, classname: str, methodname: str, attr: str) -> bool:
    """Return True if classname.methodname contains a call to self.engine.{attr}(...)."""
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == classname:
            for item in ast.walk(node):
                if isinstance(item, ast.FunctionDef) and item.name == methodname:
                    for call in ast.walk(item):
                        if isinstance(call, ast.Call):
                            func = call.func
                            if (
                                isinstance(func, ast.Attribute)
                                and func.attr == attr
                                and isinstance(func.value, ast.Attribute)
                                and func.value.attr == "engine"
                                and isinstance(func.value.value, ast.Name)
                                and func.value.value.id == "self"
                            ):
                                return True
    return False


# ---------------------------------------------------------------------------
# TestFromAC_NamingLeafModule — AC1: _naming.py exists with 4 helpers
# ---------------------------------------------------------------------------


class TestFromAC_NamingLeafModule:
    """AC1: New leaf module _naming.py exists with 4 path/naming helpers."""

    def test_naming_module_exists(self) -> None:
        """AC1: _naming.py must exist inside owlbear_kanban package."""
        naming_path = _PKG_DIR / "_naming.py"
        assert naming_path.exists(), "_naming.py does not exist in owlbear_kanban package"

    def test_naming_module_has_generate_slug(self) -> None:
        """AC1: _naming.py must define generate_slug at module level."""
        src = _source("_naming.py")
        assert _has_top_level_function(src, "generate_slug"), "_naming.py missing top-level function: generate_slug"

    def test_naming_module_has_make_task_filename(self) -> None:
        """AC1: _naming.py must define make_task_filename at module level."""
        src = _source("_naming.py")
        assert _has_top_level_function(src, "make_task_filename"), (
            "_naming.py missing top-level function: make_task_filename"
        )

    def test_naming_module_has_validate_path_containment(self) -> None:
        """AC1: _naming.py must define validate_path_containment at module level."""
        src = _source("_naming.py")
        assert _has_top_level_function(src, "validate_path_containment"), (
            "_naming.py missing top-level function: validate_path_containment"
        )

    def test_naming_module_has_move_to_quarantine(self) -> None:
        """AC1: _naming.py must define move_to_quarantine at module level."""
        src = _source("_naming.py")
        assert _has_top_level_function(src, "move_to_quarantine"), (
            "_naming.py missing top-level function: move_to_quarantine"
        )


# ---------------------------------------------------------------------------
# TestFromAC_StorageReexports — AC2: storage.py re-exports from _naming.py
# ---------------------------------------------------------------------------


class TestFromAC_StorageReexports:
    """AC2: storage.py re-exports from _naming.py; no local function bodies for the 4 helpers."""

    def test_storage_imports_from_naming(self) -> None:
        """AC2: storage.py must have 'from owlbear_kanban._naming import ...'."""
        src = _source("storage.py")
        assert _imports_from(src, "owlbear_kanban._naming"), "storage.py does not import from owlbear_kanban._naming"

    def test_storage_generate_slug_no_local_body(self) -> None:
        """AC2: generate_slug must NOT have a function body in storage.py (re-export only)."""
        src = _source("storage.py")
        assert not _has_top_level_function(src, "generate_slug"), (
            "storage.py still has a local function body for generate_slug"
        )

    def test_storage_make_task_filename_no_local_body(self) -> None:
        """AC2: make_task_filename must NOT have a function body in storage.py."""
        src = _source("storage.py")
        assert not _has_top_level_function(src, "make_task_filename"), (
            "storage.py still has a local function body for make_task_filename"
        )

    def test_storage_validate_path_containment_no_local_body(self) -> None:
        """AC2: validate_path_containment must NOT have a function body in storage.py."""
        src = _source("storage.py")
        assert not _has_top_level_function(src, "validate_path_containment"), (
            "storage.py still has a local function body for validate_path_containment"
        )

    def test_storage_move_to_quarantine_no_local_body(self) -> None:
        """AC2: move_to_quarantine must NOT have a function body in storage.py."""
        src = _source("storage.py")
        assert not _has_top_level_function(src, "move_to_quarantine"), (
            "storage.py still has a local function body for move_to_quarantine"
        )

    def test_storage_imports_generate_slug_from_naming(self) -> None:
        """AC2: generate_slug must be explicitly named in storage.py's _naming import."""
        src = _source("storage.py")
        names = _imported_names_from(src, "owlbear_kanban._naming")
        assert "generate_slug" in names, (
            "storage.py does not explicitly import generate_slug from owlbear_kanban._naming"
        )

    def test_storage_imports_make_task_filename_from_naming(self) -> None:
        """AC2: make_task_filename must be explicitly named in storage.py's _naming import."""
        src = _source("storage.py")
        names = _imported_names_from(src, "owlbear_kanban._naming")
        assert "make_task_filename" in names, (
            "storage.py does not explicitly import make_task_filename from owlbear_kanban._naming"
        )

    def test_storage_imports_validate_path_containment_from_naming(self) -> None:
        """AC2: validate_path_containment must be explicitly named in storage.py's _naming import."""
        src = _source("storage.py")
        names = _imported_names_from(src, "owlbear_kanban._naming")
        assert "validate_path_containment" in names, (
            "storage.py does not explicitly import validate_path_containment from owlbear_kanban._naming"
        )

    def test_storage_imports_move_to_quarantine_from_naming(self) -> None:
        """AC2: move_to_quarantine must be explicitly named in storage.py's _naming import."""
        src = _source("storage.py")
        names = _imported_names_from(src, "owlbear_kanban._naming")
        assert "move_to_quarantine" in names, (
            "storage.py does not explicitly import move_to_quarantine from owlbear_kanban._naming"
        )


# ---------------------------------------------------------------------------
# TestFromAC_CorruptionImportsFromNaming — AC3: corruption.py imports from _naming.py
# ---------------------------------------------------------------------------


class TestFromAC_CorruptionImportsFromNaming:
    """AC3: corruption.py imports from _naming.py; private copies deleted."""

    def test_corruption_imports_from_naming(self) -> None:
        """AC3: corruption.py must have 'from owlbear_kanban._naming import ...'."""
        src = _source("corruption.py")
        assert _imports_from(src, "owlbear_kanban._naming"), "corruption.py does not import from owlbear_kanban._naming"

    def test_corruption_no_private_generate_slug(self) -> None:
        """AC3: Private copy _generate_slug must be deleted from corruption.py."""
        src = _source("corruption.py")
        assert not _has_top_level_function(src, "_generate_slug"), (
            "corruption.py still has private function body _generate_slug"
        )

    def test_corruption_no_private_make_task_filename(self) -> None:
        """AC3: Private copy _make_task_filename must be deleted from corruption.py."""
        src = _source("corruption.py")
        assert not _has_top_level_function(src, "_make_task_filename"), (
            "corruption.py still has private function body _make_task_filename"
        )

    def test_corruption_no_private_validate_path_containment(self) -> None:
        """AC3: Private copy _validate_path_containment must be deleted from corruption.py."""
        src = _source("corruption.py")
        assert not _has_top_level_function(src, "_validate_path_containment"), (
            "corruption.py still has private function body _validate_path_containment"
        )

    def test_corruption_no_private_move_to_quarantine(self) -> None:
        """AC3: Private copy _move_to_quarantine must be deleted from corruption.py."""
        src = _source("corruption.py")
        assert not _has_top_level_function(src, "_move_to_quarantine"), (
            "corruption.py still has private function body _move_to_quarantine"
        )

    def test_corruption_imports_make_task_filename_from_naming(self) -> None:
        """AC3: make_task_filename must be explicitly named in corruption.py's _naming import."""
        src = _source("corruption.py")
        names = _imported_names_from(src, "owlbear_kanban._naming")
        assert "make_task_filename" in names, (
            "corruption.py does not explicitly import make_task_filename from owlbear_kanban._naming"
        )

    def test_corruption_imports_move_to_quarantine_from_naming(self) -> None:
        """AC3: move_to_quarantine must be explicitly named in corruption.py's _naming import."""
        src = _source("corruption.py")
        names = _imported_names_from(src, "owlbear_kanban._naming")
        assert "move_to_quarantine" in names, (
            "corruption.py does not explicitly import move_to_quarantine from owlbear_kanban._naming"
        )


# ---------------------------------------------------------------------------
# TestFromAC_AgentViewDelegation — AC4 & AC5: AgentView delegates to KanbanEngine
# ---------------------------------------------------------------------------


class TestFromAC_AgentViewDelegation:
    """AC4: AgentView._dep_effect_from_archival_reason removed; delegates to KanbanEngine.
    AC5: AgentView._compute_dep_status removed; delegates to KanbanEngine.
    """

    def test_agentview_no_dep_effect_method(self) -> None:
        """AC4: AgentView must NOT define _dep_effect_from_archival_reason as its own method."""
        src = _source("engine.py")
        assert not _has_class_method(src, "AgentView", "_dep_effect_from_archival_reason"), (
            "AgentView still has its own _dep_effect_from_archival_reason; must delegate to KanbanEngine"
        )

    def test_agentview_no_compute_dep_status_method(self) -> None:
        """AC5: AgentView must NOT define _compute_dep_status as its own method."""
        src = _source("engine.py")
        assert not _has_class_method(src, "AgentView", "_compute_dep_status"), (
            "AgentView still has its own _compute_dep_status; must delegate to KanbanEngine"
        )

    def test_kanbanengine_has_dep_effect_method(self) -> None:
        """AC4: KanbanEngine must have _dep_effect_from_archival_reason as the canonical location."""
        src = _source("engine.py")
        assert _has_class_method(src, "KanbanEngine", "_dep_effect_from_archival_reason"), (
            "KanbanEngine missing _dep_effect_from_archival_reason; canonical location must exist"
        )

    def test_agentview_show_task_delegates_compute_dep_status(self) -> None:
        """AC5: AgentView.show_task() must call self.engine._compute_dep_status(...)."""
        src = _source("agent_view.py")
        assert _method_calls_engine_attr(src, "AgentView", "show_task", "_compute_dep_status"), (
            "AgentView.show_task() does not delegate to self.engine._compute_dep_status(...)"
        )


# ---------------------------------------------------------------------------
# TestFromAC_NoCircularImports — AC6: import owlbear_kanban._naming succeeds
# ---------------------------------------------------------------------------


class TestFromAC_NoCircularImports:
    """AC6: No circular imports — owlbear_kanban._naming importable, full package loads."""

    def test_naming_module_importable(self) -> None:
        """AC6: owlbear_kanban._naming must be importable without ImportError."""
        import importlib  # noqa: PLC0415

        mod = importlib.import_module("owlbear_kanban._naming")
        assert mod is not None

    def test_naming_module_exports_generate_slug(self) -> None:
        """AC6: owlbear_kanban._naming must expose generate_slug callable."""
        import importlib  # noqa: PLC0415

        mod = importlib.import_module("owlbear_kanban._naming")
        assert callable(getattr(mod, "generate_slug", None)), "owlbear_kanban._naming.generate_slug not callable"

    def test_storage_generate_slug_comes_from_naming(self) -> None:
        """AC2+AC6: generate_slug imported into storage must originate from _naming module."""
        from owlbear_kanban import storage  # noqa: PLC0415

        fn = getattr(storage, "generate_slug", None)
        assert fn is not None, "storage.generate_slug not present"
        assert getattr(fn, "__module__", None) == "owlbear_kanban._naming", (
            f"generate_slug.__module__ == {fn.__module__!r}, expected 'owlbear_kanban._naming'"
        )
